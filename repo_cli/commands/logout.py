"""
Log out from binstar
"""
from ..utils .config import get_server_api, remove_token
import logging

from .base import SubCommandBase

logger = logging.getLogger('repo_cli')


def main(args):
    aserver_api = get_server_api(args.token, args.site)
    if aserver_api.token:

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


class SubCommand(SubCommandBase):
    name = "logout"


    def main(self):
        aserver_api = get_server_api(self.args.token, self.args.site)
        if aserver_api.token:

            # Change it to name once we release the latest version of binstar server
            #     try:
            #     aserver_api.remove_authentication()
            # except errors.Unauthorized as err:
            #     logger.debug("The token that you are trying to remove may not be valid"
            #               "{}".format(err))

            remove_token(self.args)
            self.log.info("logout successful")
        else:
            self.log.info("You are not logged in")

    def add_parser(self, subparsers):
        self.subparser = subparsers.add_parser('logout', help='Log out from your Anaconda repository',
                                          description=__doc__)

        self.subparser.set_defaults(main=self.main)