"""Channel subcommand: anaconda channel <subcommand>.

New subcommands (list, create, show, remove, modify) work with repocore private channels.
Legacy --dashed options (--list, --copy, --show, --lock, --unlock, --remove) are preserved
for backward compatibility and operate on labels via the old API.
"""

import argparse
from typing import Optional, Tuple

import typer
from rich.panel import Panel

from anaconda_cli_base.console import Table, console
from binstar_client import __version__
from binstar_client.repocore import RepoCoreClient

app = typer.Typer(
    name="channel",
    help="Manage your Anaconda repository channels",
    invoke_without_command=True,
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)


@app.callback(invoke_without_command=True)
def _callback(
    ctx: typer.Context,
    organization: Optional[str] = typer.Option(None, "-o", "--organization", hidden=True),
    copy: Tuple[str, str] = typer.Option(("", ""), "--copy", hidden=True, show_default=False),
    list_: bool = typer.Option(False, "--list", hidden=True),
    show_legacy: Optional[str] = typer.Option(None, "--show", hidden=True),
    lock: Optional[str] = typer.Option(None, "--lock", hidden=True),
    unlock: Optional[str] = typer.Option(None, "--unlock", hidden=True),
    remove_legacy: Optional[str] = typer.Option(None, "--remove", hidden=True),
) -> None:
    """Manage your Anaconda repository channels."""
    from anaconda_cli_base.cli import ContextExtras

    if ctx.obj is None:
        ctx.obj = ContextExtras()

    parsed_copy = list(copy) if copy != ("", "") else None
    legacy_actions = [
        ("'--list'", list_),
        ("'--copy'", parsed_copy),
        ("'--show'", show_legacy),
        ("'--lock'", lock),
        ("'--unlock'", unlock),
        ("'--remove'", remove_legacy),
    ]
    active_legacy = [name for name, val in legacy_actions if val]

    if len(active_legacy) > 1:
        raise typer.BadParameter(f"Invalid value for {active_legacy[1]}: mutually exclusive with {active_legacy[0]}")

    if active_legacy:
        from binstar_client.commands.channel import main

        args = argparse.Namespace(
            token=ctx.obj.params.get("token"),
            site=ctx.obj.params.get("site"),
            organization=organization,
            copy=parsed_copy,
            list=list_,
            show=show_legacy,
            lock=lock,
            unlock=unlock,
            remove=remove_legacy,
        )
        main(args, name="channel", deprecated=True)
        raise typer.Exit(0)

    if organization and not active_legacy:
        raise typer.BadParameter("one of --copy, --list, --show, --lock, --unlock, or --remove must be provided")

    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        raise typer.Exit(0)

    site_value = getattr(ctx.obj, "params", {}).get("at") or getattr(ctx.obj, "params", {}).get("site")

    try:
        ctx.obj.repo_api = RepoCoreClient(site=site_value, version=__version__)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def _resolve_namespace_and_channel(
    api, name: str, namespace: Optional[str] = None, require_namespace: bool = True
) -> tuple:
    """Resolve namespace and channel name from the given inputs.

    Returns (namespace, channel_name). namespace may be None if require_namespace=False
    and no namespaces are available (lets create delegate to the API).

    Resolution order:
      1. name contains "/" AND --namespace provided → error (ambiguous)
      2. name contains "/" → split into namespace/channel
      3. --namespace provided → use it, name is the channel
      4. Neither → resolve namespace from API via user's top-level channels
    """
    if "/" in name and namespace:
        console.print("[red]Error:[/red] Ambiguous: name contains '/' but --namespace was also provided.")
        raise typer.Exit(1)

    if "/" in name:
        parts = name.split("/", 1)
        return (parts[0], parts[1])

    if namespace:
        return (namespace, name)

    # Resolve from API
    data = api.list_user_channels(offset=0, limit=100)
    namespaces = [ch.get("name", "") for ch in data.get("items", [])]

    if not namespaces:
        if require_namespace:
            console.print(
                "[red]Error:[/red] No resolvable namespaces. Specify one with --namespace or use namespace/channel format."
            )
            raise typer.Exit(1)
        return (None, name)

    if len(namespaces) == 1:
        return (namespaces[0], name)

    console.print("\nMultiple namespaces available:")
    for i, ns in enumerate(namespaces, 1):
        console.print(f"  {i}. [cyan]{ns}[/cyan]")
    console.print()

    options = {str(i): ns for i, ns in enumerate(namespaces, 1)}
    while True:
        choice = typer.prompt(f"Namespace [1-{len(namespaces)}]")
        if choice in options:
            return (options[choice], name)
        console.print(f"[red]Invalid choice.[/red] Please enter 1-{len(namespaces)}.")


@app.command(name="list", help="List all channels")
def list_command(
    ctx: typer.Context,
    namespace: Optional[str] = typer.Option(None, "--namespace", "-n", help="Filter to a specific namespace"),
    offset: int = typer.Option(0, "--offset", "-o", help="Offset when displaying results"),
    limit: int = typer.Option(50, "--limit", "-l", help="Limit when displaying results"),
) -> None:
    """List all channels for the current user."""
    api = ctx.obj.repo_api
    data = api.list_user_channels(offset, limit)

    channels = data.get("items", [])
    if namespace:
        channels = [ch for ch in channels if ch.get("name", "") == namespace]

    table = Table(title="Channels")
    table.add_column("Namespace / Channel", style="cyan")
    table.add_column("Privacy")
    table.add_column("Description")
    table.add_column("Artifacts", justify="right")
    table.add_column("Downloads", justify="right")

    for ch in channels:
        channel_name = ch.get("name", "")
        table.add_row(
            channel_name,
            ch.get("privacy", ""),
            ch.get("description", "") or "",
            str(ch.get("artifact_count", 0)),
            str(ch.get("download_count", 0)),
        )
        if ch.get("subchannel_count", 0) > 0:
            subchannels = api.get_channel_subchannels(channel_name)
            for sub in subchannels.get("items", []):
                table.add_row(
                    f"  {channel_name}/{sub.get('name', '')}",
                    sub.get("privacy", ""),
                    sub.get("description", "") or "",
                    str(sub.get("artifact_count", 0)),
                    str(sub.get("download_count", 0)),
                )

    console.print(table)


@app.command(name="create", help="Create a new channel")
def create_command(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Channel name to create (or namespace/channel)"),
    namespace: Optional[str] = typer.Option(None, "--namespace", "-n", help="Namespace to create the channel under"),
    private: bool = typer.Option(False, "--private", help="Create as a private channel (default)"),
    authenticated: bool = typer.Option(False, "--authenticated", help="Create as an authenticated channel"),
    public: bool = typer.Option(False, "--public", help="Create as a public channel"),
) -> None:
    """Create a new channel."""
    flags = sum([private, authenticated, public])
    if flags > 1:
        console.print("[red]Error:[/red] --private, --authenticated, and --public are mutually exclusive.")
        raise typer.Exit(1)

    api = ctx.obj.repo_api
    namespace, subchannel = _resolve_namespace_and_channel(api, name, namespace, require_namespace=False)

    if public:
        privacy = "public"
    elif authenticated:
        privacy = "authenticated"
    else:
        privacy = "private"

    manifest = api.create_namespace_channel(subchannel_name=subchannel, namespace=namespace, privacy=privacy)
    channel_path = manifest["channel_path"]
    console.print(f"[green]Success![/green] Channel '[cyan]{channel_path}[/cyan]' created ({privacy}).")


@app.command(name="remove", help="Remove a channel")
def remove_command(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Channel name to remove"),
    namespace: Optional[str] = typer.Option(None, "--namespace", "-n", help="Namespace the channel belongs to"),
) -> None:
    """Remove a channel."""
    api = ctx.obj.repo_api
    ns, channel = _resolve_namespace_and_channel(api, name, namespace)
    qualified = f"{ns}/{channel}"
    api.remove_channel(qualified)
    console.print(f"[green]Success![/green] Channel '[cyan]{qualified}[/cyan]' removed.")


@app.command(name="show", help="Show channel information")
def show_command(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Channel name to show"),
    namespace: Optional[str] = typer.Option(None, "--namespace", "-n", help="Namespace the channel belongs to"),
    full_details: bool = typer.Option(False, "--full-details", help="Show full details including subchannels"),
) -> None:
    """Show information about a channel."""
    api = ctx.obj.repo_api
    ns, channel = _resolve_namespace_and_channel(api, name, namespace)
    name = f"{ns}/{channel}"
    channel_data = api.get_channel(name)

    if full_details and not api.is_subchannel(name):
        channel_data["subchannels"] = api.get_channel_subchannels(name)

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Field", style="bold cyan")
    table.add_column("Value")

    fields = [
        ("Name", channel_data.get("name", "")),
        ("Description", channel_data.get("description", "") or ""),
        ("Privacy", channel_data.get("privacy", "")),
        ("Artifacts", str(channel_data.get("artifact_count", 0))),
        ("Downloads", str(channel_data.get("download_count", 0))),
        ("Mirrors", str(channel_data.get("mirror_count", 0))),
        ("Subchannels", str(channel_data.get("subchannel_count", 0))),
        ("Indexing", channel_data.get("indexing_behavior", "")),
        ("Created", channel_data.get("created", "")),
        ("Updated", channel_data.get("updated", "")),
    ]

    owners = [o for o in channel_data.get("owners", []) if o]
    if owners:
        fields.append(("Owners", ", ".join(owners)))

    for field, value in fields:
        table.add_row(field, str(value))

    console.print(Panel(table, title=f"Channel: {name}", border_style="green"))

    if full_details and "subchannels" in channel_data:
        subchannels = channel_data["subchannels"].get("items", [])
        if subchannels:
            console.print("\n[bold]Subchannels:[/bold]")
            sub_table = Table()
            sub_table.add_column("Name", style="cyan")
            sub_table.add_column("Privacy")
            sub_table.add_column("Artifacts", justify="right")
            for sub in subchannels:
                sub_table.add_row(
                    sub.get("name", ""),
                    sub.get("privacy", ""),
                    str(sub.get("artifact_count", 0)),
                )
            console.print(sub_table)


@app.command(name="modify", help="Modify channel settings")
def modify_command(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Channel name to modify"),
    namespace: Optional[str] = typer.Option(None, "--namespace", "-n", help="Namespace the channel belongs to"),
    privacy: Optional[str] = typer.Option(
        None, "--privacy", help="Set channel privacy: public, authenticated, or private"
    ),
    indexing_behavior: Optional[str] = typer.Option(
        None, "--indexing-behavior", help="Set indexing behavior: default or frozen"
    ),
) -> None:
    """Modify channel settings (privacy, indexing behavior)."""
    valid_privacy = ("public", "authenticated", "private")
    valid_indexing = ("default", "frozen")

    if privacy and privacy not in valid_privacy:
        console.print(f"[red]Error:[/red] --privacy must be one of: {', '.join(valid_privacy)}")
        raise typer.Exit(1)

    if indexing_behavior and indexing_behavior not in valid_indexing:
        console.print(f"[red]Error:[/red] --indexing-behavior must be one of: {', '.join(valid_indexing)}")
        raise typer.Exit(1)

    if not privacy and not indexing_behavior:
        console.print("[red]Error:[/red] At least one option is required (--privacy or --indexing-behavior).")
        raise typer.Exit(1)

    api = ctx.obj.repo_api
    ns, channel = _resolve_namespace_and_channel(api, name, namespace)
    name = f"{ns}/{channel}"

    if privacy:
        api.update_channel(name, privacy=privacy)
        state_map = {"private": "locked", "authenticated": "soft-locked", "public": "unlocked"}
        console.print(f"[green]Success![/green] Channel '[cyan]{name}[/cyan]' is now {state_map[privacy]} ({privacy}).")

    if indexing_behavior:
        api.update_channel(name, indexing_behavior=indexing_behavior)
        state_map = {"frozen": "frozen", "default": "unfrozen"}
        console.print(f"[green]Success![/green] Channel '[cyan]{name}[/cyan]' is now {state_map[indexing_behavior]}.")
