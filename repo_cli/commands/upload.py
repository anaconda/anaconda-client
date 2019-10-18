"""

    anaconda upload CONDA_PACKAGE_1.bz2

##### See Also

  * [Uploading a Conda Package](http://docs.anaconda.org/using.html#Uploading)
  * [Uploading a PyPI Package](http://docs.anaconda.org/using.html#UploadingPypiPackages)

"""
from __future__ import unicode_literals

import argparse
import tempfile
import logging
import subprocess

from glob import glob

from six.moves import input

from ..utils.config import get_config, PACKAGE_TYPES, DEFAULT_CONFIG, DEFAULT_URL
from ..utils.detect import detect_package_type, get_attrs
from .. import errors

logger = logging.getLogger('repo_cli')


def verbose_package_type(pkg_type, lowercase=True):
    verbose_type = PACKAGE_TYPES.get(pkg_type, 'unknown')
    if lowercase:
        verbose_type = verbose_type.lower()
    return verbose_type


def determine_package_type(filename, args):
    """
    return the file type from the inspected package or from the
    -t/--package-type argument
    """
    if args.package_type:
        package_type = args.package_type
    else:
        logger.info('Detecting file type...')

        package_type = detect_package_type(filename)

        if package_type is None:
            message = 'Could not detect package type of file %r please specify package type with option --package-type' % filename
            logger.error(message)
            raise errors.RepoCLIError(message)

        logger.info('File type is "%s"', package_type)

    return package_type


import requests
import os
from os.path import join, basename


def upload_file(base_url, token, filepath, channel):
    url = join(base_url, 'channels', channel, 'artifacts')
    statinfo = os.stat(filepath)
    filename = basename(filepath)
    logger.debug(f'[UPLOAD] Using token {token} on {base_url}')
    multipart_form_data = {
        'content': (filename, open(filepath, 'rb')),
        'filetype': (None, 'conda1'),
        'size': (None, statinfo.st_size)
    }
    logger.info(f'uploading to {url}')
    # user_token, jwt = token['user'], token['jwt']
    response = requests.post(url, files=multipart_form_data, headers={ 'X-Auth': f'{token}'})
    # response = requests.post(url, files=multipart_form_data, headers={ 'Authorization': f'Bearer {jwt}'})
    return response


def main(args):
    config = get_config(site=args.site)
    url = config.get('url', DEFAULT_URL)
    try:
        token = args.token
    except AttributeError:
        raise errors.Unauthorized

    if not token:
        raise errors.Unauthorized

    for filepath in args.files:
        for fp in filepath:
            for channel in args.labels:
                logger.debug(f'Using token {token}')
                resp = upload_file(url, token, fp, channel)
                if resp.status_code in [201, 200]:
                    logger.info(f'File {fp} successfully uploaded to {url}::{channel} with response {resp.status_code}')
                    logger.debug(f'Server responded with {resp.content}')
                else:
                    msg = f'Error uploading {fp} to {url}::{channel}. ' \
                        f'Server responded with status code {resp.status_code}.\n' \
                        f'Error details: {resp.content}'
                    logger.error(msg)


def windows_glob(item):
    if os.name == 'nt' and '*' in item:
        return glob(item)
    else:
        return [item]


def add_parser(subparsers):
    description = 'Upload packages to your Anaconda repository'
    parser = subparsers.add_parser('upload',
                                   formatter_class=argparse.RawDescriptionHelpFormatter,
                                   help=description, description=description,
                                   epilog=__doc__)

    parser.add_argument('files', nargs='+', help='Distributions to upload', default=[], type=windows_glob)

    label_help = (
        '{deprecation}Add this file to a specific {label}. '
        'Warning: if the file {label}s do not include "main", '
        'the file will not show up in your user {label}')

    parser.add_argument('-c', '--channel', action='append', default=[], dest='labels',
                        help=label_help.format(deprecation='[DEPRECATED]\n', label='channel'),
                        metavar='CHANNELS')
    parser.add_argument('-l', '--label', action='append', dest='labels',
                        help=label_help.format(deprecation='', label='label'))
    parser.add_argument('--no-progress', help="Don't show upload progress", action='store_true')
    parser.add_argument('-u', '--user', help='User account or Organization, defaults to the current user')
    parser.add_argument('--all', help='Use conda convert to generate packages for all platforms and upload them',
                        action='store_true')

    mgroup = parser.add_argument_group('metadata options')
    mgroup.add_argument('-p', '--package', help='Defaults to the package name in the uploaded file')
    mgroup.add_argument('-v', '--version', help='Defaults to the package version in the uploaded file')
    mgroup.add_argument('-s', '--summary', help='Set the summary of the package')
    # To preserve current behavior
    pkgs = PACKAGE_TYPES.copy()
    pkgs.pop('conda')
    pkgs.pop('pypi')
    pkg_types = ', '.join(list(pkgs.keys()))
    mgroup.add_argument('-t', '--package-type', help='Set the package type [{0}]. Defaults to autodetect'.format(pkg_types))
    mgroup.add_argument('-d', '--description', help='description of the file(s)')
    mgroup.add_argument('--thumbnail', help='Notebook\'s thumbnail image')
    mgroup.add_argument('--private', help="Create the package with private access", action='store_true')

    register_group = parser.add_mutually_exclusive_group()
    register_group.add_argument("--no-register", dest="auto_register", action="store_false",
                        help='Don\'t create a new package namespace if it does not exist')
    register_group.add_argument("--register", dest="auto_register", action="store_true",
                        help='Create a new package namespace if it does not exist')
    parser.set_defaults(auto_register=DEFAULT_CONFIG.get('auto_register', True))
    parser.add_argument('--build-id', help='Anaconda repository Build ID (internal only)')

    group = parser.add_mutually_exclusive_group()
    group.add_argument('-i', '--interactive', action='store_const', help='Run an interactive prompt if any packages are missing',
                        dest='mode', const='interactive')
    group.add_argument('-f', '--fail', help='Fail if a package or release does not exist (default)',
                                        action='store_const', dest='mode', const='fail')
    group.add_argument('--force', help='Force a package upload regardless of errors',
                                        action='store_const', dest='mode', const='force')
    group.add_argument('--skip-existing', help='Skip errors on package batch upload if it already exists',
                                        action='store_const', dest='mode', const='skip')

    parser.set_defaults(main=main)
