from clyent.errors import ClyentError

class BinstarError(ClyentError):

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

        if not hasattr(self, 'message'):
            self.message = args[0] if args else None

class Unauthorized(BinstarError):
    pass

class Conflict(BinstarError):
    pass

class NotFound(BinstarError, IndexError):

    def __init__(self, *args, **kwargs):
        BinstarError.__init__(self, *args, **kwargs)
        IndexError.__init__(self, *args, **kwargs)

        self.message = args[0]

class UserError(BinstarError):
    pass

class ServerError(BinstarError):
    pass


class ShowHelp(BinstarError):
    pass


class NoMetadataError(BinstarError):
    pass
