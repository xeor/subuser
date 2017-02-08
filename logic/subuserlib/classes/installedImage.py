# -*- coding: utf-8 -*-

"""
Each user has a set of images that have been installed.
"""

#external imports
import os
import json
#internal imports
from subuserlib.classes.userOwnedObject import UserOwnedObject
from subuserlib.classes.describable import Describable
import subuserlib.classes.docker.dockerDaemon as dockerDaemon

class InstalledImage(UserOwnedObject,Describable):
  def __init__(self,user,imageId,imageSourceName,sourceRepoId,imageSourceHash):
    self.imageId = imageId
    self.__imageSourceHash = imageSourceHash
    self.imageSourceName = imageSourceName
    self.sourceRepoId = sourceRepoId
    self.__alreadyCheckedForUpdates = None
    UserOwnedObject.__init__(self,user)

  def getImageSource(self):
    return self.getUser().getRegistry().getRepositories()[self.sourceRepoId][self.imageSourceName]

  def getImageSourceHash(self):
    return self.__imageSourceHash

  def isDockerImageThere(self):
    """
    Does the Docker daemon have an image with this imageId?
    """
    return not (self.getUser().getDockerDaemon().getImageProperties(self.imageId) == None)

  def removeCachedRuntimes(self):
    """
    Remove cached runtime environments.
    """
    pathToImagesRuntimeCacheDir = os.path.join(self.getUser().getConfig()["runtime-cache"],self.imageId)
    try:
      for permissionsSpecificCacheInfoFileName in os.listdir(pathToImagesRuntimeCacheDir):
        permissionsSpecificCacheInfoFilePath = os.path.join(pathToImagesRuntimeCacheDir,permissionsSpecificCacheInfoFileName)
        with open(permissionsSpecificCacheInfoFilePath,mode='r') as permissionsSpecificCacheInfoFileHandle:
          permissionsSpecificCacheInfo = json.load(permissionsSpecificCacheInfoFileHandle)
          try:
            try:
              imageId = permissionsSpecificCacheInfo['run-ready-image-id']
              self.getUser().getRegistry().log("Removing runtime cache image %s"%imageId)
              self.getUser().getDockerDaemon().removeImage(imageId)
            except dockerDaemon.ImageDoesNotExistsException:
              pass
            os.remove(permissionsSpecificCacheInfoFilePath)
          except dockerDaemon.ContainerDependsOnImageException:
            pass
    except OSError:
      pass

  def removeDockerImage(self):
    """
    Remove the image from the Docker daemon's image store.
    """
    try:
      self.getUser().getRegistry().log("Removing image %s"%self.imageId)
      self.getUser().getDockerDaemon().removeImage(self.imageId)
    except (dockerDaemon.ImageDoesNotExistsException,dockerDaemon.ContainerDependsOnImageException,dockerDaemon.ServerErrorException) as e:
      self.getUser().getRegistry().log("Error removing image: "+self.imageId+"\n"+str(e))

  def describe(self):
    print("Image Id: "+self.imageId)
    try:
      print("Image source: "+self.getImageSource().getIdentifier())
    except KeyError:
      print("Image is broken, image source does not exist!")
    print("Last update time: "+self.getCreationDateTime())

  def checkForUpdates(self):
    """
    Check for updates using the image's built in check-for-updates script. This launches the script as root in a privilageless container. Returns True if the image needs to be updated.
    """
    if self.__alreadyCheckedForUpdates:
      return False
    self.__alreadyCheckedForUpdates = True
    self.getUser().getRegistry().log("Checking for updates to: " + self.getImageSource().getIdentifier())
    if self.getUser().getDockerDaemon().execute(["run","--rm","--entrypoint","/usr/bin/test",self.imageId,"-e","/subuser/check-for-updates"]) == 0:
      returnCode = self.getUser().getDockerDaemon().execute(["run","--rm","--entrypoint","/subuser/check-for-updates",self.imageId])
      if returnCode == 0:
        return True
    return False

  def getCreationDateTime(self):
    """
    Return the creation date/time of the installed docker image. Or None if the image does not exist.
    """
    imageProperties = self.getUser().getDockerDaemon().getImageProperties(self.imageId)
    if not imageProperties is None:
      return imageProperties["Created"]
    else:
      return None

  def getLineageLayers(self):
    """
    Return the list(lineage) of id of Docker image layers which goes from a base image to this image including all of the image's ancestors in order of dependency.
    """
    def getLineageRecursive(imageId):
      imageProperties = self.getUser().getDockerDaemon().getImageProperties(imageId)
      if imageProperties == None:
        return []
        #sys.exit("Failed to get properties of image "+imageId)
      if not imageProperties["Parent"] == "":
        return getLineageRecursive(imageProperties["Parent"]) + [imageId]
      else:
        return [imageId]
    return getLineageRecursive(self.imageId)

  def getImageLineage(self):
    """
    Return the list(lineage) of InstalledImages which goes from a base image to this image including all of the image's ancestors in order of dependency.
    """
    lineage = []
    dockerImageLayers = self.getLineageLayers()
    for dockerImageLayer in dockerImageLayers:
      if dockerImageLayer in self.getUser().getInstalledImages():
        lineage.append(self.getUser().getInstalledImages()[dockerImageLayer])
    return lineage
