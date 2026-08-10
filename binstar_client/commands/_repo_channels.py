"""Channel subcommand: anaconda channel <subcommand>.

New subcommands (list, create, show, remove, modify, upload) work with repocore private channels.
Legacy --dashed options (--list, --copy, --show, --lock, --unlock, --remove) are preserved
for backward compatibility and operate on labels via the old API.
"""

import argparse
import logging
import os
import re
from glob import glob
from typing import List, Optional, Tuple, cast

import typer
from pydantic import BaseModel
from rich.panel import Panel

from anaconda_cli_base.console import Table, console, select_from_list
from binstar_client import __version__
from binstar_client.commands import _channel_notices as channel_notices
from binstar_client.commands import remove as remove_mod
from binstar_client.commands import show as show_mod
from binstar_client.commands import upload as upload_mod
from binstar_client.repocore import RepoCoreClient
from binstar_client.repocore.errors import RepoCoreError, Unauthorized
from binstar_client.repocore.telemetry import ChannelEvents, UploadEvents
from binstar_client.repocore.package_utils import PackageType, determine_package_type, windows_glob
from binstar_client.repocore.resolve import (
    classify_and_resolve,
    resolve_channels_with_namespaces as _resolve_channels_with_namespaces,
    resolve_namespace_and_channel as _resolve_namespace_and_channel,
    resolve_no_namespace as _resolve_no_namespace,
)
from binstar_client.utils import get_server_api, parse_specs
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


class _DotOrgCredentials(BaseModel):
    """The ``--token``/``--site`` pair plus the anaconda.org owner probe built from them.

    Shared by the ``show``, ``upload``, and ``remove-package`` commands to route a
    bare name to anaconda.org (dotorg) when it matches an owner there.

    ``--at`` selects the anaconda.com (repo) domain and is NOT a valid anaconda.org
    site alias, so only ``--site`` is carried here as ``site``.
    """

    token: Optional[str] = None
    site: Optional[str] = None

    @classmethod
    def from_ctx(cls, ctx) -> "_DotOrgCredentials":
        """Read ``--token``/``--site`` off the command context's params."""
        params = getattr(ctx.obj, "params", {})
        return cls(token=params.get("token"), site=params.get("site"))

    def owner_probe(self, name: str) -> bool:
        """Whether ``name`` is a real anaconda.org owner (user or organization)."""
        try:
            aserver_api = get_server_api(self.token, self.site)
            aserver_api.user(name)
            return True
        except Exception:
            return False


def _extract_limit_from_error(error: Exception) -> Optional[int]:
    """Extract channel limit number from error message."""
    limit_match = re.search(r'has reached the limit of (\d+)', str(error))
    return int(limit_match.group(1)) if limit_match else None


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
    _, error = api.upload_file(filepath, channel, pkg_type)
    package_name = os.path.basename(filepath)
    UploadEvents.uploaded(
        api, app.info.name, channel=channel, package_type=pkg_type, package_name=package_name, error=bool(error)
    )
    if error:
        raise error
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
        channels, total, error = api.list_all_channels(offset=offset, limit=_PAGE_SIZE)
        if error:
            raise error
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
    error_occurred = False

    if source in ("all", "repo"):
        try:
            _add_repo_rows(table, ctx.obj.repo_api, namespace)
        except Exception as exc:
            notes.append(f"repo channels unavailable: {exc}")
            error_occurred = True

    if source in ("all", "org"):
        try:
            params = getattr(ctx.obj, "params", {})
            aserver_api = get_server_api(params.get("token"), params.get("site"))
            _add_org_rows(table, aserver_api)
        except Exception as exc:
            notes.append(f"anaconda.org owners unavailable: {exc}")
            error_occurred = True

    channel_path = namespace if namespace else "all"
    ChannelEvents.accessed(
        ctx.obj.repo_api, app.info.name, channel_path=channel_path, action="list", error=error_occurred
    )

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
    response, error = api.create_namespace_channel(
        channel_name=resolved.channel_name, namespace=resolved.namespace, privacy=privacy
    )
    channel_path = f"{resolved.namespace}/{resolved.channel_name}" if resolved.namespace else resolved.channel_name
    operation_org_id = getattr(response, 'org_id', None) if response else None
    event_kwargs = {
        "api": api,
        "app_name": app.info.name,
        "channel_path": channel_path,
        "privacy": privacy,
        "operation_org_id": operation_org_id,
        "error": bool(error),
    }
    if error:
        error_msg = str(error).lower()
        if "limit" in error_msg and "private" in error_msg:
            limit_value = _extract_limit_from_error(error)
            ChannelEvents.limit(api, app.info.name, channel_path=channel_path, action="create", limit=limit_value)
        ChannelEvents.created(**event_kwargs)
        raise error
    if response.created:
        ChannelEvents.created(**event_kwargs)
        console.print(f"[green]Success![/green] Channel '[cyan]{response.channel_path}[/cyan]' created ({privacy}).")
    else:
        ChannelEvents.created_exists(**event_kwargs)
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
    _, error = api.remove_channel(qualified)
    ChannelEvents.removed(api, app.info.name, channel_path=qualified, error=bool(error))
    if error:
        raise error
    console.print(f"[green]Success![/green] Channel '[cyan]{qualified}[/cyan]' removed.")


@app.command(name="show", help="Show channel information")
def show_command(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Channel name to show"),
    namespace: Optional[str] = typer.Option(None, "--namespace", "-n", help="Namespace the channel belongs to"),
    full_details: bool = typer.Option(False, "--full-details", help="Show full details including subchannels"),
    packages: bool = typer.Option(False, "--packages", "-p", help="Also list the packages in the channel."),
    files: bool = typer.Option(
        False,
        "--files",
        help="Also list individual files (with the exact filename to remove) instead of a package summary.",
    ),
) -> None:
    """Show information about a channel.

    Like ``channel upload``, this proxies across systems: a bare ``name`` that
    matches an anaconda.org owner routes to anaconda.org (delegating to the
    legacy ``anaconda show``); otherwise it targets an anaconda.com (repocore)
    channel.

    By default this prints channel metadata only. ``--packages/-p`` appends a
    package summary; ``--files`` appends a per-file listing (with the exact
    filename to pass to ``remove-package``). The two listing flags are alternatives.
    """
    # --packages/-p and --files pick the listing format; reject both at once
    # rather than silently letting one win.
    if packages and files:
        console.print("[red]Error:[/red] --packages/-p and --files are mutually exclusive; specify at most one.")
        raise typer.Exit(1)

    api = ctx.obj.repo_api
    dotorg_creds = _DotOrgCredentials.from_ctx(ctx)

    # Classify the name the same way `channel upload`/`remove-package` do: a bare
    # name matching an anaconda.org owner routes to dotorg, otherwise anaconda.com.
    resolved = classify_and_resolve(api, name, namespace, owner_probe=dotorg_creds.owner_probe)

    if resolved.target == "org":
        # anaconda.org packages/files listings don't apply; `anaconda show OWNER`
        # already lists the owner's packages.
        _show_dotorg(cast(str, resolved.owner), dotorg_creds.token, dotorg_creds.site)
        return

    name = f"{resolved.namespace}/{resolved.channel_name}" if resolved.namespace else resolved.channel_name
    channel_data, error = api.get_namespace_channel(name)
    ChannelEvents.accessed(api, app.info.name, channel_path=name, action="show", error=bool(error))
    if error:
        raise error

    subchannels_response = None
    if full_details and not api.is_subchannel(name):
        subchannels_response, error = api.get_channels(name)
        if error:
            raise error

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

    if packages or files:
        console.print()
        _render_package_listing(api, name, files)


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
        result, error = api.update_channel(name, privacy=privacy)
        if error:
            error_msg = str(error).lower()
            if "limit" in error_msg and "private" in error_msg:
                limit_value = _extract_limit_from_error(error)
                ChannelEvents.limit(api, app.info.name, channel_path=name, action="modify", limit=limit_value)
        ChannelEvents.modified(api, app.info.name, channel_path=name, privacy=privacy, error=bool(error))
        if error:
            raise error
        if result.changed:
            state_map = {"private": "locked", "authenticated": "soft-locked", "public": "unlocked"}
            console.print(
                f"[green]Success![/green] Channel '[cyan]{name}[/cyan]' is now {state_map[privacy]} ({privacy})."
            )
        else:
            console.print(f"[yellow]No change:[/yellow] Channel '[cyan]{name}[/cyan]' is already {privacy}.")

    if indexing_behavior:
        result, error = api.update_channel(name, indexing_behavior=indexing_behavior)
        ChannelEvents.modified(
            api, app.info.name, channel_path=name, indexing_behavior=indexing_behavior, error=bool(error)
        )
        if error:
            raise error
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
    dotorg_creds: _DotOrgCredentials,
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

    resolved = _resolve_channels_with_namespaces(
        api, channels, namespace, from_deprecated_channel_flag, owner_probe=dotorg_creds.owner_probe
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
    if ctx is None:
        from anaconda_cli_base.cli import ContextExtras
        from binstar_client import __version__

        # Carry --site/--token from the `anaconda upload` bridge, if provided.
        site_value = getattr(org_upload_args, "site", None)
        dotorg_creds = _DotOrgCredentials(token=getattr(org_upload_args, "token", None), site=site_value)

        ctx_obj = ContextExtras()
        ctx_obj.repo_api = RepoCoreClient(site=site_value, version=__version__)

        class FakeContext:
            obj = ctx_obj

        ctx = FakeContext()
    else:
        dotorg_creds = _DotOrgCredentials.from_ctx(ctx)

    _do_upload(
        ctx.obj.repo_api,
        files,
        channel or [],
        namespace,
        package_type,
        from_deprecated_channel_flag,
        dotorg_creds,
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
    # typer validates -t against the repocore enum at the CLI boundary; hand the
    # raw string down so _do_upload can validate per-target uniformly.
    _do_upload(
        ctx.obj.repo_api,
        files,
        channel or [],
        namespace,
        package_type.value if package_type else None,
        from_deprecated_channel_flag=False,
        dotorg_creds=_DotOrgCredentials.from_ctx(ctx),
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
        result, error = api.share_channel(resolved.namespace, resolved.channel_name, user, action=action, grant=grant)
        event_kwargs = {"api": api, "app_name": app.info.name, "channel_path": ch, "user": user, "error": bool(error)}
        if action == "share":
            ChannelEvents.share(**event_kwargs, role=role)
        else:
            ChannelEvents.unshare(**event_kwargs)
        if error:
            raise error
        console.print(f"[green]Success![/green] {action.capitalize()}d channel '[cyan]{ch}[/cyan]' with {user}")


def _iter_all_artifacts(api, channel: str):
    """Yield every package (artifact) in ``channel``, paging through the listing."""
    offset = 0
    while True:
        artifacts, total = api.list_artifacts(channel, offset=offset, limit=_PAGE_SIZE)
        yield from artifacts
        offset += len(artifacts)
        # Stop on an empty/short page too, so an over-reported total can't loop forever.
        if not artifacts or len(artifacts) < _PAGE_SIZE or offset >= total:
            break


def _iter_artifact_files(api, channel: str, family: str, name: str):
    """Yield every file of one package in ``channel``, paging through the listing."""
    offset = 0
    while True:
        files, total = api.list_artifact_files(channel, family, name, offset=offset, limit=_PAGE_SIZE)
        yield from files
        offset += len(files)
        # Stop on an empty/short page too, so an over-reported total can't loop forever.
        if not files or len(files) < _PAGE_SIZE or offset >= total:
            break


def _find_file_by_name(api, channel: str, filename: str):
    """Find the (family, name, ckey) of a package file by its bare filename.

    Scans the channel's packages and their files, matching on the ckey basename.
    Returns a list of matching ``(family, name, ckey)`` tuples so the caller can
    report ambiguity (the same filename under more than one package/subdir).
    """
    matches: List[Tuple[str, str, str]] = []
    for artifact in _iter_all_artifacts(api, channel):
        for f in _iter_artifact_files(api, channel, artifact.family, artifact.name):
            if f.filename == filename:
                matches.append((artifact.family, artifact.name, f.ckey))
    return matches


def _fmt_size(num_bytes: int) -> str:
    """Human-readable byte size for the files table."""
    size = float(num_bytes or 0)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def _render_package_listing(api, channel: str, files: bool) -> None:
    """Print the package (or, with ``files``, per-file) listing for a channel.

    The package summary shows one row per package. ``files=True`` drills into
    every file so the exact filename to pass to ``remove-package`` is visible.
    Long listings page through the console.
    """
    if files:
        table = Table(title=f"Files in {channel}")
        table.add_column("Filename", style="cyan")
        table.add_column("Package")
        table.add_column("Family")
        table.add_column("Size", justify="right")
        row_count = 0
        for artifact in _iter_all_artifacts(api, channel):
            for f in _iter_artifact_files(api, channel, artifact.family, artifact.name):
                table.add_row(f.filename, f.name or artifact.name, f.family or artifact.family, _fmt_size(f.size))
                row_count += 1
    else:
        table = Table(title=f"Packages in {channel}")
        table.add_column("Package", style="cyan")
        table.add_column("Family")
        table.add_column("Versions", justify="right")
        table.add_column("Files", justify="right")
        table.add_column("Downloads", justify="right")
        row_count = 0
        for artifact in _iter_all_artifacts(api, channel):
            table.add_row(
                artifact.name,
                artifact.family,
                str(len(artifact.available_versions)),
                str(artifact.file_count),
                str(artifact.download_count),
            )
            row_count += 1

    if row_count == 0:
        console.print(f"No packages found in [cyan]{channel}[/cyan].")
        return

    if console.height and table.row_count > console.height:
        with console.pager():
            console.print(f"[dim]Showing {table.row_count} rows — ↑/↓ to scroll, press q to quit.[/dim]")
            console.print(table)
    else:
        console.print(table)


def _remove_from_repo(api, channel: str, target: str, force: bool) -> None:
    """Remove a single file (by filename) from an anaconda.com repo channel.

    ``target`` is the bare filename; it is resolved to its file (ckey) by
    scanning the channel, then removed via the bulk endpoint so only that one
    file goes, not the whole package.
    """
    matches = _find_file_by_name(api, channel, target)
    if not matches:
        console.print(
            f"[red]Error:[/red] No file named '[cyan]{target}[/cyan]' found in channel '[cyan]{channel}[/cyan]'. "
            f"Run 'anaconda channel view -c {channel} --files' to list removable filenames."
        )
        raise typer.Exit(1)
    if len(matches) > 1:
        console.print(f"[red]Error:[/red] '{target}' matches more than one file in '{channel}':")
        for family, name, ckey in matches:
            console.print(f"  - {family}/{name}: [cyan]{ckey}[/cyan]")
        console.print("This is unexpected for a single filename; contact support if it persists.")
        raise typer.Exit(1)

    family, name, ckey = matches[0]

    if not force:
        console.print(f"About to remove [cyan]{ckey}[/cyan] ({family}/{name}) from [cyan]{channel}[/cyan].")
        if not typer.confirm("Are you sure?"):
            raise typer.Exit(0)

    api.delete_artifact_file(channel, family, name, ckey)
    console.print(f"[green]Success![/green] Removed [cyan]{target}[/cyan] from '[cyan]{channel}[/cyan]'.")


def _ensure_binstar_console_logging() -> None:
    """Make the legacy ``binstar`` logger print to the console at INFO.

    The delegated legacy commands (``show``/``remove``) write their user-facing
    output via ``logging`` at INFO. Under the standalone ``binstar`` entrypoint
    that logger is configured by ``setup_logging``; but when we call their
    ``main()`` from inside the ``anaconda channel`` Typer app nothing has
    configured it, so INFO records are dropped (the logger defaults to WARNING
    with no handler) and the command appears to print nothing. Install a plain
    console handler at INFO once, only if none is already attached.
    """
    binstar_logger = logging.getLogger("binstar")
    if binstar_logger.level == logging.NOTSET or binstar_logger.level > logging.INFO:
        binstar_logger.setLevel(logging.INFO)
    if not any(isinstance(h, logging.StreamHandler) for h in binstar_logger.handlers):
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter("%(message)s"))
        binstar_logger.addHandler(handler)


def _show_dotorg(owner: str, token_value, org_site_value) -> None:
    """Delegate a channel show for an anaconda.org owner to the legacy ``show`` path.

    anaconda.org has no repocore channel metadata; ``anaconda show OWNER`` lists
    the owner's packages, which is the closest equivalent — the same proxying
    ``channel upload`` does for owner-only names.
    """
    # show.main emits its listing through the binstar logger at INFO; ensure it
    # reaches the console when invoked via this Typer app (see helper).
    _ensure_binstar_console_logging()
    args = argparse.Namespace(
        token=token_value,
        site=org_site_value,
        spec=parse_specs(owner),
    )
    show_mod.main(args)


def _remove_from_dotorg(owner: str, target: str, token_value, org_site_value, force: bool) -> None:
    """Delegate a package removal to the anaconda.org ``remove`` path.

    anaconda.org has no bare-filename delete; its grammar is
    ``owner/package/version/filename``. The ``target`` is the part after the
    owner (``-c owner`` supplies the owner), so we reconstruct the full spec and
    hand it to the legacy remove command — the same proxying ``channel upload``
    does for owner-only names.
    """
    spec = target if target.startswith(f"{owner}/") else f"{owner}/{target}"
    args = argparse.Namespace(
        token=token_value,
        site=org_site_value,
        specs=[parse_specs(spec)],
        force=force,
    )
    remove_mod.main(args)


@app.command(name="remove-package", help="Remove a package file from a channel")
def remove_package_command(
    ctx: typer.Context,
    target: str = typer.Argument(
        ...,
        metavar="PACKAGE",
        help=(
            "For an anaconda.com channel: the package filename to remove "
            "(e.g. numpy-2.2.5-py313h51bfb38_3.conda). For an anaconda.org owner: "
            "the package spec 'package/version/filename'."
        ),
    ),
    channel: Optional[List[str]] = typer.Option(
        None,
        "--channel",
        "-c",
        help="Channel 'namespace/channel'/'channel', or an anaconda.org owner.",
    ),
    namespace: Optional[str] = typer.Option(None, "--namespace", "-n", help="Namespace the channel belongs to"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip the confirmation prompt."),
) -> None:
    """Remove a single package file from a channel.

    Like ``channel upload``, this proxies across systems: a ``-c`` value that names
    an anaconda.org owner routes to anaconda.org; otherwise it targets an
    anaconda.com (repocore) channel. On anaconda.com a package spans many files, so
    removal targets one file — the filename is resolved to its file (ckey) by
    scanning the channel; run ``anaconda channel view -c CHANNEL --files`` to see
    removable filenames.
    """
    channels = channel or []
    if not channels:
        console.print("[red]Error:[/red] No channel specified. Use --channel/-c to specify a channel.")
        raise typer.Exit(1)
    if len(channels) > 1:
        console.print("[red]Error:[/red] remove-package accepts a single channel; specify -c once.")
        raise typer.Exit(1)

    api = ctx.obj.repo_api
    dotorg_creds = _DotOrgCredentials.from_ctx(ctx)

    # Classify the -c target the same way `channel upload` does: a bare name that
    # matches an anaconda.org owner routes to dotorg, otherwise anaconda.com.
    resolved = classify_and_resolve(api, channels[0], namespace, owner_probe=dotorg_creds.owner_probe)

    if resolved.target == "org":
        _remove_from_dotorg(cast(str, resolved.owner), target, dotorg_creds.token, dotorg_creds.site, force)
        return

    channel_path = f"{resolved.namespace}/{resolved.channel_name}" if resolved.namespace else resolved.channel_name
    _remove_from_repo(api, channel_path, target, force)


channel_notices.mount_notice_subcommand(app)
