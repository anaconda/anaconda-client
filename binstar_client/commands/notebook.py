# pylint: disable=missing-function-docstring

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
from binstar_client.utils.notebook import parse, notebook_url, has_environment
from binstar_client.utils.notebook.uploader import Uploader
from binstar_client.utils.notebook.downloader import Downloader

logger = logging.getLogger('binstar.notebook')


def add_parser(subparsers):
    description = 'Interact with notebooks in your Anaconda repository'
    parser = subparsers.add_parser('notebook',
                                   formatter_class=argparse.RawDescriptionHelpFormatter,
                                   help=description,
                                   description=description,
                                   epilog=__doc__)

    nb_subparsers = parser.add_subparsers()
    add_upload_parser(nb_subparsers)
    add_download_parser(nb_subparsers)


def add_upload_parser(subparsers):
    description = 'Upload a notebook to your Anaconda repository'
    epilog = '''
    [Deprecation warning]
    `anaconda notebook` is going to be deprecated
    use `anaconda upload` instead
    '''
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
        help='Force a notebook upload regardless of errors',
        action='store_true'
    )

    parser.add_argument(
        'notebook',
        help='Notebook to upload',
        action='store'
    )

    parser.set_defaults(main=upload)


def add_download_parser(subparsers):
    description = 'Download notebooks from your Anaconda repository'
    epilog = '''
    [Deprecation warning]
    `anaconda notebook` is going to be deprecated
    use `anaconda download` instead
    '''
    parser = subparsers.add_parser('download',
                                   formatter_class=argparse.RawDescriptionHelpFormatter,
                                   help=description,
                                   description=description,
                                   epilog=epilog)

    parser.add_argument(
        'handle',
        help='user/notebook',
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
    aserver_api = get_server_api(args.token, args.site)

    uploader = Uploader(aserver_api, args.notebook, user=args.user, summary=args.summary,
                        version=args.version, thumbnail=args.thumbnail, name=args.name)

    try:
        upload_info = uploader.upload(force=args.force)
        logger.warning('`anaconda notebook` is going to be deprecated')
        logger.warning('use `anaconda upload` instead.')
        logger.info('%s has been uploaded.', args.notebook)
        logger.info('You can visit your notebook at %s', notebook_url(upload_info))
    except (errors.BinstarError, IOError) as error:
        logger.error(error)


def download(args):
    aserver_api = get_server_api(token=args.token, site=args.site)

    username, notebook = parse(args.handle)
    username = username or aserver_api.user()['login']
    downloader = Downloader(aserver_api, username, notebook)
    try:
        download_info = downloader(output=args.output, force=args.force)
        logger.warning('`anaconda notebook` is going to be deprecated')
        logger.warning('use `anaconda download` instead.')
        logger.info('%s has been downloaded as %s.', args.handle, download_info[0])
        if has_environment(download_info[0]):
            logger.info('%s has an environment embedded.', download_info[0])
            logger.info('Run:')
            logger.info('    conda env create %s', download_info[0])
            logger.info('To install the environment in your system')
    except (errors.DestinationPathExists, errors.NotFound, OSError) as err:
        logger.info(err.msg)
