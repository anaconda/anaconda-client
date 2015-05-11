"""
Usage:
    binstar notebook upload notebook
    binstar notebook upload project/notebook
    binstar notebook upload project/notebook-file.ipynb
    binstar notebook download project
    binstar notebook download project/notebook-file[.ipynb]
"""

from __future__ import unicode_literals
import argparse
import logging

log = logging.getLogger("binstar.notebook")


def add_parser(subparsers):

    description = 'Upload/Download notebooks to/from binstar'
    parser = subparsers.add_parser('notebook',
                                   formatter_class=argparse.RawDescriptionHelpFormatter,
                                   help=description,
                                   description=description,
                                   epilog=__doc__)

    parser.add_argument(
        'action',
        choices=['upload', 'download']
    )

    mgroup = parser.add_argument_group('metadata options')
    mgroup.add_argument('-v', '--version', help='Notebook version')
    mgroup.add_argument('-s', '--summary', help='Set the summary of the notebook')

    parser.add_argument(
        '-u', '--user',
        help='User account, defaults to the current user'
    )

    parser.add_argument(
        'notebook',
        help="project/notebook or notebook's filename",
        action='store',
        default=None,
        nargs='?'
    )

    parser.set_defaults(main=main)


def main(args):
    print(args)
