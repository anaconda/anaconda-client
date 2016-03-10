"""
[Deprecation warning]
`anaconda notebook` is going to be deprecated
use `anaconda upload/download` instead
"""

from __future__ import unicode_literals
import argparse
import logging
from binstar_client import errors
from binstar_client.utils import get_server_api
from binstar_client.utils.notebook import Uploader, Downloader, parse, notebook_url, has_environment

log = logging.getLogger("binstar.notebook")


def add_parser(subparsers):
    description = 'Interact with notebooks in anaconda.org'
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
    [Deprecation warning]
    `anaconda notebook` is going to be deprecated
    use `anaconda upload` instead
    """
    parser = subparsers.add_parser('upload',
                                   formatter_class=argparse.RawDescriptionHelpFormatter,
                                   help=description,
                                   description=description,
                                   epilog=epilog)

    mgroup = parser.add_argument_group('metadata options')
    mgroup.add_argument('-n', '--name', help='Notebook\'s name (will be parameterized)')
    mgroup.add_argument('-v', '--version', help='Notebook\'s version')
    mgroup.add_argument('-s', '--summary', help='Set the summary of the notebook')
    mgroup.add_argument('-t', '--thumbnail', help='Notebook\'s thumbnail image')

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
    description = "Download notebooks from anaconda.org"
    epilog = """
    [Deprecation warning]
    `anaconda notebook` is going to be deprecated
    use `anaconda download` instead
    """
    parser = subparsers.add_parser('download',
                                   formatter_class=argparse.RawDescriptionHelpFormatter,
                                   help=description,
                                   description=description,
                                   epilog=epilog)

    parser.add_argument(
        'handle',
        help="user/notebook",
        action='store'
    )

    parser.add_argument(
        '-f', '--force',
        help='Overwrite',
        action='store_true'
    )

    parser.add_argument(
        '-o', '--output',
        help='Download as',
        default='.'
    )

    parser.set_defaults(main=download)


def upload(args):
    aserver_api = get_server_api(args.token, args.site, args.log_level)

    uploader = Uploader(aserver_api, args.notebook, user=args.user, summary=args.summary,
                        version=args.version, thumbnail=args.thumbnail, name=args.name)

    try:
        upload_info = uploader.upload(force=args.force)
        log.warn("`anaconda notebook` is going to be deprecated")
        log.warn("use `anaconda upload` instead.")
        log.info("{} has been uploaded.".format(args.notebook))
        log.info("You can visit your notebook at {}".format(notebook_url(upload_info)))
    except (errors.BinstarError, IOError) as e:
        log.error(str(e))


def download(args):
    aserver_api = get_server_api(args.token, args.site, args.log_level)

    username, notebook = parse(args.handle)
    username = username or aserver_api.user()['login']
    downloader = Downloader(aserver_api, username, notebook)
    try:
        download_info = downloader(output=args.output, force=args.force)
        log.warn("`anaconda notebook` is going to be deprecated")
        log.warn("use `anaconda download` instead.")
        log.info("{} has been downloaded as {}.".format(args.handle, download_info[0]))
        if has_environment(download_info[0]):
            log.info("{} has an environment embedded.".format(download_info[0]))
            log.info("Run:")
            log.info("    conda env create {}".format(download_info[0]))
            log.info("To install the environment in your system")
    except (errors.DestionationPathExists, errors.NotFound, OSError) as err:
        log.info(err.msg)
