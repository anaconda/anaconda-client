"""
Log out from binstar
"""
from ..utils .config import get_server_api, remove_token

import logging
from .. import errors

logger = logging.getLogger('repo_cli')


def main(args):

    aserver_api = get_server_api(args.token, args.site)
    if aserver_api.token:
    # TODO: named 'application' because I was using the github model
    # Change it to name once we release the latest version of binstar server
    #     try:
        #     aserver_api.remove_authentication()
        # except errors.Unauthorized as err:
        #     logger.debug("The token that you are trying to remove may not be valid"
        #               "{}".format(err))

        remove_token(args)
        logger.info("logout successful")
    else:
        logger.info("You are not logged in")


def add_parser(subparsers):
    subparser = subparsers.add_parser('logout',
                                      help='Log out from your Anaconda repository',
                                      description=__doc__)

    subparser.set_defaults(main=main)
