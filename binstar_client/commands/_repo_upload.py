"""Upload subcommand for repocore: anaconda repo upload <files>."""

import os
from enum import Enum
from glob import glob
from typing import List, Optional

import typer

from anaconda_cli_base.console import console

from binstar_client.repocore.detect import detect_package_type
from binstar_client.repocore.errors import Unauthorized

app = typer.Typer(
    name="upload",
    help="Upload packages to your repository",
    no_args_is_help=True,
)


class PackageType(str, Enum):
    env = "env"
    ipynb = "ipynb"
    conda = "conda"
    pypi = "pypi"
    project = "project"
    sdist = "sdist"
    gra = "gra"


def _windows_glob(item: str) -> List[str]:
    if os.name == "nt" and "*" in item:
        return glob(item)
    return [item]


def _determine_package_type(filename: str, package_type: Optional[PackageType] = None) -> str:
    if package_type:
        return package_type.value

    console.print(f"Detecting file type for [cyan]{filename}[/cyan]...")
    detected_type = detect_package_type(filename)

    if detected_type is None:
        console.print(
            f"[red]Error:[/red] Could not detect package type for '{filename}'.\n"
            "Please specify package type with --package-type option.\n"
            "For General Artifacts, use: --package-type gra"
        )
        raise typer.Exit(1)

    console.print(f"Detected type: [green]{detected_type}[/green]")
    return detected_type


@app.callback(invoke_without_command=True)
def upload_command(
    ctx: typer.Context,
    files: List[str] = typer.Argument(..., help="Files to upload"),
    channel: Optional[List[str]] = typer.Option(
        None, "--channel", "-c", help="Target channel(s). Can be specified multiple times."
    ),
    package_type: Optional[PackageType] = typer.Option(
        None, "--package-type", "-t", help="Package type. Defaults to auto-detect."
    ),
    name: Optional[str] = typer.Option(
        None, "--name", "-n", help="Package name (required for General Artifacts)"
    ),
    version: Optional[str] = typer.Option(
        None, "--version", "-v", help="Package version (for General Artifacts)"
    ),
) -> None:
    """Upload packages to your Anaconda repository."""
    api = ctx.obj.repo_api
    channels = channel or []

    if not channels:
        default_channel = api.get_default_channel()
        if not default_channel:
            console.print(
                "[red]Error:[/red] No channel specified and user has no default channel.\n"
                "Please set a default channel in your account or use --channel option."
            )
            raise typer.Exit(1)
        channels = [default_channel]
        console.print(f"Using default channel: [cyan]{default_channel}[/cyan]")

    for file_pattern in files:
        for filepath in _windows_glob(file_pattern):
            if not os.path.exists(filepath):
                console.print(f"[yellow]Warning:[/yellow] File not found: {filepath}")
                continue

            pkg_type = _determine_package_type(filepath, package_type)

            if pkg_type == PackageType.gra.value and not name:
                console.print(
                    "[red]Error:[/red] Name is required for General Artifacts.\n"
                    "Please provide a name with --name option."
                )
                raise typer.Exit(1)

            for ch in channels:
                console.print(f"Uploading [cyan]{filepath}[/cyan] to channel [cyan]{ch}[/cyan]...")

                try:
                    response = api.upload_file(filepath, ch, pkg_type, name, version)

                    if response.status_code in [200, 201]:
                        console.print(f"[green]Success![/green] Uploaded {filepath} to {ch}")
                    elif response.status_code == 401:
                        raise Unauthorized()
                    else:
                        try:
                            detail = response.json()
                            error_msg = detail.get("message") or detail.get("detail") or str(detail)
                        except (ValueError, KeyError):
                            error_msg = f"status {response.status_code}"
                        console.print(f"[red]Error:[/red] Failed to upload {filepath}: {error_msg}")
                except Unauthorized:
                    console.print(
                        "[red]Error:[/red] Authentication failed. Please run 'anaconda login'."
                    )
                    raise typer.Exit(1)
