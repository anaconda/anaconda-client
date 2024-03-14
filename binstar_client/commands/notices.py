"""
Anaconda channel notices utilities
"""
import argparse
import json
import logging
import pathlib
import typing

from binstar_client import errors
from binstar_client.utils import get_server_api, get_config

logger = logging.getLogger('binstar.notices')


def main(args):
    """Entry point for notices command"""
    api = get_server_api(
        token=args.token, site=args.site, config=get_config(args.site)
    )
    api.check_server()

    if args.user is None:
        args.user = api.user().get('login')

        if args.user is None:
            message: str = 'Unable to determine owner in user; please make sure you are logged in'
            logger.error(message)
            raise errors.BinstarError(message)

    if args.notices:
        api.create_notices(args.user, args.label, args.notices)

    elif args.remove:
        api.remove_notices(args.user, args.label)

    elif args.get:
        notices = api.notices(args.user, args.label)
        logger.info(json.dumps(notices, indent=2))


class NoticesAction(argparse.Action):
    """
    Used to parse the notices argument as either an JSON string or JSON file
    """

    def __call__(self, parser, namespace, values, *args, **kwargs):
        """
        We first test if ``values`` is a file and then try to parse it as JSON.
        If it isn't, we assume it's a JSON string itself and attempt to parse it.
        """
        try:
            path = pathlib.Path(values)
        except TypeError as error:
            message: str = 'Notices argument must be defined as a string'
            logger.error(message)
            raise SystemExit(1) from error

        if path.exists():
            try:
                with path.open(encoding='utf-8') as file_pointer:
                    values = file_pointer.read()
            except OSError as error:
                message: str = f'Unable to read provided JSON file: {error}'
                logger.error(message)
                raise SystemExit(1) from error

        try:
            data = json.loads(values)
        except json.JSONDecodeError as error:
            message: str = 'Unable to parse provided JSON; please make sure it is valid JSON'
            logger.error(message)
            raise SystemExit(1) from error

        setattr(namespace, self.dest, data)


def add_parser(subparsers: typing.Any) -> None:
    """
    Set options for notices subcommand
    """
    description: str = 'Create, modify and delete channels notices in your Anaconda repository'
    parser: argparse.ArgumentParser = subparsers.add_parser(
        'notices',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help=description, description=description,
        epilog=__doc__,
    )

    parser.add_argument(
        '-l', '--label',
        default='main',
        help='Label to use for channel notice'
    )

    parser.add_argument(
        '-u', '--user',
        help='User account or Organization, defaults to the current user',
    )

    agroup = parser.add_argument_group('actions')
    group = agroup.add_mutually_exclusive_group()
    group.add_argument(
        '--create',
        dest='notices',
        metavar='notices',
        action=NoticesAction,
        help='Create notices; existing notices will be replaced'
    )
    group.add_argument(
        '--remove',
        action='store_true',
        help='Remove notices'
    )
    group.add_argument(
        '--get',
        action='store_true',
        help='Display notices'
    )

    parser.set_defaults(main=main)
