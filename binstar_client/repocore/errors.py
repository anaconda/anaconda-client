"""Repocore-specific exceptions."""

from anaconda_cli_base.exceptions import register_error_handler


class RepoCoreError(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not hasattr(self, "message"):
            self.message = args[0] if args else None


class Unauthorized(RepoCoreError):
    def __init__(self, message=None):
        self.msg = message or "The provided token does not allow you to perform this operation"
        super().__init__(self.msg)


class LoginRequiredError(RepoCoreError):
    def __init__(self):
        super().__init__(
            "Authentication required. Please run 'anaconda login' and try again."
        )


class InvalidName(RepoCoreError):
    pass


class NoDefaultChannel(RepoCoreError):
    pass


@register_error_handler(LoginRequiredError)
def _handle_login_required(e: Exception) -> int:
    from anaconda_auth.cli import _continue_with_login

    return _continue_with_login()
