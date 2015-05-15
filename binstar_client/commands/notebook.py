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
from binstar_client.utils.notebook import Finder, Uploader, Downloader, SCM, local_files, parse

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
    description = "Upload notebooks to binstar"
    epilog = """
    Usage:
        binstar notebook upload project notebook.ipynb
        binstar notebook upload project directory
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

    parser.set_defaults(main=upload)


def add_download_parser(subparsers):
    description = "Download notebooks from binstar"
    epilog = """
    Usage:
        binstar notebook download project
        binstar notebook download user/project
        binstar notebook download user/project:notebook
    """
    parser = subparsers.add_parser('download',
                                   formatter_class=argparse.RawDescriptionHelpFormatter,
                                   help=description,
                                   description=description,
                                   epilog=epilog)

    parser.add_argument(
        'handle',
        help="user/project:notebook",
        action='store'
    )

    parser.add_argument(
        '-f', '--force',
        help='Overwrite',
        action='store_true'
    )

    parser.add_argument(
        '-o', '--output',
        help='Download as'
    )

    parser.set_defaults(main=download)


def upload(args):
    binstar = get_binstar(args)
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


def download(args):
    binstar = get_binstar(args)
    username, project, notebook = parse(args.handle)
    username = username or binstar.user()['login']
    downloader = Downloader(binstar, username, project, notebook)
    try:
        downloader.call(output=args.output, force=args.force)
        log.info("{} has been downloaded.".format(args.handle))
    except (errors.NotFound, OSError) as err:
        log.info(err.msg)
