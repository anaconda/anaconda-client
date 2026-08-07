"""Channel subcommand: anaconda channel <subcommand>.

New subcommands (list, create, show, remove, modify, upload) work with repocore private channels.
Legacy --dashed options (--list, --copy, --show, --lock, --unlock, --remove) are preserved
for backward compatibility and operate on labels via the old API.
"""

import argparse
import logging
import os
from glob import glob
from typing import List, Optional, Tuple, cast

import typer
from rich.panel import Panel

from anaconda_cli_base.console import Table, console, select_from_list
from binstar_client import __version__
from binstar_client.commands import _channel_notices as channel_notices
from binstar_client.commands import upload as upload_mod
from binstar_client.repocore import RepoCoreClient
from binstar_client.repocore.errors import RepoCoreError, Unauthorized
from binstar_client.repocore.package_utils import PackageType, determine_package_type, windows_glob
from binstar_client.repocore.resolve import (
    resolve_channels_with_namespaces as _resolve_channels_with_namespaces,
    resolve_namespace_and_channel as _resolve_namespace_and_channel,
    resolve_no_namespace as _resolve_no_namespace,
)
from binstar_client.utils import get_server_api
from binstar_client.utils.console_utils import configure_console_encoding

__all__ = ["app", "_resolve_namespace_and_channel", "_resolve_no_namespace", "_resolve_channels_with_namespaces"]

logger = logging.getLogger("binstar.channel")

# Ensure Rich box-drawing borders render on Windows legacy code pages instead of
# being emitted as escaped \uXXXX literals (see console_utils for details).
configure_console_encoding()

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

            if os.path.getsize(filepath) == 0:
                console.print(f"[red]Error:[/red] File is empty (0 bytes): {filepath}")
                raise typer.Exit(1)

            pkg_type = determine_package_type(filepath, package_type)

            for ch in resolved_channels:
                _upload_file_to_channel(api, filepath, ch, pkg_type, from_deprecated_channel_flag)


def _upload_to_dotorg(
    files: List[str],
    owner: str,
    labels: List[str],
    org_upload_args,
    package_type: Optional[str] = None,
) -> None:
    """Delegate an owner-only channel upload to the anaconda.org Uploader.

    Reuses the legacy upload path (dotorg has no namespace concept). ``org_upload_args``
    carries the original CLI options when the caller was ``anaconda upload``; otherwise
    a minimal argument set is synthesized from context. ``package_type`` (from
    ``-t/--package-type``) is honored on both paths.
    """
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

    # Honor an explicit --package-type on the direct `channel upload` org route.
    # The Uploader validates it against anaconda.org's own (wider) enum. When the
    # `anaconda upload` bridge supplied the original args, its raw package_type is
    # already present on them, so only the synthesized branch needs this backfill.
    if org_upload_args is None and package_type is not None:
        args.package_type = package_type

    # Expand glob patterns the same way the repo path does (windows_glob is a
    # no-op on POSIX, where the shell already expanded them). Without this, a
    # literal "*.conda" would reach the Uploader unexpanded on Windows.
    expanded = [f for pattern in files for f in windows_glob(pattern)]
    args.files = [[f] for f in expanded]
    args.user = owner
    args.channels = []  # go to the dotorg Uploader, not back through this command
    args.namespace = None
    args.labels = labels

    upload_mod.main(args)


def _iter_all_channels(api):
    """Yield every channel the user can read, paging through ``GET /channels``."""
    offset = 0
    while True:
        channels, total = api.list_all_channels(offset=offset, limit=_PAGE_SIZE)
        yield from channels
        offset += len(channels)
        if not channels or offset >= total:
            break


def _add_repo_rows(table: Table, api, namespace: Optional[str]) -> None:
    """Append anaconda.com (repocore) namespace/channel rows to the table."""
    namespaces: list[str] = []
    subchannels: dict[str, list] = {}
    for channel in _iter_all_channels(api):
        if channel.parent is None:
            # A top-level channel is a namespace header, not a channel row.
            if channel.name not in namespaces:
                namespaces.append(channel.name)
        else:
            subchannels.setdefault(channel.parent, []).append(channel)
            if channel.parent not in namespaces:
                # Shared channel from a namespace we don't own a header for yet.
                namespaces.append(channel.parent)

    if namespace:
        namespaces = [ns for ns in namespaces if ns == namespace]

    for ns in namespaces:
        table.add_row(ns, "", "", "", "")
        for channel in subchannels.get(ns, []):
            table.add_row(
                f"  {channel.path}",
                channel.privacy,
                channel.description,
                str(channel.artifact_count),
                str(channel.download_count),
            )


def _add_org_rows(table: Table, aserver_api) -> None:
    """Append anaconda.org owner rows to the table.

    anaconda.org owners are not repocore channels: they have no namespace and no
    channel-level privacy (both shown as a dash). Labels are intentionally *not*
    listed here — a label is not a channel, and `anaconda channel list` lists
    channels. Use ``anaconda label`` to work with labels.
    """
    login = aserver_api.user()["login"]
    owners = [login]
    try:
        owners += [org["login"] for org in aserver_api.user_orgs()]
    except Exception as exc:
        # Org membership lookup is best-effort; fall back to just the user.
        logger.debug("Could not list anaconda.org organizations, using user only: %s", exc)

    # Group header for the whole anaconda.org section: no namespace exists here,
    # so the Namespace / Channel column is a dash and owners are listed beneath it.
    table.add_row(_NOT_APPLICABLE, _NOT_APPLICABLE, _NOT_APPLICABLE, _NOT_APPLICABLE, _NOT_APPLICABLE)

    for owner in owners:
        table.add_row(
            f"  {owner}",
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
        help="Which channels to list: 'repo' (anaconda.com), 'org' (anaconda.org owners), or 'all'.",
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
            notes.append(f"anaconda.org owners unavailable: {exc}")

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

    # The PUT reports whether it actually changed anything, so a no-op is surfaced
    # rather than a misleading "Success!".
    if privacy:
        result = api.update_channel(name, privacy=privacy)
        if result.changed:
            state_map = {"private": "locked", "authenticated": "soft-locked", "public": "unlocked"}
            console.print(
                f"[green]Success![/green] Channel '[cyan]{name}[/cyan]' is now {state_map[privacy]} ({privacy})."
            )
        else:
            console.print(f"[yellow]No change:[/yellow] Channel '[cyan]{name}[/cyan]' is already {privacy}.")

    if indexing_behavior:
        result = api.update_channel(name, indexing_behavior=indexing_behavior)
        if result.changed:
            state_map = {"frozen": "frozen", "default": "unfrozen"}
            console.print(
                f"[green]Success![/green] Channel '[cyan]{name}[/cyan]' is now {state_map[indexing_behavior]}."
            )
        else:
            console.print(
                f"[yellow]No change:[/yellow] Channel '[cyan]{name}[/cyan]' indexing behavior is already "
                f"{indexing_behavior}."
            )


def _do_upload(
    api,
    files: List[str],
    channels: List[str],
    namespace: Optional[str],
    package_type: Optional[str],
    from_deprecated_channel_flag: bool,
    token_value: Optional[str],
    org_site_value: Optional[str] = None,
    labels: Optional[List[str]] = None,
    org_upload_args: object = None,
) -> None:
    """Classify each channel and upload to anaconda.com and/or anaconda.org.

    Shared by the ``anaconda channel upload`` command and the ``anaconda upload``
    bridge. ``package_type`` is the raw ``--package-type`` string as the user
    typed it (or ``None`` to autodetect); it flows through untouched and is
    validated against each resolved target's own accepted set, since anaconda.com
    and anaconda.org have overlapping-but-different type sets. ``labels``/
    ``org_upload_args`` are only used for owner-only names that route to anaconda.org.
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
        # Each resolved channel carries the set of package types its target
        # accepts. Reject a --package-type only for the targets that actually
        # can't take it — a name may resolve to anaconda.org, which has a
        # different type set, so an "invalid" type there is not an error here.
        offending = next((r for r in repo_targets if not r.accepts_package_type(package_type)), None)
        if offending is not None:
            valid_types = "', '".join(sorted(offending.accepted_package_types))
            console.print(
                f"[red]Error:[/red] Invalid value for '--package-type' / '-t': '{package_type}' "
                f"is not one of '{valid_types}' for anaconda.com repo channels."
            )
            raise typer.Exit(1)

        # Validated above, so the string is a valid repocore type here (or None).
        repo_package_type = PackageType(package_type) if package_type else None
        repo_channels = [f"{r.namespace}/{r.channel_name}" if r.namespace else r.channel_name for r in repo_targets]
        _process_and_upload_files(api, files, repo_channels, repo_package_type, from_deprecated_channel_flag)

    for r in org_targets:
        # ResolvedChannel guarantees a dotorg target carries an owner.
        _upload_to_dotorg(files, cast(str, r.owner), labels, org_upload_args, package_type=package_type)


def upload_command(
    ctx: "typer.Context",
    files: List[str],
    channel: Optional[List[str]] = None,
    namespace: Optional[str] = None,
    package_type: Optional[str] = None,
    from_deprecated_channel_flag: bool = False,
    labels: Optional[List[str]] = None,
    org_upload_args: object = None,
) -> None:
    """Programmatic entry for uploads (used by the ``anaconda upload`` bridge)."""
    token_value = None
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
    token_value = params.get("token")
    # typer validates -t against the repocore enum at the CLI boundary; hand the
    # raw string down so _do_upload can validate per-target uniformly.
    _do_upload(
        ctx.obj.repo_api,
        files,
        channel or [],
        namespace,
        package_type.value if package_type else None,
        from_deprecated_channel_flag=False,
        token_value=token_value,
        org_site_value=params.get("site"),
        labels=label or [],
    )


@app.command(name="share", help="Share a channel with a user")
def share_command(
    ctx: typer.Context,
    user: str = typer.Argument(..., help="User ID, email, or username to share with"),
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
    role: str = typer.Option(
        "viewer",
        "--role",
        "-r",
        help="Role to grant: viewer (read) or collaborator (write). Defaults to viewer.",
    ),
    unshare: bool = typer.Option(False, "--unshare", help="Unshare the channel instead of sharing"),
) -> None:
    """Share a channel with a user."""
    api = ctx.obj.repo_api

    channels = channel or []
    if not channels:
        console.print("[red]Error:[/red] No channel specified. Use --channel option to specify channel(s) to share.")
        raise typer.Exit(1)

    if role not in ("viewer", "collaborator"):
        console.print("[red]Error:[/red] --role must be either 'viewer' or 'collaborator'.")
        raise typer.Exit(1)

    grant = "write" if role == "collaborator" else "read"

    # Sharing is an anaconda.com (repo) concept only; resolve without an owner
    # probe so bare names stay repo channels rather than routing to anaconda.org.
    resolved_channels = _resolve_channels_with_namespaces(api, channels, namespace, False)

    action = "unshare" if unshare else "share"
    for resolved in resolved_channels:
        if not resolved.namespace:
            console.print(
                f"[red]Error:[/red] Could not resolve a namespace for '{resolved.channel_name}'. "
                "Specify one with --namespace or use namespace/channel format."
            )
            raise typer.Exit(1)
        ch = f"{resolved.namespace}/{resolved.channel_name}"
        api.share_channel(resolved.namespace, resolved.channel_name, user, action=action, grant=grant)
        console.print(f"[green]Success![/green] {action.capitalize()}d channel '[cyan]{ch}[/cyan]' with {user}")


channel_notices.mount_notice_subcommand(app)
