"""Defines the subcommand plugins for the new CLI defined in anaconda-cli-base.

We define a new subcommand called `anaconda org`, which nests all existing
anaconda-client subcommands beneath it. Additionally, we mount all of the
existing subcommands, with the exception of "login" and "logout" at the top
level of the CLI, although some of these are mounted silently. This is done to
maintain backwards compatibility while we work to deprecate some of them.

Rather than re-write all the CLI code in anaconda-client, we opt to dynamically
register each subcommand in the `load_legacy_subcommands` function.

Note: This module should not be imported, except as defined as a plugin
entrypoint in setup.py.

"""

import logging
import sys
from argparse import ArgumentParser
from typing import Any
from typing import Callable
from typing import List
from typing import Optional
from typing import Set

from binstar_client import commands as command_module
from binstar_client.scripts.cli import (
    _add_subparser_modules as add_subparser_modules, main as binstar_main,
)
from binstar_client.scripts.cli import main as binstar_main

from typer import Context, Typer

# All subcommands in anaconda-client
LEGACY_SUBCOMMANDS = {
    "auth",
    "channel",
    "config",
    "copy",
    "download",
    "groups",
    "label",
    "login",
    "logout",
    "move",
    "notebook",
    "package",
    "remove",
    "search",
    "show",
    "update",
    "upload",
    "whoami",
}
# These subcommands will be shown in the top-level help
NON_HIDDEN_SUBCOMMANDS = {
    "upload",
}
# Any subcommands that should emit deprecation warnings, and show as deprecated in the help
DEPRECATED_SUBCOMMANDS: Set[str] = set()

# The logger
log = logging.getLogger(__name__)

app = Typer(
    add_completion=False,
    name="org",
    help="Interact with anaconda.org",
    no_args_is_help=True,
)


def _get_help_text(parser: ArgumentParser, name: str) -> str:
    """Extract the help text from the anaconda-client CLI Argument Parser."""
    if parser._subparsers is None:
        return ""
    if parser._subparsers._actions is None:
        return ""
    if parser._subparsers._actions[1].choices is None:
        return ""
    subcommand_parser = dict(parser._subparsers._actions[1].choices).get(name)
    if subcommand_parser is None:
        return ""
    description = subcommand_parser.description
    if description is None:
        return ""
    return description.strip()


def _deprecate(name: str, f: Callable) -> Callable:
    def new_f(ctx: Context) -> Any:
        if name in DEPRECATED_SUBCOMMANDS:
            log.warning(
                "The existing anaconda-client commands will be deprecated. To maintain compatibility, "
                "please either pin `anaconda-client<2` or update your system call with the `org` prefix, "
                f'e.g. "anaconda org {name} ..."'
            )
        return f(ctx)

    return new_f


def _subcommand(ctx: Context) -> None:
    """A common function to use for all subcommands.

    In a proper typer/click app, this is the function that is decorated.

    We use the typer.Context object to extract the args passed into the CLI, and then delegate
    to the binstar_main function.

    """
    args = []
    # Ensure we capture the subcommand name if there is one
    if ctx.info_name is not None:
        args.append(ctx.info_name)
    args.extend(ctx.args)
    binstar_main(args, allow_plugin_main=False)


def load_legacy_subcommands() -> None:
    """Load each of the legacy subcommands into its own typer subcommand.

    This allows them to be called from the new CLI, without having to manually migrate.

    """

    from anaconda_cli_base.cli import app as main_app

    parser = ArgumentParser()
    add_subparser_modules(parser, command_module)

    for name in LEGACY_SUBCOMMANDS:

        # Define all of the subcommands in the typer app
        # TODO: Can we load the arguments, or at least the docstring to make the help nicer?
        help_text = _get_help_text(parser, name)
        app.command(
            name=name,
            help=help_text,
            context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
        )(_subcommand)

        # Mount some CLI subcommands at the top-level, but optionally emit a deprecation warning
        if name not in {"login", "logout"}:
            help_text = f"anaconda.org: {help_text + ' ' if help_text else ''}(alias for 'anaconda org {name}')"
            if name in DEPRECATED_SUBCOMMANDS:
                help_text = f"(deprecated) {help_text}"
            main_app.command(
                name=name,
                help=help_text,
                hidden=name not in NON_HIDDEN_SUBCOMMANDS,
                context_settings={
                    "allow_extra_args": True,
                    "ignore_unknown_options": True,
                },
            )(_deprecate(name, _subcommand))


load_legacy_subcommands()
