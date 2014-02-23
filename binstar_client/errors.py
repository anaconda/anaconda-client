'''
Created on Jul 15, 2013

@author: sean
'''

class BinstarError(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)
        
        if not hasattr(self, 'message'):
            self.message = args[0] if args else None

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


