"""Repocore-specific exceptions."""

import re


class RepoCoreError(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not hasattr(self, "message"):
            self.message = args[0] if args else None

    def __str__(self):
        message = super().__str__()
        return re.sub(r'\b[Ss]ubchannel\b', lambda m: 'Channel' if m.group()[0].isupper() else 'channel', message)


class Unauthorized(RepoCoreError):
    def __init__(self, message=None):
        self.msg = message or "The provided token does not allow you to perform this operation"
        super().__init__(self.msg)


class LoginRequiredError(RepoCoreError):
    def __init__(self):
        super().__init__("Authentication required. Please run 'anaconda login' and try again.")


class InvalidName(RepoCoreError):
    pass


class NoDefaultChannel(RepoCoreError):
    pass
