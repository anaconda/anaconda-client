'''
Print the information of the current user
'''
from __future__ import unicode_literals
from binstar_client import errors
from binstar_client.utils import get_server_api
from binstar_client.utils.pprint import pprint_user
import logging

log = logging.getLogger('binstar.whoami')

def main(args):
    aserver_api = get_server_api(args.token, args.site, args.log_level)

    try:
        user = aserver_api.user()
    except errors.Unauthorized as err:
        log.debug(err)
        log.info('Anonymous User')
        return 1

    pprint_user(user)


def add_parser(subparsers):
    subparser = subparsers.add_parser('whoami',
                                      help='Print the information of the current user',
                                      description=__doc__)

    subparser.set_defaults(main=main)
