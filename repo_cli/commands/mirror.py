"""
Manage your Anaconda repository channels.
"""

from __future__ import unicode_literals, print_function

import argparse
from pprint import pformat
from .. import errors
from ..utils.artifacts import SimplePackageSpec
from .base import SubCommandBase
from ..utils.format import MirrorFormatter

class SubCommand(SubCommandBase):
    name = "mirror"

    def main(self):
        self.log.info("")
        args = self.args
        if args.create:
            self.create_mirror(args.channel, args.source, args.create, args.mode,
                               args.type, args.cron, args.run_now)
        elif args.delete:
            self.delete(args.channel, args.delete)

        elif args.list:
            self.show_list(args.channel)

        elif args.show:
            self.show(args.channel, args.show)

        else:

            raise NotImplementedError()

    def create_mirror(self, channel, source, name, mode, type_, cron, run_now):
        self.api.create_mirror(channel, source, name, mode, type_, cron, run_now)
        self.log.info('Mirror %s successfully created on channel %s', name, channel)


    def show_list(self, channel):
        data = self.api.get_mirrors(channel)
        self.log.info(MirrorFormatter.format_list(data))
        self.log.info('')

    def show(self, channel, name):
        # TODO: Get mirror api is currently unavailable so we need to use the
        #       GET mirrors api and filter by name...
        # data = self.api.get_mirror(channel, name)

        data = self.api.get_mirrors(channel)
        for mirror in data:
            if mirror['mirror_name'] == name:
                self.log.info(MirrorFormatter.format_detail(mirror))

        self.log.info('')

    def delete(self, channel, name):
        self.api.delete_mirror(channel, name)
        self.log.info('Mirror %s successfully delete on channel %s', name, channel)


    def add_parser(self, subparsers):
        subparser = subparsers.add_parser(
            self.name,
            help='Manage your Anaconda repository {}s'.format(self.name),
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description=__doc__)

        subparser.add_argument('--channel', '-c', help='Channel to mirror to.')
        group = subparser.add_mutually_exclusive_group(required=True)

        # group.add_argument('--create', nargs=2, metavar=self.name.upper())
        group.add_argument(
            '--create',
            metavar=self.name.upper(),
            help="Create a new {}".format(self.name)
        )
        group.add_argument(
            '--delete',
            metavar=self.name.upper(),
            help="Create a new {}".format(self.name)
        )
        group.add_argument(
            '--list',
            action='store_true',
            help="list all {}s for a user".format(self.name)
        )
        group.add_argument(
            '--show',
            metavar=self.name.upper(),
            help="Show all of the files in a {}".format(self.name)
        )

        # import pdb; pdb.set_trace()

        subparser.add_argument('--source', '-s', help='Path to the source channel to mirror. '
                                                   'I.e.: https://conda.anaconda.org/conda-test')
        subparser.add_argument('--name', '-n', help='Name of the mirror')

        # {"mirror_name": "mirror-from-el", "mirror_mode": "active", "mirror_type": "conda", "cron": "0 0 * * *",
        #  "source_root": "http://repo-wip.dev.anaconda.com/api/repo/ekoch/", "run_now": true}
        subparser.add_argument(
            '--mode',
            default='active',
            help='Mirror mode. If "active", will download all the files from the source channel '
                 'immediately else, if "passive", download JSON immediately and files on demand '
                 'later'
        )
        subparser.add_argument(
            '--type',
            default='conda',
            help='Mirror type. Possible types: "conda", "python_simple" and "CRAN"'
        )
        subparser.add_argument(
            '--cron',
            default='0 0 * * *',
            help='Cron string to configure the mirror job.'
        )
        subparser.add_argument(
            '--run_now',
            action='store_false',
            help='Determines whether the mirror job should run immediately or '
                 'according to the cron schedule'
        )

        subparser.set_defaults(main=self.main)
