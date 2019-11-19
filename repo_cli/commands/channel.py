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
        logger.info(f'Channel {channel} {action} action successful on {base_url}')
        if callable(success_handler):
            success_handler(response)
        logger.debug(f'Server responded with response {response.status_code}\nData: {response.content}')
    else:
        msg = f'Error executing {channel} {action} action on {base_url}.' \
            f'Server responded with status code {response.status_code}.\n' \
            f'Error details: {response.content}'
        logger.error(msg)
        if response.status_code in authz_fail_codes:
            raise errors.Unauthorized()

def create_channel(base_url, token, channel):
    '''Create a new channel with name `channel` on the repo server at `base_url` using `token`
    to authenticate.

    Args:
          base_url(str): url to the repo server api
          token(str): user token to be use for authentication and authorization
          channel(str): name of the channel to be created

    Returns:
          response (http response object)
    '''
    url = join(base_url, 'channels')
    data = {'name': channel}
    logger.debug(f'Creating channel {channel} on {base_url}')
    logger.debug(f'Using token {token} on {base_url}')
    response = requests.post(url, json=data, headers={
        'X-Auth': f'{token}',
        'Content-Type': 'application/json',
    })
    if response.status_code in [201]:
        logger.info(f'Channel {channel} successfully created on {base_url}')
        logger.debug(f'Server responded with {response.status_code}\nData: {response.content}')
    else:
        msg = f'Error creating {channel} on {base_url}.' \
            f'Server responded with status code {response.status_code}.\n' \
            f'Error details: {response.content}'
        logger.error(msg)
        if response.status_code in [403, 401]:
            raise errors.Unauthorized()
    return response

def remove_channel(base_url, token, channel):
    url = join(base_url, 'channels', channel)
    logger.debug(f'Deleting channel {channel} on {base_url}')
    logger.debug(f'Using token {token} on {base_url}')
    response = requests.delete(url, headers={
        'X-Auth': f'{token}',
        'Content-Type': 'application/json',
    })
    if response.status_code in [201]:
        logger.info(f'Channel {channel} successfully deleted on {base_url}')
        logger.debug(f'Server responded with {response.status_code}\nData: {response.content}')
    else:
        msg = f'Error creating {channel} on {base_url}.' \
            f'Server responded with status code {response.status_code}.\n' \
            f'Error details: {response.content}'
        logger.error(msg)
        if response.status_code in [403, 401]:
            raise errors.Unauthorized()
    return response


def update_channel(base_url, token, channel, success_message=None, **data):
    url = join(base_url, 'channels', channel)
    logger.debug(f'Updating channel {channel} on {base_url}')
    logger.debug(f'Using token {token} on {base_url}')
    response = requests.put(url, json=data, headers={
        'X-Auth': f'{token}',
        'Content-Type': 'application/json',
    })
    if not success_message:
        success_message = f'Channel {channel} successfully update on {base_url}.'
    if response.status_code in [204]:
        logger.info(success_message)
        logger.debug(f'Server responded with {response.status_code}\nData: {response.content}')
    else:
        msg = f'Error creating {channel} on {base_url}.' \
            f'Server responded with status code {response.status_code}.\n' \
            f'Error details: {response.content}'
        logger.error(msg)
        if response.status_code in [403, 401]:
            raise errors.Unauthorized()
    return response

def show_channel(base_url, token, channel):
    url = join(base_url, 'channels', channel)
    logger.debug(f'Getting channek info with token {token} on {base_url}')
    response = requests.get(url, headers={
        'X-Auth': f'{token}',
        'Content-Type': 'application/json',
    })
    handle_response(response, channel, base_url, success_codes=[200], authz_fail_codes=[401, 403],
                    action='show', success_handler=show_channel_detail)


def list_channels(base_url, token):
    url = join(base_url, 'channels')
    logger.debug(f'Getting channels info with token {token} on {base_url}')
    response = requests.get(url, headers={
        'X-Auth': f'{token}',
        'Content-Type': 'application/json',
    })
    handle_response(response, '', base_url, success_codes=[200], authz_fail_codes=[401, 403],
                    action='list', success_handler=show_list_channels)


def show_channel_detail(response):
    data = response.json()
    resp = ["Channel details:", '']
    keymap = {'download_count': 'downloads', 'artifact_count': 'artifacts'}
    for key in ['name', 'description', 'privacy', ]:
        resp.append("%s: %s" % (keymap.get(key, key), data.get(key, '')))
    resp.append("")
    logger.info('\n'.join(resp))


def show_list_channels(response):
    data = response.json()
    resp = ["Channels available to the user:", '']
    keymap = {'download_count': 'downloads', 'artifact_count': 'artifacts'}
    cols_ = ['name', 'privacy', 'description', 'artifact_count', 'download_count']
    cols = [keymap.get(key, key) for key in cols_]
    resp.append('\t'.join(cols))
    for ch in data:
        resp.append('\t'.join([str(ch.get(key, '')) for key in cols_]))

    resp.append('')
    logger.info('\n'.join(resp))


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

    logger.info("")
    if args.create:
        if not channel:
            msg = 'Channel name not specified. Please use -n or -o to specify your channel.\n'\
                  'Use --help for help.'
            logger.info(msg)
            raise errors.RepoCLIError(msg)

        create_channel(url, token, channel)
    elif args.copy:
        # aserver_api.copy_channel(args.copy[0], channel, args.copy[1])
        # logger.info("Copied {} {} to {}".format(name, *tuple(args.copy)))
        logger.info("Copy operation not yet implemented.")
    elif args.remove:
        remove_channel(url, token, args.remove)
    elif args.list:
        list_channels(url, token)
    elif args.show:
        show_channel(url, token, args.show)
    elif args.lock:
        channel = args.lock
        msg = "{} {} is now locked".format(name.title(), channel)
        update_channel(url, token, channel, privacy='private', success_message=msg)
    elif args.soft_lock:
        channel = args.soft_lock
        msg = "{} {} is now soft-locked".format(name.title(), channel)
        update_channel(url, token, channel, privacy='authenticated', success_message=msg)
    elif args.unlock:
        channel = args.unlock
        msg = "{} {} is now unlocked".format(name.title(), channel)
        update_channel(url, token, channel, privacy='public', success_message=msg)
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
        '--soft-lock',
        metavar=name.upper(),
        help="{}Soft Lock a {}, so that only authenticated users can see it.".format(deprecated_warn, name))
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
