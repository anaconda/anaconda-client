'''
Register a package in binstar.

This command must be run before 'binstar upload' if the package namespace does
not exist.

eg:
    binstar register CONDA_PACKAGE_1.bz2
    binstar upload CONDA_PACKAGE_1.bz2
'''
from __future__ import unicode_literals
from binstar_client.utils import get_binstar, get_config
from binstar_client import BinstarError, NotFound
from os.path import exists
import sys
import logging
from binstar_client.utils.detect import detect_package_type, get_attrs
from binstar_client.errors import UserError
import argparse

log = logging.getLogger('binstar.register')


def main(args):

    binstar = get_binstar(args)

    if args.user:
        username = args.user
    else:
        user = binstar.user()
        username = user ['login']

    if not exists(args.filename):
        raise BinstarError('file %s does not exist' % (args.filename))

    log.info('detecting package type ...')
    sys.stdout.flush()
    package_type = detect_package_type(args.filename)
    if package_type is None:
        raise UserError('Could not detect package type of file %r' % args.filename)

    log.info(package_type)

    log.info('extracting package attributes ...')
    sys.stdout.flush()
    try:
        package_attrs = get_attrs(package_type, args.filename)
    except Exception:
        if args.show_traceback:
            raise

        raise BinstarError('Trouble reading metadata from %r. Please make sure this package is correct.' % (args.filename))

    _, package_name, _, _, summary, _, license = package_attrs

    if args.summary:
        summary = args.summary

    if args.package:
        package_name = args.package

    try:
        binstar.package(username, package_name)
    except NotFound:
        binstar.add_package(username, package_name,
                            summary,
                            license,
                            public=args.access != 'private')
        log.info('Created package %s/%s' % (username, package_name))
    else:
        raise UserError('Package %s/%s already exists' % (username, package_name))


def add_parser(subparsers):

    config = get_config()

    parser = subparsers.add_parser('register',
                                      formatter_class=argparse.RawDescriptionHelpFormatter,
                                      help='Register a package on binstar',
                                      description=__doc__)

    parser.add_argument('filename', help='Inspect this file, to get the package name and summary', default=None)

    parser.add_argument('-u', '--user', help='User account, defaults to the current user')
    parser.add_argument('-p', '--package', help='Defaults to the packge name in the uploaded file')
    parser.add_argument('-s', '--summary', help='Summary of the package')

    perms = parser.add_mutually_exclusive_group()

    package_access = config.get('package_access', 'personal')
    perms.desciption = 'The package permissions'

    perms.add_argument('--private', action='store_const',
                       dest='access', const='private',
                       default=package_access == 'private',
                       help='Set the permissions of the package to private (if it does not exist)')

    perms.add_argument('--personal', action='store_const',
                       dest='access', const='personal',
                       default=package_access == 'personal',
                       help=('Set the permissions of the package to public. '
                             'Do not publish this to the global public repo. This package will be kept in you user repository.'))

    parser.set_defaults(main=main)
