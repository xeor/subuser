# -*- coding: utf-8 -*-

"""
All objects in subuser are owned by the C{subuserlib.classes.user.User} object.
"""

#external imports
#import ...
#internal imports
#import ...

class UserOwnedObject(object):
  def __init__(self,user):
    self.user = user
