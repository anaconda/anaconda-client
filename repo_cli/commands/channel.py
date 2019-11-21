"""
Manage your Anaconda repository channels.
"""

from __future__ import unicode_literals, print_function

from os.path import join

import functools
import logging
import argparse
import requests
from pprint import pformat
from .. import errors
from ..utils.config import get_config, DEFAULT_URL
from ..utils.artifacts import SimplePackageSpec
from .base import SubCommandBase

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


class SubCommand(SubCommandBase):
    name = "channel"


    def main(self):
        # channel = self.args.name or self.args.organization
        # else:
        #     current_user = aserver_api.user()
        #     owner = current_user['login']
        # if not args.name:
        #     raise errors.RepoCLIError()

        self.log.info("")
        if self.args.create:
            channel = self.args.create
            if not channel:
                msg = 'Channel name not specified. Please use -n or -o to specify your channel.\n' \
                      'Use --help for help.'
                logger.info(msg)
                raise errors.RepoCLIError(msg)

            self.api.create_channel(channel)
        elif self.args.copy:
            # aserver_api.copy_channel(args.copy[0], channel, args.copy[1])
            # logger.info("Copied {} {} to {}".format(name, *tuple(args.copy)))
            self.log.info("Copy operation not yet implemented.")
        elif self.args.remove:
            self.api.remove_channel(self.args.remove)
        elif self.args.list:
            self.list_user_channels()
        elif self.args.list_packages:
            for spec in self.args.list_packages:
                self.show_channel_packages(spec)
        elif self.args.list_files:
            for spec in self.args.list_files:
                self.show_channel_files(spec, family=self.args.family, full_details=self.args.full_details)
        elif self.args.show:
            self.show_channel(self.args.show)
        elif self.args.lock:
            channel = self.args.lock
            msg = "{} {} is now locked".format(self.name.title(), channel)
            self.api.update_channel(channel, privacy='private', success_message=msg)
        elif self.args.soft_lock:
            channel = self.args.soft_lock
            msg = "{} {} is now soft-locked".format(self.name.title(), channel)
            self.api.update_channel(channel, privacy='authenticated', success_message=msg)
        elif self.args.unlock:
            channel = self.args.unlock
            msg = "{} {} is now unlocked".format(self.name.title(), channel)
            self.api.update_channel(channel, privacy='public', success_message=msg)
        else:
            raise NotImplementedError()

    def show_channel_packages(self, spec):
        packages = self.api.get_channel_artifacts(spec.channel)
        self.log.info('')
        self.log.info('Total packages matching spec %s found: %s\n' % (spec, len(packages)))
        for package in packages:
            self.show_package_detail(package)
        self.log.info('')

    def show_package_detail(self, package):
        keymap = {'download_count': '# of downloads', 'file_count': '# of files',}
        pack = dict(package)
        pack.update(package['metadata'])
        resp = ["---------------"]

        for key in ['name', 'file_count', 'download_count', 'license', 'description']:
            label = keymap.get(key, key)
            value = pack.get(key, '')
            resp.append("%s: %s" % (label, value))

        self.log.info('\n'.join(resp))

    def show_channel_files(self, spec, family, full_details=False):
        packages = self.api.get_channel_artifacts_files(
            spec.channel, family, spec.package, spec.version, spec.filename, return_raw=full_details
        )

        if not packages:
            logger.warning('No files matches were found for the provided spec: %s\n' % (spec))
            return

        files_descr = []
        for filep in packages:
            if full_details:
                files_descr.append("----------------\n%s\n" % pformat(filep))
            else:
                files_descr.append(
                    '----------------\n{name}/{version}//{ckey}\n'.format(**filep))

        affected_files = '\n'.join(sorted(files_descr))
        msg = 'Found %s files matching the specified spec %s:\n\n%s\n' % (len(files_descr), spec, affected_files)
        self.log.info(msg)

    def show_channel(self, channel):
        response = self.api.get_channel(channel)
        handle_response(response, channel, self.api.base_url,
                        success_codes=[200], authz_fail_codes=[401, 403],
                        action='show', success_handler=self.show_channel_detail)

    def show_channel_detail(self, response):
        data = response.json()
        resp = ["Channel details:", '']
        keymap = {'download_count': '# of downloads', 'artifact_count': '# of artifacts', 'download_count': '# of downloads',
                  'mirror_count': '# mirrors', 'subchannel_count': '# of subchannels'}

        for key in ['name', 'description', 'privacy', 'artifact_count', 'download_count', 'mirror_count',
                    'subchannel_count', 'created', 'updated']:
            label = keymap.get(key, key)
            value = data.get(key, '')
            resp.append("\t%s: %s" % (label, value))

        owners = ', '.join(data['owners'])
        resp.append('\towners: %s' % owners)
        resp.append("")
        logger.info('\n'.join(resp))

    def list_user_channels(self):
        response = self.api.list_user_channels()
        handle_response(response, '', self.api.base_url, success_codes=[200], authz_fail_codes=[401, 403],
                        action='list', success_handler=show_list_channels)

    def show_list_channels(self, response):
        data = response.json()
        resp = ["Channels available to the user:", '']
        keymap = {'download_count': 'downloads', 'artifact_count': 'artifacts'}
        cols_ = ['name', 'privacy', 'description', 'artifact_count', 'download_count']
        cols = [keymap.get(key, key) for key in cols_]
        resp.append('\t'.join(cols))
        for ch in data:
            resp.append('\t'.join([str(ch.get(key, '')) for key in cols_]))

        resp.append('')
        self.log.info('\n'.join(resp))

    def add_parser(self, subparsers):
        subparser = subparsers.add_parser(
            self.name,
            help='Manage your Anaconda repository {}s'.format(self.name),
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description=__doc__)
        subparser.add_argument('--family',
                               default='conda',
                               help='artifact family (i.e.: conda, pypy, cran). ONLY USED IN COMBINATION '
                                    'WITH --list-files, ignored otherwise.', action='store_true')
        subparser.add_argument('--full-details', help='Prints full file details. ONLY USED IN COMBINATION '
                                    'WITH --list-files, ignored otherwise.', action='store_true')

        group = subparser.add_mutually_exclusive_group(required=True)

        group.add_argument('--copy', nargs=2, metavar=self.name.upper())
        group.add_argument(
            '--create',
            # action='store_true',
            metavar=self.name.upper(),
            help="Create a new {}".format(self.name)
        )
        group.add_argument(
            '--list',
            action='store_true',
            help="list all {}s for a user".format(self.name)
        )
        group.add_argument('--list-packages',
                            help='Package written as <channel>/<subchannel>]]',
                            type=SimplePackageSpec.from_string, nargs='+')
        group.add_argument('--list-files',
                           help='Package written as <channel>/<subchannel>[::<package>[/<version>[/<filename>]]]',
                           type=SimplePackageSpec.from_string, nargs='+')
        group.add_argument(
            '--show',
            metavar=self.name.upper(),
            help="Show all of the files in a {}".format(self.name)
        )
        group.add_argument(
            '--lock',
            metavar=self.name.upper(),
            help="Lock a {}".format(self.name))
        group.add_argument(
            '--soft-lock',
            metavar=self.name.upper(),
            help="Soft Lock a {}, so that only authenticated users can see it.".format(self.name))
        group.add_argument(
            '--unlock',
            metavar=self.name.upper(),
            help="Unlock a {}".format(self.name)
        )
        group.add_argument(
            '--remove',
            metavar=self.name.upper(),
            help="Remove a {}".format(self.name)
        )
        subparser.set_defaults(main=self.main)
