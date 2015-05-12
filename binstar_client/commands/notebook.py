"""
Usage:
    binstar notebook upload project notebook.ipynb
    binstar notebook upload project directory/

Deprecated:
    binstar notebook upload notebook.ipynb
    binstar notebook upload project:PATH/TO/notebook.ipynb
    binstar notebook download project
    binstar notebook download project:notebook
"""

from __future__ import unicode_literals
import os
import argparse
import logging
from binstar_client import errors
from binstar_client.utils import get_binstar
from binstar_client.utils.notebook import Finder, Uploader

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
        'project',
        help="project to upload/download",
        action='store'
    )

    parser.add_argument(
        'files',
        help='Files to puload',
        action='append',
        default=[]
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
        binstar = get_binstar(args)
        finder = Finder(args.files)
        valid, invalid = finder.parse()

        uploader = Uploader(binstar, args.project, username=args.user, version=args.version, summary=args.summary)
        for filename in valid:
            if uploader.upload(filename, force=False):
                log.info("{} has been uploaded.".format(filename))
            else:
                raise errors.BinstarError(uploader.msg)
        for filename in invalid:
            log.info("{} can't be uploaded.".format(filename))

    elif args.action == 'download':
        raise errors.BinstarError("Download notebooks hasn't been implemented yet. Soon!")
