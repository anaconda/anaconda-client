'''
Authenticate a user
'''
from __future__ import unicode_literals
import getpass
from binstar_client.utils import get_config, get_binstar, store_token
from binstar_client.errors import Unauthorized, BinstarError
import sys
import logging
import socket

log = logging.getLogger('binstar.login')

try:
    input = raw_input
except NameError:
    input = input

def interactive_get_token():
    bs = get_binstar()
    config = get_config()

    url = config.get('url', 'https://api.binstar.org')

    token = None
    username = input('Username: ')

    for _ in range(3):
        try:
            sys.stderr.write("%s's " % username)
            password = getpass.getpass(stream=sys.stderr)
            token = bs.authenticate(username, password, 'binstar_client:%s' % (socket.gethostname()), url,
                                    created_with=' '.join(sys.argv))
            break
        except Unauthorized:
            log.error('Invalid Username password combination, please try again')
            continue

    if token is None:
        raise BinstarError('Sorry. Please try again (go to https://binstar.org/account/forgot_password to reset your password)')

    return token

def interactive_login():
    token = interactive_get_token()
    store_token(token)
    log.info('login successful')

def main(args):
    interactive_login()

def add_parser(subparsers):
    subparser = subparsers.add_parser('login',
                                      help='Authenticate a user',
                                      description=__doc__)

    subparser.set_defaults(main=main)
