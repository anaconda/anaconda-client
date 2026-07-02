"""Manage conda channel notices.

Notices are channel-level messages shown to conda users. New notices start as
**draft** (admin-only), become visible after **publish**, and can be **archived**
or deleted. Use ``notice list`` for the admin view (filter with ``--status``).

``<channel>`` is the channel login (user or organization account), e.g. ``user`` or
``myorg`` — not a repocore namespace path.

example::

    anaconda channel notice create mychannel --message "Maintenance tonight" --expires-after 30
    anaconda channel notice publish mychannel 550e8400-e29b-41d4-a716-446655440000
    anaconda channel notice list mychannel --status published

"""

from __future__ import annotations

import argparse
import datetime
import json
import logging
import re
import sys
import uuid
from enum import Enum
from typing import Any, Dict, Optional

import typer
from anaconda_cli_base.console import Table, console
from dateutil.parser import parse as parse_date
from rich.panel import Panel

from binstar_client import errors
from binstar_client.utils import bool_input, get_server_api

logger = logging.getLogger('binstar.channel_notices')

CHANNEL_HELP = 'Channel login (user or organization account)'
NAMESPACE_HELP = 'Organization namespace (owner login)'
NOTICE_CLI_PREFIX = 'anaconda channel notice'
EXPIRY_PROMPT = 'Expiry (days e.g. 30, or ISO 8601 e.g. 2026-09-16T12:00:00Z): '
EXPIRY_UPDATE_PROMPT = 'Expiry (days e.g. 30, or ISO 8601 e.g. 2026-09-16T12:00:00Z; blank to keep current): '
DEFAULT_INTERACTIVE_EXPIRY_DAYS = 30
MAX_BLANK_EXPIRY_ATTEMPTS = 3
MESSAGE_MAX_LEN = 256
MESSAGE_HELP = f'Text to show in the notice (max {MESSAGE_MAX_LEN} characters)'
MESSAGE_UPDATE_HELP = f'Updated text to show in the notice (max {MESSAGE_MAX_LEN} characters)'
EXPIRES_AT_HELP = 'Expiry time in ISO 8601 format (e.g. 2026-09-16T12:00:00Z)'
EXPIRES_AFTER_HELP = 'Expire after this many days from now (mutually exclusive with --expires-at)'


class NoticeLevel(str, Enum):
    INFO = 'info'
    WARNING = 'warning'
    CRITICAL = 'critical'


class NoticeStatus(str, Enum):
    DRAFT = 'draft'
    PUBLISHED = 'published'
    ARCHIVED = 'archived'
    DELETED = 'deleted'


class NoticeUpdateStatus(str, Enum):
    DRAFT = 'draft'
    PUBLISHED = 'published'
    ARCHIVED = 'archived'


class NoticeAction(str, Enum):
    LIST = 'list'
    GET = 'get'
    CREATE = 'create'
    UPDATE = 'update'
    DELETE = 'delete'
    PUBLISH = 'publish'
    ARCHIVE = 'archive'


NOTICE_LEVELS = tuple(level.value for level in NoticeLevel)
DEFAULT_NOTICE_LEVEL = NoticeLevel.INFO.value
LEVEL_HELP = f'Notice level: {", ".join(NOTICE_LEVELS)} (default: {DEFAULT_NOTICE_LEVEL})'
LEVEL_UPDATE_HELP = f'Updated notice level: {", ".join(NOTICE_LEVELS)}'
NOTICE_STATUSES = tuple(status.value for status in NoticeStatus)
LIST_FILTER_STATUSES = tuple(status.value for status in NoticeUpdateStatus)
UPDATE_STATUS_VALUES = LIST_FILTER_STATUSES
STATUS_UPDATE_HELP = f'Updated status: {", ".join(UPDATE_STATUS_VALUES)}'
NOTICE_ACTION_HELP: Dict[NoticeAction, str] = {
    NoticeAction.LIST: 'List notices for a channel',
    NoticeAction.GET: 'Get a single notice',
    NoticeAction.CREATE: 'Create a draft notice',
    NoticeAction.UPDATE: 'Update a notice',
    NoticeAction.DELETE: 'Delete a notice',
    NoticeAction.PUBLISH: 'Publish a draft notice',
    NoticeAction.ARCHIVE: 'Archive a notice',
}
NOTICE_ID_ACTIONS = (
    (NoticeAction.DELETE.value, NOTICE_ACTION_HELP[NoticeAction.DELETE]),
    (NoticeAction.PUBLISH.value, NOTICE_ACTION_HELP[NoticeAction.PUBLISH]),
    (NoticeAction.ARCHIVE.value, NOTICE_ACTION_HELP[NoticeAction.ARCHIVE]),
)
NOTICE_ID_HELP = f'Notice UUID (from create output or run: {NOTICE_CLI_PREFIX} {NoticeAction.LIST.value} <channel>)'
NOTICE_ID_ACTIONS_REQUIRING_UUID = (
    NoticeAction.GET,
    NoticeAction.UPDATE,
    NoticeAction.DELETE,
    NoticeAction.PUBLISH,
    NoticeAction.ARCHIVE,
)


def resolve_notice_owner(
    channel: Optional[str],
    namespace: Optional[str],
) -> str:
    """Resolve CLI channel/namespace arguments to owner login for the notices API."""
    if channel and namespace:
        raise errors.UserError('Cannot specify both channel and --namespace')
    if channel:
        return channel
    if namespace:
        return namespace
    raise errors.UserError('channel or --namespace is required')


def _is_interactive() -> bool:
    return sys.stdin.isatty()


def validate_notice_id(notice_id: str) -> str:
    try:
        uuid.UUID(notice_id)
    except ValueError as err:
        raise errors.UserError('notice_id must be a valid UUID') from err
    return notice_id


def validate_message(message: str) -> str:
    message = message.strip()
    if not message:
        raise errors.UserError('message is required')
    if len(message) > MESSAGE_MAX_LEN:
        raise errors.UserError(f'message must be at most {MESSAGE_MAX_LEN} characters')
    return message


def prompt_message(value: Optional[str] = None, *, interactive: bool) -> str:
    if value is not None:
        return validate_message(value)
    if not interactive:
        raise errors.UserError('message is required (non-interactive mode)')
    while True:
        message = input('Message: ').strip()
        try:
            return validate_message(message)
        except errors.UserError as err:
            logger.warning('%s', err)


def resolve_level(value: Optional[str] = None, *, interactive: bool) -> str:
    if value:
        if value not in NOTICE_LEVELS:
            raise errors.UserError(f'level must be one of: {", ".join(NOTICE_LEVELS)}')
        return value
    if not interactive:
        return DEFAULT_NOTICE_LEVEL
    level = input(f'Level ({"/".join(NOTICE_LEVELS)}, default: {DEFAULT_NOTICE_LEVEL}): ').strip().lower()
    if not level:
        return DEFAULT_NOTICE_LEVEL
    if level in NOTICE_LEVELS:
        return level
    raise errors.UserError(f'level must be one of: {", ".join(NOTICE_LEVELS)}')


def expires_at_from_days(days: int) -> str:
    if days < 1:
        raise errors.UserError('expires_after must be at least 1 day')
    expires = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=days)
    return expires.astimezone(datetime.timezone.utc).replace(microsecond=0).strftime('%Y-%m-%dT%H:%M:%S+00:00')


def validate_expires_at(expires_at: str) -> str:
    """Parse expiry time and ensure it is not in the past."""
    try:
        parsed = parse_date(expires_at)
    except (ValueError, TypeError) as err:
        raise errors.UserError('Invalid expires_at datetime. Use ISO 8601 format.') from err

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.timezone.utc)
    else:
        parsed = parsed.astimezone(datetime.timezone.utc)

    now = datetime.datetime.now(datetime.timezone.utc)
    if parsed < now:
        raise errors.UserError('expires_at must be in the future')

    return parsed.replace(microsecond=0).strftime('%Y-%m-%dT%H:%M:%S+00:00')


def parse_expiry_input(value: str) -> str:
    """Parse days (``30``/``30d``) or ISO 8601 expiry input."""
    value = value.strip()
    if not value:
        raise errors.UserError('expiry is required')

    days_match = re.fullmatch(r'(\d+)d?', value, re.IGNORECASE)
    if days_match:
        return expires_at_from_days(int(days_match.group(1)))

    return validate_expires_at(value)


def prompt_expiry_interactive() -> str:
    blank_attempts = 0
    while True:
        value = input(EXPIRY_PROMPT).strip()
        if not value:
            blank_attempts += 1
            if blank_attempts >= MAX_BLANK_EXPIRY_ATTEMPTS:
                if bool_input(
                    f'Use default notice period of {DEFAULT_INTERACTIVE_EXPIRY_DAYS} days?',
                    default=True,
                ):
                    return expires_at_from_days(DEFAULT_INTERACTIVE_EXPIRY_DAYS)
                blank_attempts = 0
            else:
                logger.warning('expiry is required')
            continue

        blank_attempts = 0
        try:
            return parse_expiry_input(value)
        except errors.UserError as err:
            logger.warning('%s', err)


def resolve_expires_at(
    expires_at: Optional[str] = None,
    expires_after: Optional[int] = None,
    *,
    interactive: bool,
) -> str:
    if expires_at is not None and expires_after is not None:
        raise errors.UserError('Use only one of --expires-at or --expires-after')
    if expires_after is not None:
        return expires_at_from_days(expires_after)
    if expires_at:
        return parse_expiry_input(expires_at)
    if not interactive:
        raise errors.UserError('expires_at is required (use --expires-at or --expires-after)')
    return prompt_expiry_interactive()


def format_list_command(channel: str) -> str:
    return f'{NOTICE_CLI_PREFIX} {NoticeAction.LIST.value} {channel}'


def print_missing_notice_id_hint(channel: Optional[str] = None) -> None:
    channel_arg = channel or '<channel>'
    list_cmd = format_list_command(channel_arg)
    console.print("[bold red]Error:[/bold red] Missing argument 'NOTICE_ID'.")
    console.print(f'Note: Find notice IDs with: [cyan]{list_cmd}[/cyan]')


def require_notice_id(notice_id: Optional[str], channel: Optional[str] = None) -> str:
    if not notice_id:
        print_missing_notice_id_hint(channel)
        raise errors.UserError("Missing argument 'NOTICE_ID'.")
    return notice_id


def format_publish_command(channel: str, notice_id: str) -> str:
    return f'{NOTICE_CLI_PREFIX} {NoticeAction.PUBLISH.value} {channel} {notice_id}'


def offer_publish_after_create(
    api,
    channel: str,
    notice_id: str,
    status: str,
    *,
    interactive: bool,
) -> None:
    if status != NoticeStatus.DRAFT.value:
        return

    publish_cmd = format_publish_command(channel, notice_id)
    if interactive:
        if bool_input('Do you want to publish this notice to the channel?', default=False):
            do_publish(api, channel, notice_id, force=True)
            return

    console.print('Notice is a draft and not visible to channel users yet.')
    console.print(f'To publish, run: {publish_cmd}')


def _print_table(table: Table) -> None:
    if console.height and table.row_count > console.height:
        with console.pager():
            console.print(table)
    else:
        console.print(table)


def show_admin_notices(items: list, channel: str) -> None:
    if not items:
        console.print('[dim]No notices found.[/dim]')
        return

    table = Table(title=f'{channel} Notices')
    table.add_column('Notice ID', style='cyan')
    table.add_column('Status')
    table.add_column('Level')
    table.add_column('Message')
    table.add_column('Expires')

    for item in items:
        table.add_row(
            str(item.get('notice_id', '')),
            str(item.get('status', '')),
            str(item.get('level', '')),
            str(item.get('message', '')),
            str(item.get('expires_at', '')),
        )

    _print_table(table)


def show_notice_detail(notice: Dict[str, Any], verbose: bool = False) -> None:
    notice_id = notice.get('notice_id', notice.get('id', ''))

    if verbose:
        console.print(json.dumps(notice, indent=2))
        return

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column('Field', style='bold cyan')
    table.add_column('Value')

    fields = [
        ('Notice ID', notice_id),
        ('Status', notice.get('status', NoticeStatus.PUBLISHED.value)),
        ('Level', notice.get('level', '')),
        ('Message', notice.get('message', '')),
    ]
    if notice.get('expires_at'):
        fields.append(('Expires', notice['expires_at']))
    if notice.get('created_at'):
        fields.append(('Created', notice['created_at']))
    if notice.get('updated_at'):
        fields.append(('Updated', notice['updated_at']))

    for field, value in fields:
        table.add_row(field, str(value))

    console.print(Panel(table, title=f'Notice: {notice_id}', border_style='green'))


def do_list(api, channel: str, status: Optional[str], offset: int, limit: int) -> None:
    result = api.list_notices(channel, status=status, offset=offset, limit=limit)
    items = result.get('items', [])
    show_admin_notices(items, channel)
    total = result.get('total_count')
    if total is not None:
        console.print(f'Total: {total}')
        if offset + len(items) < total:
            console.print(
                f'Showing {offset + 1}–{offset + len(items)} of {total}. Use --offset {offset + len(items)} for more.'
            )


def do_get(api, channel: str, notice_id: str, verbose: bool) -> None:
    notice = api.get_notice(channel, notice_id)
    show_notice_detail(notice, verbose=verbose)


def do_create(
    api,
    channel: str,
    message: Optional[str],
    level: Optional[str],
    expires_at: Optional[str],
    expires_after: Optional[int] = None,
) -> None:
    interactive = _is_interactive()
    message = prompt_message(message, interactive=interactive)
    level = resolve_level(level, interactive=interactive)
    expires_at = resolve_expires_at(expires_at, expires_after, interactive=interactive)

    result = api.create_notice(channel, message, level, expires_at)
    created_id = result.get('notice_id')
    if not created_id:
        raise errors.UserError('API did not return a notice_id')
    status = result.get('status', NoticeStatus.DRAFT.value)
    console.print(f"Notice '{created_id}' created successfully ({status}).")
    console.print(f'Find notice IDs with: {format_list_command(channel)}')
    offer_publish_after_create(api, channel, created_id, status, interactive=interactive)


def do_update(
    api,
    channel: str,
    notice_id: str,
    message: Optional[str],
    level: Optional[str],
    expires_at: Optional[str],
    expires_after: Optional[int] = None,
    status: Optional[str] = None,
) -> None:
    if expires_at is not None and expires_after is not None:
        raise errors.UserError('Use only one of --expires-at or --expires-after')

    interactive = _is_interactive()
    fields: Dict[str, str] = {}
    if message is not None:
        fields['message'] = validate_message(message)
    if level is not None:
        fields['level'] = level
    if status is not None:
        if status not in UPDATE_STATUS_VALUES:
            raise errors.UserError(f'status must be one of: {", ".join(UPDATE_STATUS_VALUES)}')
        fields['status'] = status
    if expires_after is not None:
        fields['expires_at'] = expires_at_from_days(expires_after)
    elif expires_at is not None:
        fields['expires_at'] = parse_expiry_input(expires_at)

    if not fields:
        if not interactive:
            raise errors.UserError(
                'At least one of --message, --level, --expires-at, --expires-after, or --status is required'
            )
        optional_message = input('Message (leave blank to skip): ').strip()
        if optional_message:
            fields['message'] = validate_message(optional_message)
        optional_level = input(f'Level ({"/".join(NOTICE_LEVELS)}, blank to skip): ').strip().lower()
        if optional_level:
            if optional_level not in NOTICE_LEVELS:
                raise errors.UserError(f'level must be one of: {", ".join(NOTICE_LEVELS)}')
            fields['level'] = optional_level
        optional_status = input(f'Status ({"/".join(UPDATE_STATUS_VALUES)}, blank to skip): ').strip().lower()
        if optional_status:
            if optional_status not in UPDATE_STATUS_VALUES:
                raise errors.UserError(f'status must be one of: {", ".join(UPDATE_STATUS_VALUES)}')
            fields['status'] = optional_status
        optional_expires = input(EXPIRY_UPDATE_PROMPT).strip()
        if optional_expires:
            fields['expires_at'] = parse_expiry_input(optional_expires)

    if not fields:
        raise errors.UserError('At least one field is required to update')

    result = api.update_notice(channel, notice_id, **fields)
    updated_id = result.get('notice_id', notice_id)
    console.print(f"Notice '{updated_id}' updated successfully.")


def do_delete(api, channel: str, notice_id: str, force: bool = False) -> None:
    if not force:
        msg = f"Are you sure you want to delete notice '{notice_id}'?"
        if not bool_input(msg, False):
            console.print(f"Not deleting notice '{notice_id}'")
            return

    api.delete_notice(channel, notice_id)
    console.print(f"Notice '{notice_id}' deleted successfully.")


def do_publish(api, channel: str, notice_id: str, force: bool = False) -> None:
    if not force:
        msg = f"Are you sure you want to publish notice '{notice_id}'?"
        if not bool_input(msg, False):
            console.print(f"Not publishing notice '{notice_id}'")
            return

    result = api.publish_notice(channel, notice_id)
    published_id = result.get('notice_id', notice_id)
    console.print(f"Notice '{published_id}' published successfully.")
    console.print(f'Verify with: {format_list_command(channel)} --status published')


def do_archive(api, channel: str, notice_id: str, force: bool = False) -> None:
    if not force:
        msg = f"Are you sure you want to archive notice '{notice_id}'?"
        if not bool_input(msg, False):
            console.print(f"Not archiving notice '{notice_id}'")
            return

    result = api.archive_notice(channel, notice_id)
    archived_id = result.get('notice_id', notice_id)
    console.print(f"Notice '{archived_id}' archived successfully.")


def _parse_notice_action(action: str) -> NoticeAction:
    try:
        return NoticeAction(action)
    except ValueError as err:
        raise NotImplementedError(action) from err


def main(args: argparse.Namespace) -> None:
    """Dispatch channel notice subcommands."""
    action = _parse_notice_action(args.notice_action)
    api = get_server_api(args.token, args.site)

    channel = resolve_notice_owner(
        getattr(args, 'channel', None),
        getattr(args, 'namespace', None),
    )

    if action in NOTICE_ID_ACTIONS_REQUIRING_UUID:
        require_notice_id(getattr(args, 'notice_id', None), channel)
        validate_notice_id(args.notice_id)

    if action == NoticeAction.LIST:
        do_list(api, channel, args.status, args.offset, args.limit)
    elif action == NoticeAction.GET:
        do_get(api, channel, args.notice_id, getattr(args, 'log_level', logging.INFO) == logging.DEBUG)
    elif action == NoticeAction.CREATE:
        do_create(
            api,
            channel,
            args.message,
            args.level,
            args.expires_at,
            getattr(args, 'expires_after', None),
        )
    elif action == NoticeAction.UPDATE:
        do_update(
            api,
            channel,
            args.notice_id,
            args.message,
            args.level,
            args.expires_at,
            getattr(args, 'expires_after', None),
            getattr(args, 'status', None),
        )
    elif action == NoticeAction.DELETE:
        do_delete(api, channel, args.notice_id, force=getattr(args, 'force', False))
    elif action == NoticeAction.PUBLISH:
        do_publish(api, channel, args.notice_id, force=getattr(args, 'force', False))
    elif action == NoticeAction.ARCHIVE:
        do_archive(api, channel, args.notice_id, force=getattr(args, 'force', False))
    else:
        raise NotImplementedError(action)


def _ctx_args(ctx: typer.Context) -> argparse.Namespace:
    return argparse.Namespace(
        token=ctx.obj.params.get('token'),
        site=ctx.obj.params.get('site'),
    )


def _add_channel_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        'channel',
        nargs='?',
        default=None,
        help=CHANNEL_HELP,
    )
    parser.add_argument(
        '-n',
        '--namespace',
        help=NAMESPACE_HELP,
    )


def _add_expiry_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument('--expires-at', dest='expires_at', help=EXPIRES_AT_HELP)
    parser.add_argument(
        '--expires-after',
        dest='expires_after',
        type=int,
        metavar='DAYS',
        help=EXPIRES_AFTER_HELP,
    )


def add_notice_argparse(notice_parser: argparse.ArgumentParser) -> None:
    """Register notice subcommand parsers under the channel command."""
    notice_subparsers = notice_parser.add_subparsers(dest='notice_action', metavar='ACTION')
    notice_subparsers.required = True

    list_parser = notice_subparsers.add_parser(NoticeAction.LIST.value, help=NOTICE_ACTION_HELP[NoticeAction.LIST])
    _add_channel_args(list_parser)
    list_parser.add_argument('--status', choices=LIST_FILTER_STATUSES, help='Filter by status')
    list_parser.add_argument('--offset', type=int, default=0, help='Pagination offset')
    list_parser.add_argument('--limit', type=int, default=20, help='Page size (1-100)')
    list_parser.set_defaults(main=main)

    get_parser = notice_subparsers.add_parser(NoticeAction.GET.value, help=NOTICE_ACTION_HELP[NoticeAction.GET])
    _add_channel_args(get_parser)
    get_parser.add_argument('notice_id', nargs='?', default=None, help=NOTICE_ID_HELP)
    get_parser.set_defaults(main=main)

    create_parser = notice_subparsers.add_parser(
        NoticeAction.CREATE.value, help=NOTICE_ACTION_HELP[NoticeAction.CREATE]
    )
    _add_channel_args(create_parser)
    create_parser.add_argument(
        '--message',
        help=MESSAGE_HELP,
    )
    create_parser.add_argument(
        '--level',
        choices=NOTICE_LEVELS,
        help=LEVEL_HELP,
    )
    _add_expiry_args(create_parser)
    create_parser.set_defaults(main=main)

    update_parser = notice_subparsers.add_parser(
        NoticeAction.UPDATE.value, help=NOTICE_ACTION_HELP[NoticeAction.UPDATE]
    )
    _add_channel_args(update_parser)
    update_parser.add_argument('notice_id', nargs='?', default=None, help=NOTICE_ID_HELP)
    update_parser.add_argument(
        '--message',
        help=MESSAGE_UPDATE_HELP,
    )
    update_parser.add_argument('--level', choices=NOTICE_LEVELS, help=LEVEL_UPDATE_HELP)
    update_parser.add_argument('--status', choices=UPDATE_STATUS_VALUES, help=STATUS_UPDATE_HELP)
    _add_expiry_args(update_parser)
    update_parser.set_defaults(main=main)

    for action_name, help_text in NOTICE_ID_ACTIONS:
        action_parser = notice_subparsers.add_parser(action_name, help=help_text)
        _add_channel_args(action_parser)
        action_parser.add_argument('notice_id', nargs='?', default=None, help=NOTICE_ID_HELP)
        if action_name in (
            NoticeAction.DELETE.value,
            NoticeAction.PUBLISH.value,
            NoticeAction.ARCHIVE.value,
        ):
            action_parser.add_argument(
                '-f',
                '--force',
                action='store_true',
                help='Run without confirmation',
            )
        action_parser.set_defaults(main=main)


def mount_notice_subcommand(parent_app: typer.Typer) -> None:
    """Register nested `notice` typer commands under the channel group."""
    notice_app = typer.Typer(
        name='notice',
        help='Manage conda channel notices',
        no_args_is_help=True,
    )
    parent_app.add_typer(notice_app, name='notice')

    def _run_notice_action(
        ctx: typer.Context,
        action: NoticeAction,
        channel: Optional[str] = None,
        notice_id: Optional[str] = None,
        namespace: Optional[str] = None,
        **extra: Any,
    ) -> None:
        args = _ctx_args(ctx)
        args.notice_action = action.value
        args.channel = channel
        args.notice_id = notice_id
        args.namespace = namespace
        for key, value in extra.items():
            setattr(args, key, value)
        if action in NOTICE_ID_ACTIONS_REQUIRING_UUID and not notice_id:
            print_missing_notice_id_hint(channel or namespace)
            raise typer.Exit(2)
        main(args)

    @notice_app.command(NoticeAction.LIST.value, help=NOTICE_ACTION_HELP[NoticeAction.LIST])
    def notice_list(
        ctx: typer.Context,
        channel: Optional[str] = typer.Argument(None, help=CHANNEL_HELP),
        namespace: Optional[str] = typer.Option(None, '-n', '--namespace', help=NAMESPACE_HELP),
        status: Optional[str] = typer.Option(None, '--status', help='Filter by status'),
        offset: int = typer.Option(0, '--offset'),
        limit: int = typer.Option(20, '--limit'),
    ) -> None:
        _run_notice_action(
            ctx,
            NoticeAction.LIST,
            channel=channel,
            namespace=namespace,
            status=status,
            offset=offset,
            limit=limit,
        )

    @notice_app.command(NoticeAction.GET.value, help=NOTICE_ACTION_HELP[NoticeAction.GET])
    def notice_get(
        ctx: typer.Context,
        channel: Optional[str] = typer.Argument(None, help=CHANNEL_HELP),
        notice_id: Optional[str] = typer.Argument(None, help=NOTICE_ID_HELP),
        namespace: Optional[str] = typer.Option(None, '-n', '--namespace', help=NAMESPACE_HELP),
    ) -> None:
        _run_notice_action(ctx, NoticeAction.GET, channel=channel, notice_id=notice_id, namespace=namespace)

    @notice_app.command(NoticeAction.CREATE.value, help=NOTICE_ACTION_HELP[NoticeAction.CREATE])
    def notice_create(
        ctx: typer.Context,
        channel: Optional[str] = typer.Argument(None, help=CHANNEL_HELP),
        namespace: Optional[str] = typer.Option(None, '-n', '--namespace', help=NAMESPACE_HELP),
        message: Optional[str] = typer.Option(None, '--message', help=MESSAGE_HELP),
        level: Optional[NoticeLevel] = typer.Option(
            None,
            '--level',
            help=LEVEL_HELP,
        ),
        expires_at: Optional[str] = typer.Option(None, '--expires-at', help=EXPIRES_AT_HELP),
        expires_after: Optional[int] = typer.Option(
            None,
            '--expires-after',
            min=1,
            help=EXPIRES_AFTER_HELP,
        ),
    ) -> None:
        _run_notice_action(
            ctx,
            NoticeAction.CREATE,
            channel=channel,
            namespace=namespace,
            message=message,
            level=level.value if level else None,
            expires_at=expires_at,
            expires_after=expires_after,
        )

    @notice_app.command(NoticeAction.UPDATE.value, help=NOTICE_ACTION_HELP[NoticeAction.UPDATE])
    def notice_update(
        ctx: typer.Context,
        channel: Optional[str] = typer.Argument(None, help=CHANNEL_HELP),
        notice_id: Optional[str] = typer.Argument(None, help=NOTICE_ID_HELP),
        namespace: Optional[str] = typer.Option(None, '-n', '--namespace', help=NAMESPACE_HELP),
        message: Optional[str] = typer.Option(None, '--message', help=MESSAGE_UPDATE_HELP),
        level: Optional[NoticeLevel] = typer.Option(None, '--level', help=LEVEL_UPDATE_HELP),
        status: Optional[NoticeUpdateStatus] = typer.Option(None, '--status', help=STATUS_UPDATE_HELP),
        expires_at: Optional[str] = typer.Option(None, '--expires-at', help=EXPIRES_AT_HELP),
        expires_after: Optional[int] = typer.Option(
            None,
            '--expires-after',
            min=1,
            help=EXPIRES_AFTER_HELP,
        ),
    ) -> None:
        _run_notice_action(
            ctx,
            NoticeAction.UPDATE,
            channel=channel,
            notice_id=notice_id,
            namespace=namespace,
            message=message,
            level=level.value if level else None,
            status=status.value if status else None,
            expires_at=expires_at,
            expires_after=expires_after,
        )

    @notice_app.command(NoticeAction.DELETE.value, help=NOTICE_ACTION_HELP[NoticeAction.DELETE])
    def notice_delete(
        ctx: typer.Context,
        channel: Optional[str] = typer.Argument(None, help=CHANNEL_HELP),
        notice_id: Optional[str] = typer.Argument(None, help=NOTICE_ID_HELP),
        namespace: Optional[str] = typer.Option(None, '-n', '--namespace', help=NAMESPACE_HELP),
        force: bool = typer.Option(False, '-f', '--force', help='Delete without confirmation'),
    ) -> None:
        _run_notice_action(
            ctx,
            NoticeAction.DELETE,
            channel=channel,
            notice_id=notice_id,
            namespace=namespace,
            force=force,
        )

    @notice_app.command(NoticeAction.PUBLISH.value, help=NOTICE_ACTION_HELP[NoticeAction.PUBLISH])
    def notice_publish(
        ctx: typer.Context,
        channel: Optional[str] = typer.Argument(None, help=CHANNEL_HELP),
        notice_id: Optional[str] = typer.Argument(None, help=NOTICE_ID_HELP),
        namespace: Optional[str] = typer.Option(None, '-n', '--namespace', help=NAMESPACE_HELP),
        force: bool = typer.Option(False, '-f', '--force', help='Publish without confirmation'),
    ) -> None:
        _run_notice_action(
            ctx,
            NoticeAction.PUBLISH,
            channel=channel,
            notice_id=notice_id,
            namespace=namespace,
            force=force,
        )

    @notice_app.command(NoticeAction.ARCHIVE.value, help=NOTICE_ACTION_HELP[NoticeAction.ARCHIVE])
    def notice_archive(
        ctx: typer.Context,
        channel: Optional[str] = typer.Argument(None, help=CHANNEL_HELP),
        notice_id: Optional[str] = typer.Argument(None, help=NOTICE_ID_HELP),
        namespace: Optional[str] = typer.Option(None, '-n', '--namespace', help=NAMESPACE_HELP),
        force: bool = typer.Option(False, '-f', '--force', help='Archive without confirmation'),
    ) -> None:
        _run_notice_action(
            ctx,
            NoticeAction.ARCHIVE,
            channel=channel,
            notice_id=notice_id,
            namespace=namespace,
            force=force,
        )
