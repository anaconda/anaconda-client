"""Manage conda channel notices."""

from __future__ import annotations

import argparse
import datetime
import json
import logging
import secrets
import string
import sys
from enum import Enum
from typing import Any, Dict, Optional

import click
import typer
from dateutil.parser import parse as parse_date

from binstar_client import errors
from binstar_client.utils import get_server_api
from binstar_client.utils import tables

logger = logging.getLogger('binstar.channel_notices')

CHANNEL_HELP = 'Channel owner login (user or organization account)'
NOTICE_STATUSES = ('draft', 'published', 'archived', 'deleted')


class NoticeLevel(str, Enum):
    INFO = 'info'
    WARNING = 'warning'
    CRITICAL = 'critical'


NOTICE_LEVELS = tuple(level.value for level in NoticeLevel)
DEFAULT_NOTICE_LEVEL = NoticeLevel.INFO.value


def resolve_channel(
    channel: Optional[str],
    api,
    organization: Optional[str] = None,
) -> str:
    """Resolve CLI channel argument to API owner login."""
    if organization:
        return organization
    if channel:
        return channel
    return api.user()['login']


def _is_interactive() -> bool:
    return sys.stdin.isatty()


def _prompt_or_raise(field_name: str, value: Optional[str], prompt_fn) -> str:
    if value:
        return value
    if not _is_interactive():
        raise errors.UserError(f'{field_name} is required (non-interactive mode)')
    return prompt_fn()


def generate_notice_id(owner: str) -> str:
    """Build a default notice id: ``{owner}-notice-{3 random alphanumeric chars}``."""
    alphabet = string.ascii_lowercase + string.digits
    suffix = ''.join(secrets.choice(alphabet) for _ in range(3))
    return f'{owner}-notice-{suffix}'


def resolve_notice_id(owner: str, value: Optional[str] = None) -> str:
    if value:
        return value
    notice_id = generate_notice_id(owner)
    logger.info('Generated notice ID: %s', notice_id)
    return notice_id


def prompt_message(value: Optional[str] = None) -> str:
    return _prompt_or_raise(
        'message',
        value,
        lambda: input('Message: ').strip(),
    )


def resolve_level(value: Optional[str] = None) -> str:
    if value:
        if value not in NOTICE_LEVELS:
            raise errors.UserError(f'level must be one of: {", ".join(NOTICE_LEVELS)}')
        return value
    if not _is_interactive():
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
    return expires.replace(microsecond=0).strftime('%Y-%m-%dT%H:%M:%SZ')


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

    return expires_at


def resolve_expires_at(
    expires_at: Optional[str] = None,
    expires_after: Optional[int] = None,
) -> str:
    if expires_at is not None and expires_after is not None:
        raise errors.UserError('Use only one of --expires-at or --expires-after')
    if expires_after is not None:
        return expires_at_from_days(expires_after)
    if expires_at:
        return validate_expires_at(expires_at)
    if not _is_interactive():
        raise errors.UserError('expires_at is required (use --expires-at or --expires-after)')
    while True:
        expires_at = input('Expires at (ISO 8601 datetime): ').strip()
        try:
            return validate_expires_at(expires_at)
        except errors.UserError as err:
            logger.warning('%s', err)


def _render_table(items: list, aliases: tuple, empty_message: str) -> None:
    if not items:
        logger.info(empty_message)
        return

    table = tables.SimpleTableWithAliases(aliases=aliases, heading_rows=1)
    for item in items:
        table.append_row(item)

    logger.info('')
    for line in table.render(tables.SIMPLE):
        logger.info(line)
    logger.info('')


def show_admin_notices(items: list) -> None:
    _render_table(
        items,
        (
            ('notice_id', 'Notice ID'),
            ('status', 'Status'),
            ('level', 'Level'),
            ('message', 'Message'),
            ('expires_at', 'Expires'),
        ),
        'No notices found.',
    )


def show_active_notices(notices: list) -> None:
    _render_table(
        notices,
        (
            ('id', 'ID'),
            ('level', 'Level'),
            ('message', 'Message'),
            ('expires_at', 'Expires'),
        ),
        'No active notices found.',
    )


def show_notice_detail(notice: Dict[str, Any], verbose: bool = False) -> None:
    if verbose:
        logger.info(json.dumps(notice, indent=2))
        return
    logger.info('Notice ID: %s', notice.get('notice_id', notice.get('id')))
    logger.info('Status: %s', notice.get('status', 'published'))
    logger.info('Level: %s', notice.get('level'))
    logger.info('Message: %s', notice.get('message'))
    if notice.get('expires_at'):
        logger.info('Expires: %s', notice['expires_at'])


def do_list(api, owner: str, status: Optional[str], offset: int, limit: int) -> None:
    result = api.list_notices(owner, status=status, offset=offset, limit=limit)
    show_admin_notices(result.get('items', []))
    total = result.get('total_count')
    if total is not None:
        logger.info('Total: %s', total)


def do_get(api, owner: str, notice_id: str, verbose: bool) -> None:
    notice = api.get_notice(owner, notice_id)
    show_notice_detail(notice, verbose=verbose)


def do_create(
    api,
    owner: str,
    notice_id: Optional[str],
    message: Optional[str],
    level: Optional[str],
    expires_at: Optional[str],
    expires_after: Optional[int] = None,
) -> None:
    notice_id = resolve_notice_id(owner, notice_id)
    message = prompt_message(message)
    level = resolve_level(level)
    expires_at = resolve_expires_at(expires_at, expires_after)

    result = api.create_notice(owner, notice_id, message, level, expires_at)
    logger.info("Created notice '%s' (%s)", result.get('notice_id', notice_id), result.get('status', 'draft'))


def do_update(
    api,
    owner: str,
    notice_id: str,
    message: Optional[str],
    level: Optional[str],
    expires_at: Optional[str],
    expires_after: Optional[int] = None,
) -> None:
    if expires_at is not None and expires_after is not None:
        raise errors.UserError('Use only one of --expires-at or --expires-after')

    fields: Dict[str, str] = {}
    if message is not None:
        fields['message'] = message
    if level is not None:
        fields['level'] = level
    if expires_after is not None:
        fields['expires_at'] = expires_at_from_days(expires_after)
    elif expires_at is not None:
        fields['expires_at'] = validate_expires_at(expires_at)

    if not fields:
        if not _is_interactive():
            raise errors.UserError('At least one of --message, --level, --expires-at, or --expires-after is required')
        optional_message = input('Message (leave blank to skip): ').strip()
        if optional_message:
            fields['message'] = optional_message
        optional_level = input(f'Level ({"/".join(NOTICE_LEVELS)}, blank to skip): ').strip().lower()
        if optional_level:
            if optional_level not in NOTICE_LEVELS:
                raise errors.UserError(f'level must be one of: {", ".join(NOTICE_LEVELS)}')
            fields['level'] = optional_level
        optional_expires = input('Expires at (ISO 8601, blank to skip): ').strip()
        if optional_expires:
            fields['expires_at'] = validate_expires_at(optional_expires)

    if not fields:
        raise errors.UserError('At least one field is required to update')

    api.update_notice(owner, notice_id, **fields)
    logger.info("Updated notice '%s'", notice_id)


def do_delete(api, owner: str, notice_id: str) -> None:
    api.delete_notice(owner, notice_id)
    logger.info("Deleted notice '%s'", notice_id)


def do_publish(api, owner: str, notice_id: str) -> None:
    result = api.publish_notice(owner, notice_id)
    logger.info("Published notice '%s' (status: %s)", notice_id, result.get('status', 'published'))


def do_archive(api, owner: str, notice_id: str) -> None:
    result = api.archive_notice(owner, notice_id)
    logger.info("Archived notice '%s' (status: %s)", notice_id, result.get('status', 'archived'))


def do_active(api, channel: Optional[str]) -> None:
    result = api.list_active_notices(owner=channel)
    show_active_notices(result.get('notices', []))


def main(args: argparse.Namespace) -> None:
    """Dispatch channel notice subcommands."""
    action = args.notice_action
    api = get_server_api(args.token, args.site)

    if action == 'active':
        do_active(api, getattr(args, 'active_channel', None))
        return

    owner = resolve_channel(
        getattr(args, 'channel', None),
        api,
        organization=getattr(args, 'organization', None),
    )

    if action == 'list':
        do_list(api, owner, args.status, args.offset, args.limit)
    elif action == 'get':
        do_get(api, owner, args.notice_id, getattr(args, 'log_level', logging.INFO) == logging.DEBUG)
    elif action in ('create', 'add'):
        do_create(
            api,
            owner,
            args.notice_id,
            args.message,
            args.level,
            args.expires_at,
            getattr(args, 'expires_after', None),
        )
    elif action == 'update':
        do_update(
            api,
            owner,
            args.notice_id,
            args.message,
            args.level,
            args.expires_at,
            getattr(args, 'expires_after', None),
        )
    elif action == 'delete':
        do_delete(api, owner, args.notice_id)
    elif action == 'publish':
        do_publish(api, owner, args.notice_id)
    elif action == 'archive':
        do_archive(api, owner, args.notice_id)
    else:
        raise NotImplementedError(action)


def _common_namespace(ctx: typer.Context) -> Dict[str, Any]:
    organization = None
    current: Optional[click.Context] = ctx
    while current is not None:
        org = current.params.get('organization')
        if org:
            organization = org
            break
        current = current.parent

    return {
        'token': ctx.obj.params.get('token'),
        'site': ctx.obj.params.get('site'),
        'organization': organization,
    }


def _add_owner_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        'channel',
        nargs='?',
        default=None,
        help=CHANNEL_HELP,
    )
    parser.add_argument(
        '-o',
        '--organization',
        help='Manage notices for an organization channel',
    )


def _add_expiry_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument('--expires-at', dest='expires_at', help='Expiry time (ISO 8601)')
    parser.add_argument(
        '--expires-after',
        dest='expires_after',
        type=int,
        metavar='DAYS',
        help='Expire after this many days from now (mutually exclusive with --expires-at)',
    )


def add_notice_argparse(notice_parser: argparse.ArgumentParser) -> None:
    """Register notice subcommand parsers under the channel command."""
    notice_subparsers = notice_parser.add_subparsers(dest='notice_action', metavar='ACTION')
    notice_subparsers.required = True

    list_parser = notice_subparsers.add_parser('list', help='List notices for a channel')
    _add_owner_args(list_parser)
    list_parser.add_argument('--status', choices=NOTICE_STATUSES, help='Filter by status')
    list_parser.add_argument('--offset', type=int, default=0, help='Pagination offset')
    list_parser.add_argument('--limit', type=int, default=20, help='Page size (1-100)')
    list_parser.set_defaults(main=main)

    get_parser = notice_subparsers.add_parser('get', help='Get a single notice')
    _add_owner_args(get_parser)
    get_parser.add_argument('notice_id', help='Notice ID')
    get_parser.set_defaults(main=main)

    for action_name, help_text in (
        ('create', 'Create a draft notice'),
        ('add', 'Create a draft notice (alias for create)'),
    ):
        create_parser = notice_subparsers.add_parser(action_name, help=help_text)
        _add_owner_args(create_parser)
        create_parser.add_argument(
            '--id',
            dest='notice_id',
            help='Unique notice ID (auto-generated as CHANNEL-notice-XXX if omitted)',
        )
        create_parser.add_argument('--message', help='Notice message text')
        create_parser.add_argument(
            '--level',
            choices=NOTICE_LEVELS,
            help=f'Notice level (default: {DEFAULT_NOTICE_LEVEL})',
        )
        _add_expiry_args(create_parser)
        create_parser.set_defaults(main=main)

    update_parser = notice_subparsers.add_parser('update', help='Update a notice')
    _add_owner_args(update_parser)
    update_parser.add_argument('notice_id', help='Notice ID')
    update_parser.add_argument('--message', help='Updated message text')
    update_parser.add_argument('--level', choices=NOTICE_LEVELS, help='Updated level')
    _add_expiry_args(update_parser)
    update_parser.set_defaults(main=main)

    for action_name, help_text in (
        ('delete', 'Delete a notice'),
        ('publish', 'Publish a draft notice'),
        ('archive', 'Archive a notice'),
    ):
        action_parser = notice_subparsers.add_parser(action_name, help=help_text)
        _add_owner_args(action_parser)
        action_parser.add_argument('notice_id', help='Notice ID')
        action_parser.set_defaults(main=main)

    active_parser = notice_subparsers.add_parser('active', help='List active published notices (public)')
    active_parser.add_argument(
        '--channel',
        dest='active_channel',
        default=None,
        help=CHANNEL_HELP,
    )
    active_parser.set_defaults(main=main)


def mount_notice_subcommand(parent_app: typer.Typer) -> None:
    """Register nested `notice` typer commands under the channel group."""
    notice_app = typer.Typer(
        name='notice',
        help='Manage conda channel notices',
        no_args_is_help=True,
    )
    parent_app.add_typer(notice_app, name='notice')

    def _ctx_args(ctx: typer.Context) -> argparse.Namespace:
        return argparse.Namespace(**_common_namespace(ctx))

    def _run_notice_action(
        ctx: typer.Context,
        action: str,
        channel: Optional[str] = None,
        notice_id: Optional[str] = None,
        organization: Optional[str] = None,
        **extra: Any,
    ) -> None:
        args = _ctx_args(ctx)
        args.notice_action = action
        args.channel = channel
        args.notice_id = notice_id
        args.organization = organization
        for key, value in extra.items():
            setattr(args, key, value)
        main(args)

    @notice_app.command('list')
    def notice_list(
        ctx: typer.Context,
        channel: Optional[str] = typer.Argument(None, help=CHANNEL_HELP),
        organization: Optional[str] = typer.Option(None, '-o', '--organization'),
        status: Optional[str] = typer.Option(None, '--status'),
        offset: int = typer.Option(0, '--offset'),
        limit: int = typer.Option(20, '--limit'),
    ) -> None:
        _run_notice_action(
            ctx,
            'list',
            channel=channel,
            organization=organization,
            status=status,
            offset=offset,
            limit=limit,
        )

    @notice_app.command('get')
    def notice_get(
        ctx: typer.Context,
        channel: str = typer.Argument(..., help=CHANNEL_HELP),
        notice_id: str = typer.Argument(..., help='Notice ID'),
        organization: Optional[str] = typer.Option(None, '-o', '--organization'),
    ) -> None:
        _run_notice_action(ctx, 'get', channel=channel, notice_id=notice_id, organization=organization)

    def _create_handler(
        ctx: typer.Context,
        channel: Optional[str],
        organization: Optional[str],
        notice_id: Optional[str],
        message: Optional[str],
        level: Optional[str],
        expires_at: Optional[str],
        expires_after: Optional[int],
        action: str,
    ) -> None:
        _run_notice_action(
            ctx,
            action,
            channel=channel,
            organization=organization,
            notice_id=notice_id,
            message=message,
            level=level,
            expires_at=expires_at,
            expires_after=expires_after,
        )

    @notice_app.command('create')
    def notice_create(
        ctx: typer.Context,
        channel: Optional[str] = typer.Argument(None, help=CHANNEL_HELP),
        organization: Optional[str] = typer.Option(None, '-o', '--organization'),
        notice_id: Optional[str] = typer.Option(
            None,
            '--id',
            help='Unique notice ID (auto-generated as CHANNEL-notice-XXX if omitted)',
        ),
        message: Optional[str] = typer.Option(None, '--message'),
        level: Optional[NoticeLevel] = typer.Option(
            None,
            '--level',
            help=f'Notice level (default: {DEFAULT_NOTICE_LEVEL})',
        ),
        expires_at: Optional[str] = typer.Option(None, '--expires-at'),
        expires_after: Optional[int] = typer.Option(
            None,
            '--expires-after',
            min=1,
            help='Expire after this many days from now',
        ),
    ) -> None:
        _create_handler(
            ctx,
            channel,
            organization,
            notice_id,
            message,
            level.value if level else None,
            expires_at,
            expires_after,
            'create',
        )

    @notice_app.command('add')
    def notice_add(
        ctx: typer.Context,
        channel: Optional[str] = typer.Argument(None, help=CHANNEL_HELP),
        organization: Optional[str] = typer.Option(None, '-o', '--organization'),
        notice_id: Optional[str] = typer.Option(
            None,
            '--id',
            help='Unique notice ID (auto-generated as CHANNEL-notice-XXX if omitted)',
        ),
        message: Optional[str] = typer.Option(None, '--message'),
        level: Optional[NoticeLevel] = typer.Option(
            None,
            '--level',
            help=f'Notice level (default: {DEFAULT_NOTICE_LEVEL})',
        ),
        expires_at: Optional[str] = typer.Option(None, '--expires-at'),
        expires_after: Optional[int] = typer.Option(
            None,
            '--expires-after',
            min=1,
            help='Expire after this many days from now',
        ),
    ) -> None:
        _create_handler(
            ctx,
            channel,
            organization,
            notice_id,
            message,
            level.value if level else None,
            expires_at,
            expires_after,
            'add',
        )

    @notice_app.command('update')
    def notice_update(
        ctx: typer.Context,
        channel: str = typer.Argument(..., help=CHANNEL_HELP),
        notice_id: str = typer.Argument(..., help='Notice ID'),
        organization: Optional[str] = typer.Option(None, '-o', '--organization'),
        message: Optional[str] = typer.Option(None, '--message'),
        level: Optional[NoticeLevel] = typer.Option(None, '--level'),
        expires_at: Optional[str] = typer.Option(None, '--expires-at'),
        expires_after: Optional[int] = typer.Option(
            None,
            '--expires-after',
            min=1,
            help='Expire after this many days from now',
        ),
    ) -> None:
        _run_notice_action(
            ctx,
            'update',
            channel=channel,
            notice_id=notice_id,
            organization=organization,
            message=message,
            level=level.value if level else None,
            expires_at=expires_at,
            expires_after=expires_after,
        )

    @notice_app.command('delete')
    def notice_delete(
        ctx: typer.Context,
        channel: str = typer.Argument(..., help=CHANNEL_HELP),
        notice_id: str = typer.Argument(..., help='Notice ID'),
        organization: Optional[str] = typer.Option(None, '-o', '--organization'),
    ) -> None:
        _run_notice_action(ctx, 'delete', channel=channel, notice_id=notice_id, organization=organization)

    @notice_app.command('publish')
    def notice_publish(
        ctx: typer.Context,
        channel: str = typer.Argument(..., help=CHANNEL_HELP),
        notice_id: str = typer.Argument(..., help='Notice ID'),
        organization: Optional[str] = typer.Option(None, '-o', '--organization'),
    ) -> None:
        _run_notice_action(ctx, 'publish', channel=channel, notice_id=notice_id, organization=organization)

    @notice_app.command('archive')
    def notice_archive(
        ctx: typer.Context,
        channel: str = typer.Argument(..., help=CHANNEL_HELP),
        notice_id: str = typer.Argument(..., help='Notice ID'),
        organization: Optional[str] = typer.Option(None, '-o', '--organization'),
    ) -> None:
        _run_notice_action(ctx, 'archive', channel=channel, notice_id=notice_id, organization=organization)

    @notice_app.command('active')
    def notice_active(
        ctx: typer.Context,
        channel: Optional[str] = typer.Option(None, '--channel', help=CHANNEL_HELP),
    ) -> None:
        _run_notice_action(ctx, 'active', active_channel=channel)
