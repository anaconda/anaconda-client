'''
Created on Jul 15, 2013

@author: sean
'''

class BinstarError(Exception):
    pass

class Unauthorized(BinstarError):
    pass

class Conflict(BinstarError):
    pass

class NotFound(IndexError, BinstarError):
    pass

class UserError(BinstarError):
    pass


class ShowHelp(BinstarError):
    pass


