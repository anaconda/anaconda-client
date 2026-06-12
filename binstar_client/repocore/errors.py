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


class AnacondaLoginRequired(RepoCoreError):
    def __init__(self, domain=None):
        domain_msg = f" for domain: {domain}" if domain else ""
        self.msg = (
            f"Authentication required{domain_msg}.\n\n"
            "Please authenticate using the Anaconda CLI:\n\n"
            "    anaconda login\n\n"
            "After authentication, your credentials will be used automatically.\n"
        )
        super().__init__(self.msg)
