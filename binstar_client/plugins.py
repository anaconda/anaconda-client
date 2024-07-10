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

from anaconda_cli_base.cli import app as main_app
import typer
import typer.colors
from typer import Context, Typer

# All subcommands in anaconda-client
ALL_SUBCOMMANDS = {
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
DEPRECATED_SUBCOMMANDS: str = {
    "notebook",
}

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
    """Mark a named subcommand as deprecated.

    Args:
        name: The name of the subcommand.
        f: The subcommand callable.

    """
    def new_f(ctx: Context) -> Any:
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


def _mount_subcommand(
    *,
    name: str,
    help_text: str,
    is_deprecated: bool,
    mount_to_main: bool,
    is_hidden_on_main: bool,
) -> None:
    """Mount an existing subcommand to the `anaconda org` typer application.

    Args:
        name: The name of the subcommand.
        help_text: The help text for the subcommand
        is_deprecated: If True, mark the subcommand as deprecated. This will cause a warning to be
            emitted, and also add "(deprecated)" to the help text.
        mount_to_main: If True, also mount the subcommand to the main typer app.
        is_hidden_on_main: If True, the subcommand is registered as a hidden subcommand of the main CLI
            for backwards-compatibility

    """
    if is_deprecated:
        deprecated_text = typer.style("(deprecated)", fg=typer.colors.RED, bold=True)
        help_text = f"{deprecated_text} {help_text}"
        f = _deprecate(name, _subcommand)
    else:
        f = _subcommand

    # Mount the subcommand to the `anaconda org` application.
    app.command(
        name=name,
        help=help_text,
        context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    )(f)

    # Exit early if we are not mounting to the main `anaconda` app
    if not mount_to_main:
        return

    # Mount some CLI subcommands at the top-level, but optionally emit a deprecation warning
    help_text = f"anaconda.org: {help_text + ' ' if help_text else ''}(alias for 'anaconda org {name}')"

    main_app.command(
        name=name,
        help=help_text,
        hidden=is_hidden_on_main,
        context_settings={
            "allow_extra_args": True,
            "ignore_unknown_options": True,
        },
    )(f)


def load_legacy_subcommands() -> None:
    """Load each of the legacy subcommands into its own typer subcommand.

    This allows them to be called from the new CLI, without having to manually migrate.

    """
    parser = ArgumentParser()
    add_subparser_modules(parser, command_module)

    for name in ALL_SUBCOMMANDS:
        # TODO: Can we load the arguments, or at least the docstring to make the help nicer?
        _mount_subcommand(
            name=name,
            help_text=_get_help_text(parser, name),
            is_deprecated=(name in DEPRECATED_SUBCOMMANDS),
            mount_to_main=(name not in {"login", "logout"}),
            is_hidden_on_main=(name not in NON_HIDDEN_SUBCOMMANDS),
        )


load_legacy_subcommands()
