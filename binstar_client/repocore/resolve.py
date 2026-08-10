"""Shared namespace/channel resolution for anaconda.com (repocore) uploads.

Extracted from ``binstar_client.commands._repo_channels`` so both the
``anaconda channel`` subcommands and the top-level ``anaconda upload`` command
can share a single resolver.
"""

import sys
from typing import Callable, FrozenSet, List, Optional

import typer

from anaconda_cli_base.console import console, select_from_list
from binstar_client.repocore.models import ResolvedChannel
from binstar_client.repocore.package_utils import PackageType as RepoPackageType
from binstar_client.utils.config import PackageType as OrgPackageType

# A callable that reports whether ``name`` is a valid anaconda.org owner
# (user or organization). Injected by callers so this module stays free of
# client imports and circular dependencies.
OwnerProbe = Callable[[str], bool]

# The accepted ``--package-type`` values for each target, derived from the two
# enums so they stay in sync with the source of truth. Stamped onto each
# ResolvedChannel so callers validate generically instead of re-encoding the
# per-target type rules. anaconda.com and anaconda.org overlap but neither is a
# superset (e.g. repo has "sdist"; org has "ipynb"/"file"/"env").
REPO_PACKAGE_TYPES: FrozenSet[str] = frozenset(pt.value for pt in RepoPackageType)
ORG_PACKAGE_TYPES: FrozenSet[str] = frozenset(pt.value for pt in OrgPackageType)


def _repo_channel(namespace: Optional[str], channel_name: str) -> ResolvedChannel:
    """Build a repocore (anaconda.com) ResolvedChannel with its accepted types."""
    return ResolvedChannel(
        namespace=namespace,
        channel_name=channel_name,
        target="repo",
        accepted_package_types=REPO_PACKAGE_TYPES,
    )


def _org_channel(owner: str, channel_name: str) -> ResolvedChannel:
    """Build an anaconda.org ResolvedChannel with its accepted types."""
    return ResolvedChannel(
        namespace=None,
        channel_name=channel_name,
        target="org",
        owner=owner,
        accepted_package_types=ORG_PACKAGE_TYPES,
    )


_CHANNEL_PAGE_SIZE = 100


def _iter_readable_channels(api):
    """Yield every channel the caller can read (own + shared), paging ``GET /channels``.

    ``include_subchannels=True`` so the listing carries both top-level channels
    (a namespace: ``parent is None``) and subchannels (an actual channel, whose
    namespace is its ``parent``). The server scopes the result to the token's
    permissions, so this spans the user's own channels plus any shared with it.
    """
    offset = 0
    while True:
        channels, total, error = api.list_all_channels(
            offset=offset, limit=_CHANNEL_PAGE_SIZE, include_subchannels=True
        )
        if error:
            raise error
        yield from channels
        offset += len(channels)
        # Stop on an empty/short page too, so an over-reported total can't loop forever.
        if not channels or len(channels) < _CHANNEL_PAGE_SIZE or offset >= total:
            break


def _readable_namespaces(channels) -> List[str]:
    """The distinct namespaces present in a readable-channel listing.

    A top-level channel is itself a namespace; a subchannel's namespace is its
    ``parent``. Order is preserved and duplicates dropped so the picker is stable.
    """
    namespaces: List[str] = []
    for channel in channels:
        ns = channel.namespace or channel.name
        if ns not in namespaces:
            namespaces.append(ns)
    return namespaces


def resolve_no_namespace(api, name: str) -> ResolvedChannel:
    """Resolve the no-namespaces case.

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
            return _repo_channel(namespace=username, channel_name=name)
        raise typer.Exit(0)
    return _repo_channel(namespace=None, channel_name=name)


def resolve_namespace_and_channel(
    api, name: str, namespace: Optional[str] = None, require_namespace: bool = True
) -> ResolvedChannel:
    """Resolve namespace and channel name from the given inputs.

    Returns ResolvedChannel with namespace and channel_name. namespace may be None if require_namespace=False
    and no namespaces are available (lets create delegate to the API).

    Resolution order:
      1. name contains "/" AND --namespace provided → error (ambiguous)
      2. name contains "/" → split into namespace/channel
      3. --namespace provided → use it, name is the channel
      4. Neither → match the bare name against readable subchannels (own +
         shared): exactly one match resolves to that namespace/channel directly,
         several prompt among the full paths
      5. No existing subchannel matches → resolve the namespace instead (one
         auto-resolves, several prompt), so a new channel name still resolves
      6. Calls resolve_no_namespace if no namespaces are present
    """
    if "/" in name and namespace:
        console.print(f"[red]Error:[/red] Ambiguous: '{name}' contains '/' but --namespace was also provided.")
        raise typer.Exit(1)

    if "/" in name:
        parts = name.split("/", 1)
        return _repo_channel(namespace=parts[0], channel_name=parts[1])

    if namespace:
        return _repo_channel(namespace=namespace, channel_name=name)

    # List every channel the caller can read — its own *and* any shared with it —
    # so both existing-channel matching and namespace resolution see shared items.
    channels = list(_iter_readable_channels(api))

    # First, does the bare name already name a subchannel? A subchannel is an
    # actual channel (has a parent namespace); a top-level channel is a namespace,
    # not a channel target. If exactly one subchannel matches, resolve it directly
    # even when several namespaces exist — it's unambiguous (e.g. dude/imhungry).
    subchannel_matches = [c for c in channels if c.namespace and c.name == name]
    if len(subchannel_matches) == 1:
        chosen = subchannel_matches[0]
        return _repo_channel(namespace=chosen.namespace, channel_name=chosen.name)
    if len(subchannel_matches) > 1:
        # The same channel name under more than one readable namespace: disambiguate
        # by full path (e.g. dude/imhungry vs fluffybunnies/imhungry).
        console.print()
        paths = [c.path for c in subchannel_matches]
        selected_path = select_from_list(f"Select channel for '{name}':", paths)
        chosen = next(c for c in subchannel_matches if c.path == selected_path)
        return _repo_channel(namespace=chosen.namespace, channel_name=chosen.name)

    # No existing channel by that name — resolve the namespace it should live
    # under, so a brand-new channel name (e.g. `create`) still resolves.
    namespaces = _readable_namespaces(channels)

    if not namespaces:
        if require_namespace:
            console.print(
                "[red]Error:[/red] No resolvable namespaces. Specify one with --namespace or use namespace/channel format."
            )
            raise typer.Exit(1)

        return resolve_no_namespace(api, name)

    if len(namespaces) == 1:
        return _repo_channel(namespace=namespaces[0], channel_name=name)

    console.print()
    selected_namespace = select_from_list(f"Select namespace for channel '{name}':", namespaces)
    return _repo_channel(namespace=selected_namespace, channel_name=name)


def _prompt_repo_or_org(name: str) -> str:
    """Prompt to disambiguate a name matching both systems. Returns 'repo' or 'org'.

    The interactive selector reads raw keystrokes, which is impossible without a
    terminal. When stdin is not a TTY (pipelines, CI), refuse to guess and tell
    the user how to be explicit instead.
    """
    if not sys.stdin.isatty():
        console.print(
            f'[red]Error:[/red] "{name}" matches both an anaconda.com namespace and an '
            "anaconda.org owner, and there is no terminal to disambiguate.\n"
            f'Use "{name}/<channel>" for an anaconda.com channel, or "-u {name}" '
            "with anaconda upload for anaconda.org."
        )
        raise typer.Exit(1)

    console.print()
    console.print(f'"{name}" matches both an anaconda.com namespace and an anaconda.org owner.')
    return select_from_list(
        f'Where should "{name}" be uploaded?',
        [
            ("repo", f'anaconda.com repo namespace "{name}"'),
            ("org", f'anaconda.org owner "{name}"'),
        ],
    )


def classify_and_resolve(
    api,
    name: str,
    namespace: Optional[str] = None,
    owner_probe: Optional[OwnerProbe] = None,
) -> ResolvedChannel:
    """Resolve ``name`` to an upload target, spanning anaconda.com and anaconda.org.

    ``a/b`` is always an anaconda.com namespace/channel. A bare ``a`` is a *channel*,
    never a namespace: we find which namespace it lives under. When a bare name also
    names an anaconda.org owner, we disambiguate:

      * matches an anaconda.org owner AND a readable anaconda.com namespace -> prompt
      * matches only an anaconda.org owner                                  -> target="org"
      * otherwise -> anaconda.com channel resolution (existing behavior)

    Returns a ResolvedChannel whose ``target`` field says which system to use.
    """
    # Qualified names and explicit namespaces are unambiguously anaconda.com.
    if "/" in name or namespace:
        return resolve_namespace_and_channel(api, name, namespace, require_namespace=False)

    org_match = owner_probe is not None and owner_probe(name)

    repo_match = False
    if org_match:
        # Only fetch the (possibly expensive) channel listing to detect a real
        # collision — where the bare name already *names* something on anaconda.com:
        # a top-level namespace, or an existing readable subchannel by that name.
        # The namespace *fallback* (placing a brand-new channel under some namespace)
        # is not a collision: with no such name present, an org owner routes to org.
        try:
            channels = list(_iter_readable_channels(api))
            repo_match = any(c.name == name for c in channels)
        except Exception:
            repo_match = False

    if org_match and repo_match:
        if _prompt_repo_or_org(name) == "org":
            return _org_channel(owner=name, channel_name=name)
    elif org_match:
        return _org_channel(owner=name, channel_name=name)

    # anaconda.com: treat the bare name as a channel and resolve its namespace.
    return resolve_namespace_and_channel(api, name, namespace, require_namespace=False)


def resolve_channels_with_namespaces(
    api,
    channels: List[str],
    namespace: Optional[str],
    from_deprecated_channel_flag: bool,
    owner_probe: Optional[OwnerProbe] = None,
) -> List[ResolvedChannel]:
    """Resolve channel names to :class:`ResolvedChannel` targets.

    Each result carries a ``target`` of "repo" or "org"; callers dispatch on it.
    """
    resolved_channels = []
    for ch in channels:
        try:
            resolved = classify_and_resolve(api, ch, namespace, owner_probe=owner_probe)
        except (typer.Exit, SystemExit):
            if from_deprecated_channel_flag:
                console.print("-c/--channel no longer equals labels, did you mean --label?")
            raise
        if resolved.target == "org":
            console.print(f"Resolved to anaconda.org owner: [cyan]{resolved.owner}[/cyan]")
        else:
            if resolved.namespace:
                full_channel = f"{resolved.namespace}/{resolved.channel_name}"
            else:
                full_channel = resolved.channel_name
            console.print(f"Resolved channel: [cyan]{full_channel}[/cyan]")
        resolved_channels.append(resolved)
    return resolved_channels
