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
        self.msg = args[0]


class UserError(BinstarError):
    pass


class ServerError(BinstarError):
    pass


class ShowHelp(BinstarError):
    pass


class NoMetadataError(BinstarError):
    pass


class DestionationPathExists(BinstarError):
    def __init__(self, location):
        self.msg = "destination path '{}' already exists.".format(location)
        self.location = location
        super(BinstarError, self).__init__(self.msg)


class PillowNotInstalled(BinstarError):
    def __init__(self):
        self.msg = ("pillow is not installed. Install it with:\n"
                    "    conda install pillow")
        super(BinstarError, self).__init__(self.msg)
