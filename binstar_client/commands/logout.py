'''
Log out from binstar
'''

import getpass
from binstar_client.utils import get_binstar, remove_token

import logging
log = logging.getLogger('binstar.logout')

def main(args):

    bs = get_binstar()
    auth = bs.authentication()
    bs.remove_authentication(auth['id'])
    remove_token()
    log.info("logout successful")

def add_parser(subparsers):
    subparser = subparsers.add_parser('logout',
                                      help='Log out from binstar',
                                      description=__doc__)

    subparser.set_defaults(main=main)
