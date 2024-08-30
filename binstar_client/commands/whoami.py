# pylint: disable=missing-function-docstring

"""
Print the information of the current user
"""

from __future__ import unicode_literals

import argparse
import logging

import typer

from binstar_client import errors
from binstar_client.utils import get_server_api
from binstar_client.utils.pprint import pprint_user

logger = logging.getLogger('binstar.whoami')


def mount_subcommand(app: typer.Typer, name, context_settings):
    @app.command(name=name, context_settings=context_settings)
    def whoami(ctx: typer.Context):
        ctx.params.update({**ctx.parent.params, **ctx.params})
        args = argparse.Namespace(**ctx.params)
        logger.debug(f"{args=}")
        logger.debug(f"{ctx.params=}")
        main(args)


def main(args):  # pylint: disable=inconsistent-return-statements
    aserver_api = get_server_api(args.token, args.site)

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
