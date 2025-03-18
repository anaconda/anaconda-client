# pylint: disable=protected-access,missing-function-docstring

"""
Manage your Anaconda repository channels.
"""

from __future__ import unicode_literals, print_function

import argparse
import functools
import logging
from typing import List, Optional, Tuple

import typer

from binstar_client.utils import get_server_api

logger = logging.getLogger('binstar.channel')


def main(args, name, deprecated=False):  # pylint: disable=too-many-branches
    aserver_api = get_server_api(args.token, args.site)

    if args.organization:
        owner = args.organization
    else:
        current_user = aserver_api.user()
        owner = current_user['login']

    if deprecated:
        logger.warning('channel command is deprecated in favor of label')

    if args.copy:
        aserver_api.copy_channel(args.copy[0], owner, args.copy[1])
        logger.info('Copied %s %s to %s', name, *tuple(args.copy))
    elif args.remove:
        aserver_api.remove_channel(args.remove, owner)
        logger.info('Removed %s %s', name, args.remove)
    elif args.list:
        logger.info(name.title())
        for channel, info in aserver_api.list_channels(owner).items():
            if isinstance(info, int):  # OLD API
                logger.info(' + %s ', channel)
            else:
                logger.info(' + %s%s ', channel, '[locked]' if info['is_locked'] else '')

    elif args.show:
        info = aserver_api.show_channel(args.show, owner)
        logger.info('%s %s %s', name.title(), args.show, '[locked]' if info['is_locked'] else '')
        for file in info['files']:
            logger.info('  + %(full_name)s', file)
    elif args.lock:
        aserver_api.lock_channel(args.lock, owner)
        logger.info('%s %s is now locked', name.title(), args.lock)
    elif args.unlock:
        aserver_api.unlock_channel(args.unlock, owner)
        logger.info('%s %s is now unlocked', name.title(), args.unlock)
    else:
        raise NotImplementedError()


def _add_parser(subparsers, name, deprecated=False):
    deprecated_warn = ''
    if deprecated:
        deprecated_warn = '[DEPRECATED in favor of label] \n'

    subparser = subparsers.add_parser(
        name,
        help='{}Manage your Anaconda repository {}s'.format(deprecated_warn, name),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__)

    subparser.add_argument('-o', '--organization',
                           help='Manage an organizations {}s'.format(name))

    group = subparser.add_mutually_exclusive_group(required=True)

    group.add_argument('--copy', nargs=2, metavar=name.upper())
    group.add_argument(
        '--list',
        action='store_true',
        help='{}list all {}s for a user'.format(deprecated_warn, name)
    )
    group.add_argument(
        '--show',
        metavar=name.upper(),
        help='{}Show all of the files in a {}'.format(deprecated_warn, name)
    )
    group.add_argument(
        '--lock',
        metavar=name.upper(),
        help='{}Lock a {}'.format(deprecated_warn, name))
    group.add_argument(
        '--unlock',
        metavar=name.upper(),
        help='{}Unlock a {}'.format(deprecated_warn, name)
    )
    group.add_argument(
        '--remove',
        metavar=name.upper(),
        help='{}Remove a {}'.format(deprecated_warn, name)
    )
    subparser.set_defaults(main=functools.partial(main, name=name, deprecated=deprecated))


def add_parser(subparsers):
    _add_parser(subparsers, name='label')
    _add_parser(subparsers, name='channel', deprecated=True)


def _parse_optional_tuple(value: Tuple[str, str]) -> Optional[List[str]]:
    # Convert a sentinel tuple of empty strings to None, since it is not possible with typer parser or callback
    if value == ('', ''):
        return None
    return list(value)


def mount_subcommand(app: typer.Typer, name: str, hidden: bool, help_text: str, context_settings: dict) -> None:
    @app.command(
        name=name,
        hidden=hidden,
        help=help_text,
        context_settings=context_settings,
        no_args_is_help=True,
    )
    def channel(
        ctx: typer.Context,
        organization: Optional[str] = typer.Option(
            None,
            '-o',
            '--organization',
            help='Manage an organizations {}s'.format(name),
        ),
        copy: Tuple[str, str] = typer.Option(
            ('', ''),
            help=f'Copy a package from one {name} to another',
            show_default=False,
        ),
        list_: bool = typer.Option(
            False,
            '--list',
            is_flag=True,
            help=f'List all {name}s for a user',
        ),
        show: Optional[str] = typer.Option(
            None,
            help=f'Show all of the files in a {name}',
        ),
        lock: Optional[str] = typer.Option(
            None,
            help=f'Lock a {name}',
        ),
        unlock: Optional[str] = typer.Option(
            None,
            help=f'Unlock a {name}',
        ),
        remove: Optional[str] = typer.Option(
            None,
            help=f'Remove a {name}',
        ),
    ) -> None:
        # pylint: disable=too-many-arguments
        parsed_copy = _parse_optional_tuple(copy)
        args = argparse.Namespace(
            token=ctx.obj.params.get('token'),
            site=ctx.obj.params.get('site'),
            organization=organization,
            copy=parsed_copy,
            list=list_,
            show=show,
            lock=lock,
            unlock=unlock,
            remove=remove,
        )

        main(args, name='channel', deprecated=True)
