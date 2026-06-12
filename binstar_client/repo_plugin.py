"""Plugin entry point for the `anaconda repo` subcommand.

If conda-repo-cli is installed, defer to its app (it provides the full feature set).
Otherwise, use the built-in repocore support (channels CRUD + upload).
"""

try:
    from anaconda_repo_cli.app import app  # noqa: F401
except ImportError:
    from binstar_client.commands._repo_app import app  # noqa: F401
