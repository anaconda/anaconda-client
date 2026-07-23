"""Shared namespace/channel resolution for anaconda.com (repocore) uploads.

Extracted from ``binstar_client.commands._repo_channels`` so both the
``anaconda channel`` subcommands and the top-level ``anaconda upload`` command
can share a single resolver.
"""

import sys
from typing import Callable, List, Optional

import typer

from anaconda_cli_base.console import console, select_from_list
from binstar_client.repocore.models import ResolvedChannel

# A callable that reports whether ``name`` is a valid anaconda.org owner
# (user or organization). Injected by callers so this module stays free of
# client imports and circular dependencies.
OwnerProbe = Callable[[str], bool]


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
            return ResolvedChannel(namespace=username, channel_name=name)
        raise typer.Exit(0)
    return ResolvedChannel(namespace=None, channel_name=name)


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
      4. Neither → resolve namespace from API via user's top-level channels
      5. Calls resolve_no_namespace if none are present
    """
    if "/" in name and namespace:
        console.print(f"[red]Error:[/red] Ambiguous: '{name}' contains '/' but --namespace was also provided.")
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

        return resolve_no_namespace(api, name)

    if len(namespaces) == 1:
        return ResolvedChannel(namespace=namespaces[0], channel_name=name)

    console.print()
    selected_namespace = select_from_list(f"Select namespace for channel '{name}':", namespaces)
    return ResolvedChannel(namespace=selected_namespace, channel_name=name)


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

      * matches an anaconda.org owner AND an anaconda.com namespace -> prompt
      * matches only an anaconda.org owner                          -> target="org"
      * otherwise -> anaconda.com channel resolution (existing behavior)

    Returns a ResolvedChannel whose ``target`` field says which system to use.
    """
    # Qualified names and explicit namespaces are unambiguously anaconda.com.
    if "/" in name or namespace:
        return resolve_namespace_and_channel(api, name, namespace, require_namespace=False)

    org_match = bool(owner_probe) and owner_probe(name)

    repo_match = False
    if org_match:
        # Only need the (possibly expensive) namespace list to detect a collision.
        try:
            repo_match = any(org.name == name for org in api.list_user_organizations())
        except Exception:
            repo_match = False

    if org_match and repo_match:
        if _prompt_repo_or_org(name) == "org":
            return ResolvedChannel(namespace=None, channel_name=name, target="org", owner=name)
    elif org_match:
        return ResolvedChannel(namespace=None, channel_name=name, target="org", owner=name)

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
