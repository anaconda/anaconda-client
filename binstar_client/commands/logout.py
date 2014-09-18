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
        bs.remove_authentication()
        remove_token(args)
        log.info("logout successful")
    else:
        log.info("You are not logged in")


def add_parser(subparsers):
    subparser = subparsers.add_parser('logout',
                                      help='Log out from binstar',
                                      description=__doc__)

    subparser.set_defaults(main=main)
