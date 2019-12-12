"""
Manage your Anaconda repository channels.
"""

from __future__ import unicode_literals, print_function

import argparse
from .base import SubCommandBase
from ..utils.format import CVEFormatter

class SubCommand(SubCommandBase):
    name = "cves"

    def main(self):
        self.log.info("")
        args = self.args
        if args.list:
            self.show_list(args.offset, args.limit)
        elif args.show:
            self.show(args.show)
        else:
            raise NotImplementedError()

    def show_list(self, offset=0, limit=20):
        data = self.api.get_cves(offset, limit)
        self.log.info(CVEFormatter.format_list(data['items']))
        self.log.info('')

    def show(self, cve):
        data = self.api.get_cve(cve)
        self.log.info(CVEFormatter.format_detail(data))
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

        group = subparser.add_mutually_exclusive_group(required=True)

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


        subparser.add_argument(
            '-o', '--offset', default=0, type=int,
            help='Offset when displaying the results'
        )
        subparser.add_argument(
            '-l', '--limit', default=50, type=int,
            help='Offset when displaying the results'
        )

        subparser.set_defaults(main=self.main)
