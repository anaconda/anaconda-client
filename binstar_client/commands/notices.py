"""
Anaconda channel notices utilities
"""
import argparse
import json
import logging
import typing

from binstar_client.errors import UserError
from binstar_client.utils import get_server_api

logger = logging.getLogger('binstar.notices')


def main(args):
    """Entry point for notices command"""
    aserver_api = get_server_api(args.token, args.site)
    aserver_api.check_server()
    login = aserver_api.user().get('login')

    if login is None:
        raise UserError("Unable to determine logged in user; please make sure you are logged in")

    if args.notices:
        try:
            data = json.loads(args.notices)
        except json.JSONDecoder:
            raise UserError("Unable to parse JSON; please make sure it is valid JSON")

        aserver_api.create_notices(login, args.label, data)

    elif args.remove:
        aserver_api.remove_notices(login, args.label)

    elif args.get:
        notices = aserver_api.notices(login, args.label)
        logger.info(json.dumps(notices, indent=2))


def add_parser(subparsers: typing.Any) -> None:
    """
    Set options for notices subcommand
    """
    description: str = 'Create, modify and delete channels notices in your Anaconda repository'
    parser: argparse.ArgumentParser = subparsers.add_parser(
        "notices",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help=description, description=description,
        epilog=__doc__,
    )

    parser.add_argument(
        '-l', '--label',
        default='main',
        help='Label to use for channel notice'
    )

    agroup = parser.add_argument_group('actions')
    group = agroup.add_mutually_exclusive_group()
    group.add_argument(
        '--create',
        dest='notices',
        metavar='notices',
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
