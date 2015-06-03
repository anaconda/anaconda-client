'''

    binstar upload CONDA_PACKAGE_1.bz2

##### See Also

  * [Uploading a Conda Package](http://docs.anaconda.org/examples.html#UploadingACondaPackage)
  * [Uploading a PyPI Package](http://docs.anaconda.org/examples.html#UploadingAPypiPackage)

'''
from __future__ import unicode_literals

import argparse
from glob import glob
import logging
import os
from os.path import exists
import sys

from binstar_client import errors
from binstar_client.utils import get_binstar, bool_input, upload_print_callback
from binstar_client.utils.detect import detect_package_type, get_attrs


# Python 3 Support
try:
    input = raw_input
except NameError:
    input = input


log = logging.getLogger('binstar.upload')


def create_release(binstar, username, package_name, version, description, announce=None):
    binstar.add_release(username, package_name, version, [],
                        announce, description)

def create_release_interactive(binstar, username, package_name, version):

    log.info('\nThe release %s/%s/%s does not exist' % (username, package_name, version))
    if not bool_input('Would you like to create it now?'):
        log.info('good-bye')
        raise SystemExit(-1)

    description = input('Enter a short description of the release:\n')
    log.info("\nAnnouncements are emailed to your package followers.")
    make_announcement = bool_input('Would you like to make an announcement to the package followers?', False)
    if make_announcement:
        announce = input('Markdown Announcement:\n')
    else:
        announce = ''

    binstar.add_release(username, package_name, version, [],
                        announce, description)

def determine_package_type(filename, args):
    """
    return the file type from the inspected package or from the
    -t/--package-type argument
    """
    if args.package_type:
        package_type = args.package_type
    else:
        log.info('detecting package type ...')
        sys.stdout.flush()
        package_type = detect_package_type(filename)
        if package_type is None:
            raise errors.BinstarError('Could not detect package type of file %r please specify package type with option --package-type' % filename)
        log.info(package_type)

    return package_type

def get_package_name(args, package_attrs, filename, package_type):
    if args.package:
        if 'name' in package_attrs and package_attrs['name'].lower() != args.package.lower():
            msg = 'Package name on the command line " %s" does not match the package name in the file "%s"'
            raise errors.BinstarError(msg % (args.package.lower(), package_attrs['name'].lower()))
        package_name = args.package
    else:
        if 'name' not in package_attrs:
            raise errors.BinstarError("Could not detect package name for package type %s, please use the --package option" % (package_type,))
        package_name = package_attrs['name']

    return package_name


def get_version(args, release_attrs, package_type):
    if args.version:
        version = args.version
    else:
        if 'version' not in release_attrs:
            raise errors.BinstarError("Could not detect package version for package type %s, please use the --version option" % (package_type,))
        version = release_attrs['version']
    return version

def add_package(binstar, args, username, package_name, package_attrs, package_type):
    try:
        binstar.package(username, package_name)
    except errors.NotFound:
        if args.no_register:
            raise errors.UserError('Binstar package %s/%s does not exist. '
                            'Please run "binstar package --create" to create this package namespace in the cloud.' % (username, package_name))
        else:

            if args.summary:
                summary = args.summary
            else:
                if 'summary' not in package_attrs:
                    raise errors.BinstarError("Could not detect package summary for package type %s, please use the --summary option" % (package_type,))
                summary = package_attrs['summary']

            binstar.add_package(username, package_name, summary, package_attrs.get('license'),
                                public=True)


def add_release(binstar, args, username, package_name, version, release_attrs):
    try:
        binstar.release(username, package_name, version)
    except errors.NotFound:
        if args.mode == 'interactive':
            create_release_interactive(binstar, username, package_name, version)
        else:
            create_release(binstar, username, package_name, version, release_attrs['description'])


def remove_existing_file(binstar, args, username, package_name, version, file_attrs):
    try:
        binstar.distribution(username, package_name, version, file_attrs['basename'])
    except errors.NotFound:
        return False
    else:
        if args.mode == 'force':
            log.warning('Distribution %s already exists ... removing' % (file_attrs['basename'],))
            binstar.remove_dist(username, package_name, version, file_attrs['basename'])
        if args.mode == 'interactive':
            if bool_input('Distribution %s already exists. Would you like to replace it?' % (file_attrs['basename'],)):
                binstar.remove_dist(username, package_name, version, file_attrs['basename'])
            else:
                log.info('Not replacing distribution %s' % (file_attrs['basename'],))
                return True


def main(args):

    binstar = get_binstar(args)

    if args.user:
        username = args.user
    else:
        user = binstar.user()
        username = user ['login']

    uploaded_packages = []

    # Flatten file list because of 'windows_glob' function
    files = [f for fglob in args.files for f in fglob]

    for filename in files:

        if not exists(filename):
            raise errors.BinstarError('file %s does not exist' % (filename))

        package_type = determine_package_type(filename, args)

        log.info('extracting package attributes for upload ...')
        sys.stdout.flush()
        try:
            package_attrs, release_attrs, file_attrs = get_attrs(package_type, filename)
        except Exception:
            if args.show_traceback:
                raise
            raise errors.BinstarError('Trouble reading metadata from %r. Is this a valid %s package' % (filename, package_type))

        if args.build_id:
            file_attrs['attrs']['binstar_build'] = args.build_id


        log.info('done')

        package_name = get_package_name(args, package_attrs, filename, package_type)
        version = get_version(args, release_attrs, package_type)


        add_package(binstar, args, username, package_name, package_attrs, package_type)

        add_release(binstar, args, username, package_name, version, release_attrs)

        binstar_package_type = file_attrs.pop('binstar_package_type', package_type)

        with open(filename, 'rb') as fd:
            log.info('\nUploading file %s/%s/%s/%s ... ' % (username, package_name, version, file_attrs['basename']))
            sys.stdout.flush()

            if remove_existing_file(binstar, args, username, package_name, version, file_attrs):
                continue
            try:
                upload_info = binstar.upload(username, package_name, version, file_attrs['basename'],
                                             fd, binstar_package_type,
                                             args.description,
                                             dependencies=file_attrs.get('dependencies'),
                                             attrs=file_attrs['attrs'],
                                             channels=args.channels,
                                             callback=upload_print_callback(args))
            except errors.Conflict:
                full_name = '%s/%s/%s/%s' % (username, package_name, version, file_attrs['basename'])
                log.info('Distribution already exists. Please use the -i/--interactive or --force options or `binstar remove %s`' % full_name)
                raise

            uploaded_packages.append([package_name, upload_info])
            log.info("\n\nUpload(s) Complete\n")


    for package, upload_info in uploaded_packages:
        package_url = upload_info.get('url', 'https://anaconda.org/%s/%s' % (username, package))
        log.info("Package located at:\n%s\n" % package_url)


def windows_glob(item):
    if os.name == 'nt' and '*' in item:
        return glob(item)
    else:
        return [item]

def add_parser(subparsers):

    description = 'Upload packages to binstar'
    parser = subparsers.add_parser('upload',
                                   formatter_class=argparse.RawDescriptionHelpFormatter,
                                   help=description, description=description,
                                   epilog=__doc__)

    parser.add_argument('files', nargs='+', help='Distributions to upload', default=[], type=windows_glob)

    parser.add_argument('-c', '--channel', action='append', default=[], dest='channels',
                        help='Add this file to a specific channel. Warning: if the file Channels do not include "main", the file will not show up in your user channel')
    parser.add_argument('--no-progress', help="Don't show upload progress", action='store_true')
    parser.add_argument('-u', '--user', help='User account, defaults to the current user')

    mgroup = parser.add_argument_group('metadata options')
    mgroup.add_argument('-p', '--package', help='Defaults to the package name in the uploaded file')
    mgroup.add_argument('-v', '--version', help='Defaults to the package version in the uploaded file')
    mgroup.add_argument('-s', '--summary', help='Set the summary of the package')
    mgroup.add_argument('-t', '--package-type', help='Set the package type, defaults to autodetect')
    mgroup.add_argument('-d', '--description', help='description of the file(s)')

    parser.add_argument("--no-register", action="store_true", default=False,
                        help='Don\'t create a new package namespace if it does not exist')
    parser.add_argument('--build-id', help='Binstar-Build ID (internal only)')

    group = parser.add_mutually_exclusive_group()
    group.add_argument('-i', '--interactive', action='store_const', help='Run an interactive prompt if any packages are missing',
                        dest='mode', const='interactive')
    group.add_argument('-f', '--fail', help='Fail if a package or release does not exist (default)',
                                        action='store_const', dest='mode', const='fail')
    group.add_argument('--force', help='Force a package upload regardless of errors',
                                        action='store_const', dest='mode', const='force')

    parser.set_defaults(main=main)
