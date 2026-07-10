"""Channel subcommand: anaconda channel <subcommand>.

New subcommands (list, create, show, remove, modify, upload) work with repocore private channels.
Legacy --dashed options (--list, --copy, --show, --lock, --unlock, --remove) are preserved
for backward compatibility and operate on labels via the old API.
"""

import argparse
import os
from glob import glob
from typing import List, Optional, Tuple

import typer
from rich.panel import Panel

from anaconda_cli_base.console import Table, console, select_from_list
from binstar_client import __version__
from binstar_client.commands import _channel_notices as channel_notices
from binstar_client.repocore import RepoCoreClient, ResolvedChannel
from binstar_client.repocore.errors import RepoCoreError, Unauthorized
from binstar_client.repocore.package_utils import PackageType, determine_package_type, windows_glob

_PAGE_SIZE = 100

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


def _resolve_no_namespace(api, name: str) -> ResolvedChannel:
    """Resolve no namespaces case

    Returns ResolvedChannel with namespace and channel_name.

    Checks for username:
      1. If None or get user request errors, return empty namespace
      2. If truthy ask user to confirm creation of new namespace

    """
    try:
        username = (api.account.get("user") or {}).get("username") or ""
    except Exception:
        username = ""

    if username:
        confirm = typer.confirm(
            f"No namespaces found. A namespace can be created with your username. Use your username '{username}' as the namespace?"
        )
        if confirm:
            return ResolvedChannel(namespace=username, channel_name=name)
        raise typer.Exit(0)
    return ResolvedChannel(namespace=None, channel_name=name)


def _resolve_channels_with_namespaces(
    api, channels: List[str], namespace: Optional[str], from_deprecated_channel_flag: bool
) -> List[str]:
    """Resolve channel names to fully qualified namespace/channel format.

    Returns list of resolved channel paths like 'namespace/channel' or 'channel'.
    """
    resolved_channels = []
    for ch in channels:
        try:
            resolved = _resolve_namespace_and_channel(api, ch, namespace, require_namespace=False)
        except (typer.Exit, SystemExit):
            if from_deprecated_channel_flag:
                console.print("-c/--channel no longer equals labels, did you mean --label?")
            raise
        if resolved.namespace:
            full_channel = f"{resolved.namespace}/{resolved.channel_name}"
        else:
            full_channel = resolved.channel_name
        resolved_channels.append(full_channel)
        console.print(f"Resolved channel: [cyan]{full_channel}[/cyan]")
    return resolved_channels


def _upload_file_to_channel(
    api, filepath: str, channel: str, pkg_type: str, from_deprecated_channel_flag: bool
) -> None:
    """Upload a single file to a single channel."""
    console.print(f"Uploading [cyan]{filepath}[/cyan] to channel [cyan]{channel}[/cyan]...")

    try:
        response = api.upload_file(filepath, channel, pkg_type)

        if response.status_code in [200, 201]:
            console.print(f"[green]Success![/green] Uploaded {filepath} to {channel}")
        elif response.status_code == 401:
            raise Unauthorized()
        elif response.status_code == 404:
            msg = f"[red]Error:[/red] Channel '{channel}' not found (404)."
            if from_deprecated_channel_flag:
                msg += "\n-c/--channel no longer equals labels, did you mean --label?"
            console.print(msg)
            raise typer.Exit(1)
        else:
            console.print(
                f"[red]Error:[/red] Failed to upload {filepath}\n"
                f"Status: {response.status_code}\n"
                f"Details: {response.content.decode()}"
            )
    except Unauthorized as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except RepoCoreError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def _process_and_upload_files(
    api,
    file_patterns: List[str],
    resolved_channels: List[str],
    package_type: Optional[PackageType],
    from_deprecated_channel_flag: bool,
) -> None:
    """Process file patterns and upload each file to all resolved channels."""
    for file_pattern in file_patterns:
        for filepath in windows_glob(file_pattern):
            if not os.path.exists(filepath):
                console.print(f"[yellow]Warning:[/yellow] File not found: {filepath}")
                continue

            pkg_type = determine_package_type(filepath, package_type)

            for ch in resolved_channels:
                _upload_file_to_channel(api, filepath, ch, pkg_type, from_deprecated_channel_flag)


def _resolve_namespace_and_channel(
    api, name: str, namespace: Optional[str] = None, require_namespace: bool = True
) -> ResolvedChannel:
    """Resolve namespace and channel name from the given inputs.

    Returns ResolvedChannel with namespace and channel_name. namespace may be None if require_namespace=False
    and no namespaces are available (lets create delegate to the API).

    Resolution order:
      1. name contains "/" AND --namespace provided → error (ambiguous)
      2. name contains "/" → split into namespace/channel
      3. --namespace provided → use it, name is the channel
      4. Neither → resolve namespace from API via user's top-level channels
      5. Calls _resolve_no_namespace if none are present
    """
    if "/" in name and namespace:
        console.print("[red]Error:[/red] Ambiguous: name contains '/' but --namespace was also provided.")
        raise typer.Exit(1)

    if "/" in name:
        parts = name.split("/", 1)
        return ResolvedChannel(namespace=parts[0], channel_name=parts[1])

    if namespace:
        return ResolvedChannel(namespace=namespace, channel_name=name)

    # Resolve from API
    orgs = api.list_user_organizations()
    namespaces = [org.name for org in orgs]

    if not namespaces:
        if require_namespace:
            console.print(
                "[red]Error:[/red] No resolvable namespaces. Specify one with --namespace or use namespace/channel format."
            )
            raise typer.Exit(1)

        return _resolve_no_namespace(api, name)

    if len(namespaces) == 1:
        return ResolvedChannel(namespace=namespaces[0], channel_name=name)

    console.print()
    selected_namespace = select_from_list("Select namespace:", namespaces)
    return ResolvedChannel(namespace=selected_namespace, channel_name=name)


@app.command(name="list", help="List all channels")
def list_command(
    ctx: typer.Context,
    namespace: Optional[str] = typer.Option(None, "--namespace", "-n", help="Filter to a specific namespace"),
) -> None:
    """List all channels for the current user."""
    api = ctx.obj.repo_api
    orgs = api.list_user_organizations()

    if namespace:
        orgs = [org for org in orgs if org.name == namespace]

    table = Table(title="Channels")
    table.add_column("Namespace / Channel", style="cyan")
    table.add_column("Privacy")
    table.add_column("Description")
    table.add_column("Artifacts", justify="right")
    table.add_column("Downloads", justify="right")

    for org in orgs:
        table.add_row(org.name, "", "", "", "")

        sub_offset = 0
        while True:
            try:
                channels = api.get_channels(org.name, offset=sub_offset, limit=_PAGE_SIZE)
            except Exception:
                # Namespace may not have any channels yet in the repo
                break
            for channel in channels:
                table.add_row(
                    f"  {org.name}/{channel.name}",
                    channel.privacy,
                    channel.description,
                    str(channel.artifact_count),
                    str(channel.download_count),
                )
            if len(channels) < _PAGE_SIZE:
                break
            sub_offset += len(channels)

    if console.height and table.row_count > console.height:
        with console.pager():
            console.print(table)
    else:
        console.print(table)


@app.command(name="create", help="Create a new channel")
def create_command(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Channel name to create (or namespace/channel)"),
    namespace: Optional[str] = typer.Option(None, "--namespace", "-n", help="Namespace to create the channel under"),
    private: bool = typer.Option(False, "--private", help="Create as a private channel (default)"),
    public: bool = typer.Option(False, "--public", help="Create as a public channel"),
) -> None:
    """Create a new channel."""
    flags = sum([private, public])
    if flags > 1:
        console.print("[red]Error:[/red] --private and --public are mutually exclusive.")
        raise typer.Exit(1)

    api = ctx.obj.repo_api
    resolved = _resolve_namespace_and_channel(api, name, namespace, require_namespace=False)

    if public:
        privacy = "public"
    elif private:
        privacy = "private"
    else:
        console.print()
        privacy = select_from_list("Channel privacy:", ["private", "public"])
    response = api.create_namespace_channel(
        channel_name=resolved.channel_name, namespace=resolved.namespace, privacy=privacy
    )
    console.print(f"[green]Success![/green] Channel '[cyan]{response['channel_path']}[/cyan]' created ({privacy}).")


@app.command(name="remove", help="Remove a channel")
def remove_command(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Channel name to remove"),
    namespace: Optional[str] = typer.Option(None, "--namespace", "-n", help="Namespace the channel belongs to"),
) -> None:
    """Remove a channel."""
    api = ctx.obj.repo_api
    resolved = _resolve_namespace_and_channel(api, name, namespace)
    qualified = f"{resolved.namespace}/{resolved.channel_name}"
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
    resolved = _resolve_namespace_and_channel(api, name, namespace)
    name = f"{resolved.namespace}/{resolved.channel_name}"
    channel_data = api.get_namespace_channel(name)

    subchannels_response = None
    if full_details and not api.is_subchannel(name):
        subchannels_response = api.get_channels(name)

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Field", style="bold cyan")
    table.add_column("Value")

    fields = [
        ("Name", channel_data.name),
        ("Description", channel_data.description),
        ("Privacy", channel_data.privacy),
        ("Artifacts", str(channel_data.artifact_count)),
        ("Downloads", str(channel_data.download_count)),
        ("Mirrors", str(channel_data.mirror_count)),
        ("Indexing", channel_data.indexing_behavior),
        ("Created", channel_data.created),
        ("Updated", channel_data.updated),
    ]

    if channel_data.owners:
        fields.append(("Owners", ", ".join(channel_data.owners)))

    for field, value in fields:
        table.add_row(field, str(value))

    console.print(Panel(table, title=f"Channel: {name}", border_style="green"))

    if subchannels_response:
        console.print("\n[bold]Subchannels:[/bold]")
        sub_table = Table()
        sub_table.add_column("Name", style="cyan")
        sub_table.add_column("Privacy")
        sub_table.add_column("Artifacts", justify="right")
        for sub in subchannels_response:
            sub_table.add_row(
                sub.name,
                sub.privacy,
                str(sub.artifact_count),
            )
        console.print(sub_table)


@app.command(name="modify", help="Modify channel settings")
def modify_command(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Channel name to modify"),
    namespace: Optional[str] = typer.Option(None, "--namespace", "-n", help="Namespace the channel belongs to"),
    privacy: Optional[str] = typer.Option(None, "--privacy", "-p", help="Set channel privacy: public or private"),
    indexing_behavior: Optional[str] = typer.Option(
        None, "--indexing-behavior", "-i", help="Set indexing behavior: default or frozen"
    ),
) -> None:
    """Modify channel settings (privacy, indexing behavior)."""
    valid_privacy = ("public", "private")
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
    resolved = _resolve_namespace_and_channel(api, name, namespace)
    name = f"{resolved.namespace}/{resolved.channel_name}"

    if privacy:
        api.update_channel(name, privacy=privacy)
        state_map = {"private": "locked", "authenticated": "soft-locked", "public": "unlocked"}
        console.print(f"[green]Success![/green] Channel '[cyan]{name}[/cyan]' is now {state_map[privacy]} ({privacy}).")

    if indexing_behavior:
        api.update_channel(name, indexing_behavior=indexing_behavior)
        state_map = {"frozen": "frozen", "default": "unfrozen"}
        console.print(f"[green]Success![/green] Channel '[cyan]{name}[/cyan]' is now {state_map[indexing_behavior]}.")


@app.command(name="upload", help="Upload packages to channels")
def upload_command(
    ctx: typer.Context,
    files: List[str] = typer.Argument(
        ...,
        help="Files to upload",
    ),
    channel: Optional[List[str]] = typer.Option(
        None,
        "--channel",
        "-c",
        help="Target channel(s) in format 'namespace/channel' or 'channel'. Can be specified multiple times.",
    ),
    namespace: Optional[str] = typer.Option(
        None,
        "--namespace",
        "-n",
        help="Namespace for the channel (alternative to namespace/channel format)",
    ),
    package_type: Optional[PackageType] = typer.Option(
        None,
        "--package-type",
        "-t",
        help="Package type. Defaults to auto-detect.",
    ),
    from_deprecated_channel_flag: bool = False,
) -> None:
    """Upload packages to your Anaconda repository."""
    if ctx is None:
        from anaconda_cli_base.cli import ContextExtras
        from binstar_client import __version__

        ctx_obj = ContextExtras()
        ctx_obj.repo_api = RepoCoreClient(version=__version__)

        class FakeContext:
            obj = ctx_obj

        ctx = FakeContext()

    api = ctx.obj.repo_api

    channels = channel or []
    if not channels:
        console.print("[red]Error:[/red] No channel specified. Use --channel option to specify target channel(s).")
        raise typer.Exit(1)

    resolved_channels = _resolve_channels_with_namespaces(api, channels, namespace, from_deprecated_channel_flag)
    _process_and_upload_files(api, files, resolved_channels, package_type, from_deprecated_channel_flag)


@app.command(name="share", help="Share a channel with a user")
def share_command(
    ctx: typer.Context,
    user_email: str = typer.Argument(..., help="Email of the user to share with"),
    channel: Optional[List[str]] = typer.Option(
        None,
        "--channel",
        "-c",
        help="Channel(s) to share in format 'namespace/channel' or 'channel'. Can be specified multiple times.",
    ),
    namespace: Optional[str] = typer.Option(
        None,
        "--namespace",
        "-n",
        help="Namespace for the channel (alternative to namespace/channel format)",
    ),
) -> None:
    """Share a channel with a user."""
    api = ctx.obj.repo_api

    channels = channel or []
    if not channels:
        console.print("[red]Error:[/red] No channel specified. Use --channel option to specify channel(s) to share.")
        raise typer.Exit(1)

    resolved_channels = _resolve_channels_with_namespaces(api, channels, namespace, False)

    for ch in resolved_channels:
        try:
            api.share_channel(ch, user_email)
            console.print(f"[green]Success![/green] Shared channel '[cyan]{ch}[/cyan]' with {user_email}")
        except NotImplementedError as e:
            console.print(f"[yellow]Note:[/yellow] {e}")
            raise typer.Exit(1)
        except RepoCoreError as e:
            console.print(f"[red]Error:[/red] Failed to share channel {ch}: {e}")
            raise typer.Exit(1)


channel_notices.mount_notice_subcommand(app)
