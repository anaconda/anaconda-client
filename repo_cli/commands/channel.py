"""
Manage your Anaconda repository channels.
"""

from __future__ import unicode_literals, print_function

import argparse
from pprint import pformat
from .. import errors
from ..utils.artifacts import SimplePackageSpec
from .base import SubCommandBase
from ..utils import format

class SubCommand(SubCommandBase):
    name = "channel"

    def main(self):
        self.log.info("")
        if self.args.create:
            channel = self.args.create
            if not channel:
                msg = 'Channel name not specified. Please use -n or -o to specify your channel.\n' \
                      'Use --help for help.'
                self.log.info(msg)
                raise errors.RepoCLIError(msg)

            self.api.create_channel(channel)
            self.log.info("Channel %s successfully created" % channel)
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
            self.show_channel(self.args.show, full_details=self.args.full_details)
        elif self.args.history:
            self.show_channel_history(self.args.history, self.args.offset, self.args.limit, self.args.full_details)
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
            self.log.warning('No files matches were found for the provided spec: %s\n' % (spec))
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

    def show_channel(self, channel, full_details):
        channel_data = self.api.get_channel(channel)
        if full_details and not self.api.is_subchannel(channel):
            channel_data['subchannels'] = self.api.get_channel_subchannels(channel)

        self.show_channel_detail(channel_data)

    def show_channel_history(self, channel, offset, limit, full_details):
        data = self.api.get_channel_history(channel, offset, limit)
        self.log.info(format.HistoryFormatter.format_list(data['items'], not full_details))
        self.log.info('')

    def show_channel_detail(self, data):
        resp = ["Channel details:", '']
        keymap = {'download_count': '# of downloads', 'artifact_count': '# of artifacts', 'download_count': '# of downloads',
                  'mirror_count': '# mirrors', 'subchannel_count': '# of subchannels'}

        for key in ['name', 'description', 'privacy', 'artifact_count', 'download_count', 'mirror_count',
                    'subchannel_count', 'created', 'updated']:
            label = keymap.get(key, key)
            value = data.get(key, '')
            resp.append("\t%s: %s" % (label, value))

        try:
            owners = ', '.join(data.get('owners', ['']))
        except TypeError:
            owners = ''
        resp.append('\towners: %s' % owners)
        if 'subchannels' in data:
            resp.append("")
            resp.append("\tSubchannels:")
            resp.append("\t------------")

            resp.append(format.PackagesFormatter.format_channel_header())
            for subchannel in data['subchannels']:
                resp.append(format.PackagesFormatter.format_channel(subchannel))

        resp.append("")
        self.log.info('\n'.join(resp))

    def list_user_channels(self):
        self.show_list_channels(self.api.list_user_channels())

    def show_list_channels(self, data):
        resp = ["Channels available to the user:", '']
        keymap = {'download_count': 'downloads', 'artifact_count': 'artifacts'}
        cols_ = ['name', 'privacy', 'description', 'artifact_count', 'download_count']
        cols = [keymap.get(key, key) for key in cols_]
        resp.append('\t'.join(cols))

        for ch in data['items']:
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
                                    'WITH --list-files, ignored otherwise.')
        subparser.add_argument('--full-details', help='Prints full file details. ONLY USED IN COMBINATION '
                                    'WITH --list-files or --show ignored otherwise.', action='store_true')

        subparser.add_argument(
            '-o', '--offset', default=0, type=int,
            help='Offset when displaying the results'
        )
        subparser.add_argument(
            '-l', '--limit', default=50, type=int,
            help='Offset when displaying the results'
        )

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
            '--history',
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
