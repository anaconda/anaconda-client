'''
Authenticate a user
'''
from __future__ import unicode_literals

import getpass
import logging
import socket
import sys

from binstar_client import errors
from binstar_client.utils import get_config, get_binstar, store_token, \
    bool_input


log = logging.getLogger('binstar.login')

try:
    input = raw_input
except NameError:
    input = input

def interactive_get_token(args):
    bs = get_binstar(args)
    config = get_config(remote_site=args.site)

    url = config.get('url', 'https://api.binstar.org')

    token = None
    username = input('Username: ')

    auth_name = 'binstar_client:%s' % (socket.gethostname())
    password = None
    for _ in range(3):
        try:
            sys.stderr.write("%s's " % username)

            if password is None:
                password = getpass.getpass(stream=sys.stderr)

            token = bs.authenticate(username, password, auth_name, url,
                                    created_with=' '.join(sys.argv),
                                    fail_if_already_exists=True)
            break

        except errors.Unauthorized:
            log.error('Invalid Username password combination, please try again')
            password = None
            continue

        except errors.BinstarError as err:
            if err.args[1] == 400:
                log.error('It appears you are already logged in from host %s' % socket.gethostname())
                log.error('Logging in again will remove the previous token.')
                if bool_input("Would you like to continue"):
                    bs.remove_authentication(auth_name)
                    continue
                else:
                    raise


    if token is None:
        msg = ('Sorry. Please try again '
               '(go to https://binstar.org/account/forgot_password '
               'to reset your password)')
        raise errors.BinstarError(msg)

    return token

def interactive_login(args):
    token = interactive_get_token(args)
    store_token(token, args)
    log.info('login successful')

def main(args):
    interactive_login(args)

def add_parser(subparsers):
    subparser = subparsers.add_parser('login',
                                      help='Authenticate a user',
                                      description=__doc__)

    subparser.set_defaults(main=main)
