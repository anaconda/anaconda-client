from clyent.errors import ClyentError


class RepoCLIError(ClyentError):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

        if not hasattr(self, 'message'):
            self.message = args[0] if args else None


class Unauthorized(RepoCLIError):
    pass


class Conflict(RepoCLIError):
    pass


class NotFound(RepoCLIError, IndexError):
    def __init__(self, *args, **kwargs):
        RepoCLIError.__init__(self, *args, **kwargs)
        IndexError.__init__(self, *args, **kwargs)
        self.message = args[0]
        self.msg = args[0]


class UserError(RepoCLIError):
    pass


class ServerError(RepoCLIError):
    pass


class ShowHelp(RepoCLIError):
    pass


class NoMetadataError(RepoCLIError):
    pass


class DestionationPathExists(RepoCLIError):
    def __init__(self, location):
        self.msg = "destination path '{}' already exists.".format(location)
        self.location = location
        super(RepoCLIError, self).__init__(self.msg)


class PillowNotInstalled(RepoCLIError):
    def __init__(self):
        self.msg = ("pillow is not installed. Install it with:\n"
                    "    conda install pillow")
        super(RepoCLIError, self).__init__(self.msg)
