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
        help='Files to upload',
        action='append',
        default=[]
    )

    parser.set_defaults(main=main)


def main(args):
    binstar = get_binstar(args)
    if args.action == 'upload':
        finder = Finder(args.files)
        uploader = Uploader(binstar, args.project)
        scm = SCM(uploader, args.project)
        scm.local(local_files(finder.valid))
        scm.pull()

        if len(scm.diff) == 0:
            log.info("There are no files to upload")
        else:
            for scm_file in scm.diff:
                filename = scm_file.filename
                if uploader.upload(os.path.join(finder.prefix, filename), force=False):
                    log.info("{} has been uploaded.".format(filename))
        for f in finder.invalid:
            log.info("{} can't be uploaded".format(f))

    elif args.action == 'download':
        raise errors.BinstarError("Download notebooks hasn't been implemented yet. Soon!")
