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
import platform


log = logging.getLogger('binstar.login')

try:
    input = raw_input
except NameError:
    input = input

def interactive_get_token(args, fail_if_already_exists=True):
    bs = get_binstar(args)
    config = get_config(remote_site=args.site)

    url = config.get('url', 'https://api.anaconda.org')

    token = None
    hostname = getattr(args, 'hostname', platform.node())
    if getattr(args, 'login_username', None):
        username = args.login_username
    else:
        username = input('Username: ')

    auth_name = 'binstar_client:'
    site = args.site or config.get('default_site')
    if site and site != 'binstar':
        # For testing with binstar alpha site
        auth_name += '%s:' % site

    auth_name += '%s@%s' % (getpass.getuser(), hostname)

    password = getattr(args, 'login_password', None)

    for _ in range(3):
        try:
            sys.stderr.write("%s's " % username)

            if password is None:
                password = getpass.getpass(stream=sys.stderr)

            token = bs.authenticate(username, password, auth_name, url,
                                    created_with=' '.join(sys.argv),
                                    fail_if_already_exists=fail_if_already_exists,
                                    hostname=hostname)
            break

        except errors.Unauthorized:
            log.error('Invalid Username password combination, please try again')
            password = None
            continue

        except errors.BinstarError as err:
            if fail_if_already_exists is True and err.args[1] == 400:
                log.error('It appears you are already logged in from host %s' % socket.gethostname())
                log.error('Logging in again will remove the previous token.')
                log.error('Otherwise you can login again and specify a '
                          'different hostname with "--hostname"')
                if bool_input("Would you like to continue"):
                    fail_if_already_exists = False
                    continue
                else:
                    raise


    if token is None:
        msg = ('Sorry. Please try again '
               '(go to https://anaconda.org/account/forgot_password '
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
    subparser.add_argument('--hostname', default=platform.node(),
                           help="Specify the host name of this login, "
                                "this should be unique (default: %(default)s)"
                           )
    subparser.add_argument('--username',
                           dest='login_username',
                           help="Specify your username. "
                                "If this is not given, you will be prompted"
                           )
    subparser.add_argument('--password',
                           dest='login_password',
                           help="Specify your password. "
                                "If this is not given, you will be prompted"
                           )
    subparser.set_defaults(main=main)
