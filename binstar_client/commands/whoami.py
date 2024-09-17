# pylint: disable=missing-function-docstring

"""
Print the information of the current user
"""

from __future__ import unicode_literals

import argparse
import logging
from typing import Optional

import typer

from binstar_client import errors
from binstar_client.utils import get_server_api
from binstar_client.utils.pprint import pprint_user

logger = logging.getLogger('binstar.whoami')


def main(
    args: Optional[argparse.Namespace] = None,
    *,
    token: Optional[str] = None,
    site: Optional[str] = None,
):  # pylint: disable=inconsistent-return-statements
    if args is not None:
        token = args.token
        site = args.site

    aserver_api = get_server_api(token, site)

    try:
        user = aserver_api.user()
    except errors.Unauthorized as err:
        logger.debug(err)
        logger.info('Anonymous User')
        return 1

    pprint_user(user)


def add_parser(subparsers):
    subparser = subparsers.add_parser('whoami',
                                      help='Print the information of the current user',
                                      description=__doc__)

    subparser.set_defaults(main=main)


def mount_subcommand(app: typer.Typer, name, hidden: bool, help_text: str, context_settings: dict):
    @app.command(
        name=name,
        hidden=hidden,
        help=help_text,
        context_settings=context_settings,
    )
    def whoami(ctx: typer.Context):
        main(token=ctx.obj.params.get("token"), site=ctx.obj.params.get("site"))
