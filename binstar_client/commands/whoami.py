'''
Print the information of the current user
'''
from __future__ import unicode_literals
from binstar_client import errors
from binstar_client.utils import get_binstar
from binstar_client.utils.pprint import pprint_user
import logging

log = logging.getLogger('binstar.whoami')

def main(args):
    binstar = get_binstar(args)

    try:
        user = binstar.user()
    except errors.Unauthorized:
        log.info('Anonymous User')
        return 1

    pprint_user(user)


def add_parser(subparsers):
    subparser = subparsers.add_parser('whoami',
                                      help='Print the information of the current user',
                                      description=__doc__)

    subparser.set_defaults(main=main)
