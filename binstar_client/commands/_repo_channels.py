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
from binstar_client.repocore import RepoCoreClient
from binstar_client.repocore.errors import RepoCoreError, Unauthorized
from binstar_client.repocore.package_utils import PackageType, determine_package_type, windows_glob
from binstar_client.repocore.resolve import (
    resolve_channels_with_namespaces as _resolve_channels_with_namespaces,
    resolve_namespace_and_channel as _resolve_namespace_and_channel,
    resolve_no_namespace as _resolve_no_namespace,
)
from binstar_client.utils import get_server_api

__all__ = ["app", "_resolve_namespace_and_channel", "_resolve_no_namespace", "_resolve_channels_with_namespaces"]

# Value shown in a column where the concept does not exist for that source.
# anaconda.org labels have no namespace and no channel-level privacy.
_NOT_APPLICABLE = "—"

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


def _upload_file_to_channel(
    api, filepath: str, channel: str, pkg_type: str, from_deprecated_channel_flag: bool
) -> None:
    """Upload a single file to a single channel."""
    console.print(f"Uploading [cyan]{filepath}[/cyan] to channel [cyan]{channel}[/cyan]...")
    api.upload_file(filepath, channel, pkg_type)
    console.print(f"[green]Success![/green] Uploaded {filepath} to {channel}")


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


def _upload_to_dotorg(files: List[str], owner: str, labels: List[str], org_upload_args) -> None:
    """Delegate an owner-only channel upload to the anaconda.org Uploader.

    Reuses the legacy upload path (dotorg has no namespace concept). ``org_upload_args``
    carries the original CLI options when the caller was ``anaconda upload``; otherwise
    a minimal argument set is synthesized from context.
    """
    import argparse

    from binstar_client.commands.upload import main as upload_main

    if org_upload_args is not None:
        args = argparse.Namespace(**vars(org_upload_args))
    else:
        # Direct `anaconda channel upload` invocation: build a minimal set of args.
        # channel upload intentionally does not expose the full anaconda.org option
        # surface (--private, -p, -v, -s, -d, mode flags); use `anaconda upload -c`
        # for those. Everything here is defaulted.
        args = argparse.Namespace(
            token=None,
            site=None,
            disable_ssl_warnings=False,
            show_traceback=False,
            no_progress=False,
            keep_basename=False,
            package=None,
            version=None,
            summary=None,
            package_type=None,
            description=None,
            thumbnail=None,
            private=False,
            auto_register=True,
            build_id=None,
            mode=None,
            force_metadata_update=False,
        )

    args.files = [[f] for f in files]
    args.user = owner
    args.channels = []  # go to the dotorg Uploader, not back through this command
    args.namespace = None
    args.labels = labels
    upload_main(args)


def _add_repo_rows(table: Table, api, namespace: Optional[str]) -> None:
    """Append anaconda.com (repocore) namespace/channel rows to the table."""
    orgs = api.list_user_organizations()
    if namespace:
        orgs = [org for org in orgs if org.name == namespace]

    for org in orgs:
        table.add_row(org.name, "repo", "", "", "", "")

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
                    "repo",
                    channel.privacy,
                    channel.description,
                    str(channel.artifact_count),
                    str(channel.download_count),
                )
            if len(channels) < _PAGE_SIZE:
                break
            sub_offset += len(channels)


def _add_org_rows(table: Table, aserver_api) -> None:
    """Append anaconda.org owner/label rows to the table.

    Labels are not channels: they have no namespace (shown as a dash) and no
    channel-level privacy. Each owner's labels are rendered as ``owner · label``
    so they never read as a repocore ``namespace/channel`` path.
    """
    login = aserver_api.user()["login"]
    owners = [login]
    try:
        owners += [org["login"] for org in aserver_api.user_orgs()]
    except Exception:
        # Org membership lookup is best-effort; fall back to just the user.
        pass

    # Group header for the whole anaconda.org section: no namespace exists here.
    table.add_row(_NOT_APPLICABLE, "org", "", "", "", "")

    for owner in owners:
        labels = aserver_api.list_channels(owner)
        for label, info in labels.items():
            if isinstance(info, int):  # OLD API returns a count instead of a dict
                locked = False
            else:
                locked = bool(info.get("is_locked"))
            display = f"  {owner} · {label}"
            if locked:
                display += " [locked]"
            table.add_row(
                display,
                "org",
                _NOT_APPLICABLE,
                _NOT_APPLICABLE,
                _NOT_APPLICABLE,
                _NOT_APPLICABLE,
            )


@app.command(name="list", help="List all channels")
def list_command(
    ctx: typer.Context,
    namespace: Optional[str] = typer.Option(None, "--namespace", "-n", help="Filter to a specific namespace"),
    source: str = typer.Option(
        "all",
        "--source",
        help="Which channels to list: 'repo' (anaconda.com), 'org' (anaconda.org labels), or 'all'.",
    ),
) -> None:
    """List all channels for the current user."""
    if source not in ("all", "repo", "org"):
        console.print("[red]Error:[/red] --source must be one of: all, repo, org")
        raise typer.Exit(1)

    if namespace and source == "org":
        console.print("[yellow]Note:[/yellow] --namespace only applies to repo channels; ignored for --source org.")

    table = Table(title="Channels")
    table.add_column("Namespace / Channel", style="cyan")
    table.add_column("Source")
    table.add_column("Privacy")
    table.add_column("Description")
    table.add_column("Artifacts", justify="right")
    table.add_column("Downloads", justify="right")

    notes: List[str] = []

    if source in ("all", "repo"):
        try:
            _add_repo_rows(table, ctx.obj.repo_api, namespace)
        except Exception as exc:
            notes.append(f"repo channels unavailable: {exc}")

    if source in ("all", "org"):
        try:
            params = getattr(ctx.obj, "params", {})
            aserver_api = get_server_api(params.get("token"), params.get("site"))
            _add_org_rows(table, aserver_api)
        except Exception as exc:
            notes.append(f"anaconda.org labels unavailable: {exc}")

    def _render() -> None:
        console.print(table)
        for note in notes:
            console.print(f"[dim]{note}[/dim]")

    if console.height and table.row_count > console.height:
        with console.pager():
            console.print(f"[dim]Showing {table.row_count} rows — ↑/↓ to scroll, press q to quit.[/dim]")
            _render()
    else:
        _render()


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
    if response.created:
        console.print(f"[green]Success![/green] Channel '[cyan]{response.channel_path}[/cyan]' created ({privacy}).")
    else:
        console.print(f"Channel '[cyan]{response.channel_path}[/cyan]' already exists.")


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


def _do_upload(
    api,
    files: List[str],
    channels: List[str],
    namespace: Optional[str],
    package_type: Optional[PackageType],
    from_deprecated_channel_flag: bool,
    token_value: Optional[str],
    site_value: Optional[str],
    org_site_value: Optional[str] = None,
    labels: Optional[List[str]] = None,
    org_upload_args: object = None,
) -> None:
    """Classify each channel and upload to anaconda.com and/or anaconda.org.

    Shared by the ``anaconda channel upload`` command and the ``anaconda upload``
    bridge. ``labels``/``org_upload_args`` are only used for owner-only names that
    route to anaconda.org.
    """
    labels = labels or []

    if not channels:
        console.print("[red]Error:[/red] No channel specified. Use --channel option to specify target channel(s).")
        raise typer.Exit(1)

    # Probe used to detect anaconda.org owners so a bare name can route to dotorg.
    # Note: ``--at`` selects the anaconda.com (repo) domain and is NOT a valid
    # anaconda.org site alias, so it must not be forwarded here.
    def _owner_probe(name: str) -> bool:
        try:
            aserver_api = get_server_api(token_value, org_site_value)
            aserver_api.user(name)
            return True
        except Exception:
            return False

    resolved = _resolve_channels_with_namespaces(
        api, channels, namespace, from_deprecated_channel_flag, owner_probe=_owner_probe
    )

    org_targets = [r for r in resolved if r.target == "org"]
    repo_targets = [r for r in resolved if r.target != "org"]

    if repo_targets:
        # -l/--label has no meaning for repo channels. When a single invocation
        # targets both repo and org (multiple -c flags), the label still applies
        # to the org targets, so warn rather than error and upload to both.
        if labels:
            console.print(
                "[yellow]Note:[/yellow] -l/--label is ignored for repo channels; "
                "labels apply only to anaconda.org uploads."
            )
        repo_channels = [f"{r.namespace}/{r.channel_name}" if r.namespace else r.channel_name for r in repo_targets]
        _process_and_upload_files(api, files, repo_channels, package_type, from_deprecated_channel_flag)

    for r in org_targets:
        _upload_to_dotorg(files, r.owner, labels, org_upload_args)


def upload_command(
    ctx: "typer.Context",
    files: List[str],
    channel: Optional[List[str]] = None,
    namespace: Optional[str] = None,
    package_type: Optional[PackageType] = None,
    from_deprecated_channel_flag: bool = False,
    labels: Optional[List[str]] = None,
    org_upload_args: object = None,
) -> None:
    """Programmatic entry for uploads (used by the ``anaconda upload`` bridge)."""
    token_value = None
    site_value = None
    org_site_value = None
    if ctx is None:
        from anaconda_cli_base.cli import ContextExtras
        from binstar_client import __version__

        # Carry --site/--token from the `anaconda upload` bridge, if provided.
        token_value = getattr(org_upload_args, "token", None)
        site_value = getattr(org_upload_args, "site", None)
        org_site_value = site_value  # `anaconda upload --site` is an anaconda.org alias

        ctx_obj = ContextExtras()
        ctx_obj.repo_api = RepoCoreClient(site=site_value, version=__version__)

        class FakeContext:
            obj = ctx_obj

        ctx = FakeContext()
    else:
        params = getattr(ctx.obj, "params", {})
        site_value = params.get("at") or params.get("site")
        token_value = params.get("token")
        # --at selects the anaconda.com domain; only --site is an anaconda.org alias.
        org_site_value = params.get("site")

    _do_upload(
        ctx.obj.repo_api,
        files,
        channel or [],
        namespace,
        package_type,
        from_deprecated_channel_flag,
        token_value,
        site_value,
        org_site_value=org_site_value,
        labels=labels,
        org_upload_args=org_upload_args,
    )


@app.command(name="upload", help="Upload packages to channels")
def _upload_cli(
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
    label: Optional[List[str]] = typer.Option(
        None,
        "--label",
        "-l",
        help="anaconda.org label to apply (only when the target resolves to anaconda.org).",
    ),
    package_type: Optional[PackageType] = typer.Option(
        None,
        "--package-type",
        "-t",
        help="Package type. Defaults to auto-detect.",
    ),
) -> None:
    """Upload packages to your Anaconda repository."""
    params = getattr(ctx.obj, "params", {})
    site_value = params.get("at") or params.get("site")
    token_value = params.get("token")
    _do_upload(
        ctx.obj.repo_api,
        files,
        channel or [],
        namespace,
        package_type,
        from_deprecated_channel_flag=False,
        token_value=token_value,
        site_value=site_value,
        org_site_value=params.get("site"),
        labels=label or [],
    )


channel_notices.mount_notice_subcommand(app)
