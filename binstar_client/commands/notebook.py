"""
Usage:
    binstar notebook upload project notebook.ipynb
    binstar notebook upload project directory
    binstar notebook download project
    binstar notebook download project:notebook
"""

from __future__ import unicode_literals
import os
import argparse
import logging
from binstar_client import errors
from binstar_client.utils import get_binstar
from binstar_client.utils.notebook import Finder, Uploader, SCM, local_files

log = logging.getLogger("binstar.notebook")


def add_parser(subparsers):

    description = 'Interact with notebooks in binstar'
    parser = subparsers.add_parser('notebook',
                                   formatter_class=argparse.RawDescriptionHelpFormatter,
                                   help=description,
                                   description=description,
                                   epilog=__doc__)

    nb_subparsers = parser.add_subparsers()
    add_upload_parser(nb_subparsers)
    add_download_parser(nb_subparsers)


def add_upload_parser(subparsers):
    description = "Upload a notebook to anaconda.org"
    epilog = """
    Usage:
        binstar notebook upload notebook.ipynb
    """
    parser = subparsers.add_parser('upload',
                                   formatter_class=argparse.RawDescriptionHelpFormatter,
                                   help=description,
                                   description=description,
                                   epilog=epilog)

    mgroup = parser.add_argument_group('metadata options')
    mgroup.add_argument('-v', '--version', help='Notebook version')
    mgroup.add_argument('-s', '--summary', help='Set the summary of the notebook')

    parser.add_argument(
        '-u', '--user',
        help='User account, defaults to the current user'
    )

    parser.add_argument(
        '--force',
        help="Force a notebook upload regardless of errors",
        action='store_true'
    )

    parser.add_argument(
        'notebook',
        help='Notebook to upload',
        action='store'
    )

    parser.set_defaults(main=upload)


def add_download_parser(subparsers):
    description = "Download notebooks from binstar"
    epilog = """
    Usage:
        binstar notebook download project
        binstar notebook download project:notebook
    """
    parser = subparsers.add_parser('download',
                                   formatter_class=argparse.RawDescriptionHelpFormatter,
                                   help=description,
                                   description=description,
                                   epilog=epilog)
    parser.set_defaults(main=download)


def upload(args):
    binstar = get_binstar(args)
    uploader = Uploader(binstar, args.notebook, user=args.user, summary=args.summary,
                        version=args.version)

    if os.path.exists(args.notebook):
        uploader.upload(force=args.force)
        log.info("{} has been uploaded.".format(args.notebook))
    else:
        raise errors.BinstarError("{} can't be found".format(args.notebook))
    if uploader.msg is not None:
        log.error(uploader.msg)


def download(args):
    raise errors.BinstarError("Download notebooks hasn't been implemented yet. Soon!")
