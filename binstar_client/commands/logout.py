'''
Log out from binstar
'''

import getpass
from binstar_client.utils import get_binstar, remove_token

import logging
from binstar_client import errors
log = logging.getLogger('binstar.logout')

def main(args):

    bs = get_binstar(args)
    if bs.token:
    # TODO: named 'application' because I was using the github model
    # Change it to name once we release the latest version of binstar server
        try:
            bs.remove_authentication()
        except errors.Unauthorized as err:
            log.debug("The token that you are trying to remove may not be valid"
                      "{}".format(err))
        remove_token(args)
        log.info("logout successful")
    else:
        log.info("You are not logged in")


def add_parser(subparsers):
    subparser = subparsers.add_parser('logout',
                                      help='Log out from Anaconda Cloud',
                                      description=__doc__)

    subparser.set_defaults(main=main)
