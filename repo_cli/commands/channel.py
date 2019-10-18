"""
Manage your Anaconda repository channels.
"""

from __future__ import unicode_literals, print_function

from os.path import join

import functools
import logging
import argparse
import requests
from .. import errors
from ..utils.config import get_config, DEFAULT_URL
from binstar_client.utils import get_server_api

logger = logging.getLogger('repo_cli')


def create_channel(base_url, token, channel):
    url = join(base_url, 'channels')
    data = {'name': channel}
    logger.error(f'Creating channel {channel} on {base_url}')
    logger.error(f'Using token {token} on {base_url}')
    response = requests.post(url, json=data, headers={
        'X-Auth': f'{token}',
        'Content-Type': 'application/json',
    })
    if response.status_code in [201]:
        logger.error(f'Channel {channel} successfully created on {base_url} with response {response.status_code}')
        logger.error(f'Server responded with {response.content}')
    else:
        msg = f'Error creating {channel} on {base_url}.' \
            f'Server responded with status code {response.status_code}.\n' \
            f'Error details: {response.content}'
        logger.error(msg)
        if response.status_code in [403, 401]:
            raise errors.Unauthorized()
    return response

def main(args, name, deprecated=False):
    aserver_api = get_server_api(args.token, args.site)

    # if args.organization:
    channel = args.name
    # else:
    #     current_user = aserver_api.user()
    #     owner = current_user['login']
    # if not args.name:
    #     raise errors.RepoCLIError()
    config = get_config(site=args.site)

    token = args.token
    if not token:
        raise errors.Unauthorized()
    url = config.get('url', DEFAULT_URL)

    if deprecated:
        logger.warning('channel command is deprecated in favor of label')

    if args.create:
        create_channel(url, token, channel)
    elif args.copy:
        aserver_api.copy_channel(args.copy[0], channel, args.copy[1])
        logger.info("Copied {} {} to {}".format(name, *tuple(args.copy)))
    elif args.remove:
        aserver_api.remove_channel(args.remove, channel)
        logger.info("Removed {} {}".format(name, args.remove))
    elif args.list:
        logger.info('{}s'.format(name.title()))
        for channel, info in aserver_api.list_channels(channel).items():
            if isinstance(info, int):  # OLD API
                logger.info((' + %s ' % channel))
            else:
                logger.info((' + %s ' % channel) + ('[locked]' if info['is_locked'] else ''))

    elif args.show:
        info = aserver_api.show_channel(args.show, channel)
        logger.info('{} {} {}'.format(
            name.title(),
            args.show,
            ('[locked]' if info['is_locked'] else '')
        ))
        for f in info['files']:
            logger.info('  + %(full_name)s' % f)
    elif args.lock:
        aserver_api.lock_channel(args.lock, channel)
        logger.info("{} {} is now locked".format(name.title(), args.lock))
    elif args.unlock:
        aserver_api.unlock_channel(args.unlock, channel)
        logger.info("{} {} is now unlocked".format(name.title(), args.unlock))
    else:
        raise NotImplementedError()


def _add_parser(subparsers, name, deprecated=False):
    deprecated_warn = ""
    if deprecated:
        deprecated_warn = "[DEPRECATED in favor of label] \n"

    subparser = subparsers.add_parser(
        name,
        help='{}Manage your Anaconda repository {}s'.format(deprecated_warn, name),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__)

    subparser.add_argument('-n', '--name',
                           help="Manage a {}s".format(name), required=True)

    group = subparser.add_mutually_exclusive_group(required=True)

    group.add_argument('--copy', nargs=2, metavar=name.upper())
    group.add_argument(
        '--create',
        action='store_true',
        help="{}list all {}s for a user".format(deprecated_warn, name)
    )
    group.add_argument(
        '--list',
        action='store_true',
        help="{}list all {}s for a user".format(deprecated_warn, name)
    )
    group.add_argument(
        '--show',
        metavar=name.upper(),
        help="{}Show all of the files in a {}".format(deprecated_warn, name)
    )
    group.add_argument(
        '--lock',
        metavar=name.upper(),
        help="{}Lock a {}".format(deprecated_warn, name))
    group.add_argument(
        '--unlock',
        metavar=name.upper(),
        help="{}Unlock a {}".format(deprecated_warn, name)
    )
    group.add_argument(
        '--remove',
        metavar=name.upper(),
        help="{}Remove a {}".format(deprecated_warn, name)
    )
    subparser.set_defaults(main=functools.partial(main, name=name, deprecated=deprecated))

def add_parser(subparsers):
    # _add_parser(subparsers, name="label")
    _add_parser(subparsers, name="channel")#, deprecated=True)
