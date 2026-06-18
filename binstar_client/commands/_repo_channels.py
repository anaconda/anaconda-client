"""Channels subcommand: anaconda org channels <subcommand>."""

from typing import Optional

import typer
from rich.panel import Panel

from anaconda_cli_base.console import Table, console
from binstar_client.repocore import get_repo_api

app = typer.Typer(
    name="channels",
    help="Manage your Anaconda repository channels",
    no_args_is_help=True,
)


@app.callback(invoke_without_command=True, no_args_is_help=True)
def _callback(ctx: typer.Context) -> None:
    """Initialize repocore API client for channel commands."""
    from anaconda_cli_base.cli import ContextExtras

    if ctx.obj is None:
        ctx.obj = ContextExtras()

    site_value = getattr(ctx.obj, "params", {}).get("at") or getattr(ctx.obj, "params", {}).get("site")

    try:
        ctx.obj.repo_api = get_repo_api(site=site_value)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def _resolve_namespace(api, namespace: Optional[str] = None) -> Optional[str]:
    """Resolve the user's namespace.

    If explicitly provided, return it directly.
    Otherwise look up available top-level channels:
      - one available: return it
      - none available: return None
      - multiple: prompt the user to pick
    """
    if namespace:
        return namespace

    data = api.list_user_channels(offset=0, limit=100)
    namespaces = [ch.get("name", "") for ch in data.get("items", [])]

    if not namespaces:
        return None

    if len(namespaces) == 1:
        return namespaces[0]

    console.print("\nMultiple namespaces available:")
    for i, ns in enumerate(namespaces, 1):
        console.print(f"  {i}. [cyan]{ns}[/cyan]")
    console.print()

    options = {str(i): ns for i, ns in enumerate(namespaces, 1)}
    while True:
        choice = typer.prompt(f"Namespace [1-{len(namespaces)}]")
        if choice in options:
            return options[choice]
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
    namespace = _resolve_namespace(api, namespace)

    if "/" in name:
        namespace, subchannel = name.split("/", 1)
    elif namespace:
        subchannel = name
    else:
        namespace = name
        subchannel = "private"

    if public:
        privacy = "public"
    elif authenticated:
        privacy = "authenticated"
    else:
        privacy = "private"

    manifest = api.create_namespace_channel(namespace=namespace, subchannel_name=subchannel, privacy=privacy)
    channel_path = manifest.get("channel_path", f"{namespace}/{subchannel}")
    console.print(f"[green]Success![/green] Channel '[cyan]{channel_path}[/cyan]' created ({privacy}).")


@app.command(name="remove", help="Remove a channel")
def remove_command(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Channel name to remove"),
    namespace: Optional[str] = typer.Option(None, "--namespace", "-n", help="Namespace the channel belongs to"),
) -> None:
    """Remove a channel."""
    api = ctx.obj.repo_api
    if "/" not in name:
        namespace = _resolve_namespace(api, namespace)
        if not namespace:
            console.print(
                "[red]Error:[/red] No resolvable namespaces. Specify one with --namespace or use namespace/channel format."
            )
            raise typer.Exit(1)
        name = f"{namespace}/{name}"
    api.remove_channel(name)
    console.print(f"[green]Success![/green] Channel '[cyan]{name}[/cyan]' removed.")


@app.command(name="show", help="Show channel information")
def show_command(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Channel name to show"),
    namespace: Optional[str] = typer.Option(None, "--namespace", "-n", help="Namespace the channel belongs to"),
    full_details: bool = typer.Option(False, "--full-details", help="Show full details including subchannels"),
) -> None:
    """Show information about a channel."""
    api = ctx.obj.repo_api
    if "/" not in name:
        namespace = _resolve_namespace(api, namespace)
        if not namespace:
            console.print(
                "[red]Error:[/red] No resolvable namespaces. Specify one with --namespace or use namespace/channel format."
            )
            raise typer.Exit(1)
        name = f"{namespace}/{name}"
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
    if "/" not in name:
        namespace = _resolve_namespace(api, namespace)
        if not namespace:
            console.print(
                "[red]Error:[/red] No resolvable namespaces. Specify one with --namespace or use namespace/channel format."
            )
            raise typer.Exit(1)
        name = f"{namespace}/{name}"

    if privacy:
        api.update_channel(name, privacy=privacy)
        state_map = {"private": "locked", "authenticated": "soft-locked", "public": "unlocked"}
        console.print(f"[green]Success![/green] Channel '[cyan]{name}[/cyan]' is now {state_map[privacy]} ({privacy}).")

    if indexing_behavior:
        api.update_channel(name, indexing_behavior=indexing_behavior)
        state_map = {"frozen": "frozen", "default": "unfrozen"}
        console.print(f"[green]Success![/green] Channel '[cyan]{name}[/cyan]' is now {state_map[indexing_behavior]}.")
