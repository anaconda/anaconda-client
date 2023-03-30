# -*- coding: utf-8 -*-

"""Update public attributes of the package or the attributes of the package release."""

import typing

import argparse
import json
import logging
import os

import yaml

from binstar_client import errors
from binstar_client.utils import get_server_api
from binstar_client.utils import parse_specs
from binstar_client.utils.detect import detect_package_type, get_attrs

logger = logging.getLogger('binstar.update')


def get_attributes(
        package: str,
        package_type: typing.Any,
        args: argparse.Namespace,
) -> typing.Tuple[typing.Mapping[str, typing.Any], typing.Mapping[str, typing.Any]]:
    """Parse source for attribute details."""
    loader: typing.Optional[typing.Callable[[typing.TextIO], typing.Mapping[str, typing.Any]]] = None
    if package.endswith('.json'):
        loader = json.load
    elif package.endswith(('.yml', '.yaml')):
        loader = yaml.safe_load

    package_attrs: typing.Mapping[str, typing.Any]
    release_attrs: typing.Mapping[str, typing.Any]
    if loader is None:
        package_attrs, release_attrs, _ = get_attrs(package_type, package, parser_args=args)
    else:
        stream: typing.TextIO
        with open(package, 'rt', encoding='utf-8') as stream:
            package_attrs = release_attrs = loader(stream)

    return package_attrs, release_attrs


def main(args: argparse.Namespace) -> None:
    """Process update request."""
    anaconda_api = get_server_api(args.token, args.site)
    anaconda_api.check_server()

    package_type = detect_package_type(args.source)
    try:
        package_attrs, release_attrs = get_attributes(args.source, package_type, args)
    except Exception as error:
        message = 'Trouble reading metadata from {}. Is this a valid source file: {} ?'.format(
            args.source, package_type.label())
        logger.error(message)
        raise errors.BinstarError(message) from error

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
    logger.info('Package `%s` has been updated!', args.spec)


def file_type(path: str) -> str:
    """Validate argument value, that should be a valid path to file."""
    if os.path.isfile(path):
        return path

    raise argparse.ArgumentTypeError(f'{path} is not a valid path')


def add_parser(subparsers: typing.Any) -> None:
    """Add parser to CLI."""
    parser = subparsers.add_parser(
        'update',
        usage=(
            '\n\tanaconda update [--release] user/package[/version] CONDA_PACKAGE_1.bz2'
            '\n\tanaconda update [--release] user/package[/version] metadata.json'
        ),
        description=__doc__,
    )

    parser.add_argument(
        'spec',
        help='Package name written as `user/package[/version]`',
        type=parse_specs,
    )
    parser.add_argument(
        'source',
        help=(
            'Path to the file that consists of metadata that will be updated in the destination package. '
            'It may be a valid package file or `.json` file with described attributes to update'
        ),
        type=file_type,
    )

    release_group = parser.add_argument_group(title='Update release')
    release_group.add_argument(
        '--release',
        help='Use `source` file to update public attributes of the release specified in `spec`',
        action='store_true'
    )

    parser.set_defaults(main=main)
