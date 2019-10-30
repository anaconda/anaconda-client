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

logger = logging.getLogger('repo_cli')



def handle_response(response, channel, base_url, success_codes, authz_fail_codes, action, success_handler=None):
    if response.status_code in success_codes:
        logger.info(f'Channel {channel} {action} action successful on {base_url} with response {response.status_code}')
        if callable(success_handler):
            success_handler(response)
        logger.debug(f'Server responded with {response.content}')
    else:
        msg = f'Error executing {channel} {action} action on {base_url}.' \
            f'Server responded with status code {response.status_code}.\n' \
            f'Error details: {response.content}'
        logger.error(msg)
        if response.status_code in authz_fail_codes:
            raise errors.Unauthorized()

def create_channel(base_url, token, channel):
    url = join(base_url, 'channels')
    data = {'name': channel}
    logger.debug(f'Creating channel {channel} on {base_url}')
    logger.debug(f'Using token {token} on {base_url}')
    response = requests.post(url, json=data, headers={
        'X-Auth': f'{token}',
        'Content-Type': 'application/json',
    })
    if response.status_code in [201]:
        logger.info(f'Channel {channel} successfully created on {base_url} with response {response.status_code}')
        logger.debug(f'Server responded with {response.content}')
    else:
        msg = f'Error creating {channel} on {base_url}.' \
            f'Server responded with status code {response.status_code}.\n' \
            f'Error details: {response.content}'
        logger.error(msg)
        if response.status_code in [403, 401]:
            raise errors.Unauthorized()
    return response


def show_channel_detail(response):
    data = response.json()
    resp = ["Channel details:", '']
    keymap = {'download_count': 'downloads', 'artifact_count': 'artifacts'}
    for key in ['name', 'description', 'privacy', ]:
        resp.append("%s: %s" % (keymap.get(key, key), data.get(key, '')))

    logger.info('\n'.join(resp))


def lsit_channels(response):
    data = response.json()
    resp = ["Channels available to the user:", '']

    for channel in data:
        resp.append(channel)
    resp.append('')
    logger.info('\n'.join(resp))


def show_channel(base_url, token, channel):
    url = join(base_url, 'channels', channel)
    logger.debug(f'Getting channek info with token {token} on {base_url}')
    response = requests.get(url, headers={
        'X-Auth': f'{token}',
        'Content-Type': 'application/json',
    })
    handle_response(response, channel, base_url, success_codes=[200], authz_fail_codes=[401, 403],
                    action='show', success_handler=show_channel_detail)


def main(args, name, deprecated=False):
    # aserver_api = get_server_api(args.token, args.site)

    # if args.organization:
    channel = args.name or args.organization
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
        if not channel:
            raise errors.RepoCLIError('Channel name not specified. '
                                      'Please use -n or -o to specify your channel.\n'
                                      'Use --help for help.')

        create_channel(url, token, channel)
    elif args.copy:
        # aserver_api.copy_channel(args.copy[0], channel, args.copy[1])
        # logger.info("Copied {} {} to {}".format(name, *tuple(args.copy)))
        logger.info("Copy operation not yet implemented.")
    elif args.remove:
        # aserver_api.remove_channel(args.remove, channel)
        # logger.info("Removed {} {}".format(name, args.remove))
        logger.info("Remove operation not yet implemented.")
    elif args.list:
        # logger.info('{}s'.format(name.title()))
        # for channel, info in aserver_api.list_channels(channel).items():
        #     if isinstance(info, int):  # OLD API
        #         logger.info((' + %s ' % channel))
        #     else:
        #         logger.info((' + %s ' % channel) + ('[locked]' if info['is_locked'] else ''))
        logger.info("List operation not yet implemented.")

    elif args.show:
        show_channel(url, token, args.show)
        # info = aserver_api.show_channel(args.show, channel)
        # logger.info('{} {} {}'.format(
        #     name.title(),
        #     args.show,
        #     ('[locked]' if info['is_locked'] else '')
        # ))
        # for f in info['files']:
        #     logger.info('  + %(full_name)s' % f)

    elif args.lock:
        # aserver_api.lock_channel(args.lock, channel)
        # logger.info("{} {} is now locked".format(name.title(), args.lock))
        logger.info("Lock operation not yet implemented.")
    elif args.unlock:
        # aserver_api.unlock_channel(args.unlock, channel)
        # logger.info("{} {} is now unlocked".format(name.title(), args.unlock))
        logger.info("Unlock operation not yet implemented.")
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


    # keeping both these to support old anaconda-client interface
    # TODO: Maybe we should replace -n with -c as conda specified channels...
    subparser.add_argument('-n', '--name',
                           help="Manage a {}s".format(name))

    subparser.add_argument('-o', '--organization',
                           help="Manage an organizations {}s".format(name))

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
