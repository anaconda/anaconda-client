"""
Update public attributes of the package or the attributes of the package release
"""
import json
from binstar_client.utils import parse_specs

import argparse
import logging
import os

from binstar_client import errors
from binstar_client.utils import get_server_api
from binstar_client.utils.detect import detect_package_type, get_attrs

logger = logging.getLogger('binstar.update')


def get_attributes(package, package_type, args):
    if package.endswith('.json'):
        with open(package, 'r') as f:
            attrs = json.load(f)
            return attrs, attrs

    package_attrs, release_attrs, file_attrs = get_attrs(package_type, package, parser_args=args)
    return package_attrs, release_attrs


def main(args):
    anaconda_api = get_server_api(args.token, args.site)
    anaconda_api.check_server()

    package_type = detect_package_type(args.source)
    try:
        package_attrs, release_attrs = get_attributes(args.source, package_type, args)
    except Exception:
        message = 'Trouble reading metadata from {}. Is this a valid source file: {} ?'.format(
            args.source, package_type.label())
        logger.error(message)
        raise errors.BinstarError(message)

    attrs = package_attrs if not args.release else release_attrs
    attrs = attrs.get('public_attrs', attrs)

    if args.release:
        anaconda_api.update_release(
            args.spec.user,
            args.spec.package,
            args.spec.version,
            attrs,
        )
    else:
        anaconda_api.update_package(
            args.spec.user,
            args.spec.package,
            attrs,
        )
    logger.info("Package `{}` has been updated!".format(args.spec))


def file_type(path):
    if os.path.isfile(path):
        return path

    raise argparse.ArgumentTypeError("{} is not a valid path".format(path))


def add_parser(subparsers):
    parser = subparsers.add_parser(
        'update',
        usage="\n\tanaconda update user/package[/version] CONDA_PACKAGE_1.bz2"
              "\n\tanaconda update user/package[/version] metadata.json",
        description=__doc__)

    package_help = ('Path to the file that consists of metadata that will be updated in the destination package. '
                    'It may be a valid package file or `.json` file with described attributes to update')

    parser.add_argument('spec', help='Package name written as `user/package[/version]`', type=parse_specs)
    parser.add_argument('source', help=package_help, type=file_type)
    release_group = parser.add_argument_group(title='Update release')
    release_group.add_argument(
        '--release',
        help='Use `source` file to update public attributes of the release specified in `spec`',
        action='store_true'
    )

    parser.set_defaults(main=main)
