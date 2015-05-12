"""
Usage:
    binstar notebook upload notebook.ipynb
    binstar notebook upload project:PATH/TO/notebook.ipynb
    binstar notebook download project
    binstar notebook download project:notebook
"""

from __future__ import unicode_literals
import argparse
import logging
from binstar_client import errors
from binstar_client.utils import get_binstar
from binstar_client.utils.notebook import parse, Uploader

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
        action='store'
    )

    parser.set_defaults(main=main)


def main(args):
    """
    1) test if filename exist
    2) Detect project name or generate it from the notebook
    3) generate version with timestamp
    4) Extract summary from notebook file
    """
    if args.action == 'upload':
        project, notebook = parse(args.name)
        binstar = get_binstar(args)
        uploader = Uploader(binstar, project, notebook, user=args.user, version=args.version, summary=args.summary)
        if uploader.upload(force=False):
            print("Done")
        else:
            raise errors.BinstarError(uploader.msg)
    elif args.action == 'download':
        raise errors.BinstarError("Download notebooks hasn't been implemented yet. Soon!")
