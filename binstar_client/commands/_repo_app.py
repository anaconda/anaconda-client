"""Typer app for the `anaconda repo` subcommand (repocore channels)."""

from typing import Optional

import typer
from anaconda_cli_base.console import console

from binstar_client.commands._repo_channels import app as channels_app
from binstar_client.commands._repo_upload import app as upload_app
from binstar_client.repocore.config import get_repo_api

app = typer.Typer(
    add_completion=False,
    help="Interact with Anaconda repository channels",
    no_args_is_help=True,
)


@app.callback(invoke_without_command=True, no_args_is_help=True)
def _callback(
    ctx: typer.Context,
    site: Optional[str] = typer.Option(
        None, "-s", "--site", help="Select the anaconda-client site to use", hidden=True
    ),
) -> None:
    """Anaconda Repository CLI - manage channels, packages, and more."""
    from anaconda_cli_base.cli import ContextExtras

    ctx.obj = ctx.obj or ContextExtras()

    site_value = site or ctx.obj.params.get("at")

    try:
        ctx.obj.repo_api = get_repo_api(site=site_value)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


app.add_typer(channels_app)
app.add_typer(upload_app)
