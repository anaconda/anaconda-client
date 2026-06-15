"""Repocore-specific exceptions."""


class RepoCoreError(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not hasattr(self, "message"):
            self.message = args[0] if args else None


class Unauthorized(RepoCoreError):
    def __init__(self, message=None):
        self.msg = message or "The provided token does not allow you to perform this operation"
        super().__init__(self.msg)


class InvalidName(RepoCoreError):
    pass


class NoDefaultChannel(RepoCoreError):
    pass
