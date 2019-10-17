"""
Authenticate a user
"""
from __future__ import unicode_literals
import json
import getpass
import datetime
from os.path import join
import logging
import platform
import socket
import sys
import requests
from six.moves import input

from binstar_client import errors
from binstar_client.utils import bool_input
from ..utils.config import store_token, get_config, load_token, DEFAULT_URL
from .. import errors


logger = logging.getLogger('binstar.login')


def try_replace_token(authenticate, **kwargs):
    """
    Authenticates using the given *authenticate*, retrying if the token needs
    to be replaced.
    """

    try:
        return authenticate(**kwargs)
    except errors.BinstarError as err:
        if kwargs.get('fail_if_already_exists') and len(err.args) > 1 and err.args[1] == 400:
            logger.warning('It appears you are already logged in from host %s' % socket.gethostname())
            logger.warning('Logging in again will remove the previous token. (This could cause troubles with virtual '
                           'machines with the same hostname)')
            logger.warning('Otherwise you can login again and specify a different hostname with "--hostname"')

            if bool_input("Would you like to continue"):
                kwargs['fail_if_already_exists'] = False
                return authenticate(**kwargs)

        raise


def create_access_token(jwt_token, token_url):
    # TODO: Should we remove expires_at and let the server pick the default?
    
    data = {
            'name': 'repo-cli-token',
            'expires_at': str(datetime.datetime.now().date() + datetime.timedelta(days=30)),
            'permissions': {'scopes':[
                {'resource_type': 'channel', 'permission': 'manage'}, {'resource_type': 'artifact', 'permission': 'manage'}]}
    }
    resp = requests.post(token_url, data=json.dumps(data), headers={
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {jwt_token}'
    })
    if resp.status_code != 200:
        msg = 'Error requesting a new user token! Server responded with %s: %s' % (resp.status_code, resp.content)
        logger.error(msg)
        raise errors.RepoCLIError(msg)

    return resp.json()['token']


def get_access_token(jwt_token, token_url):
    token_resp = requests.get(token_url, headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {jwt_token}'})
    if token_resp.status_code != 200:
        msg = 'Error retrieving user token! Server responded with %s: %s' % (token_resp.status_code, token_resp.content)
        logger.error(msg)
        raise errors.RepoCLIError(msg)
    
    user_tokens = token_resp.json().get('items', [])
    if user_tokens:
        # ok, we got the token. Now we need to refresh it
        token_to_refresh = user_tokens[0]['id']
        refresh_url = join(token_url, token_to_refresh)
        logger.debug('[ACCESS_TOKEN] Refreshing token.. {token_to_refresh}')
        token_resp = requests.put(refresh_url, headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {jwt_token}'})
        if token_resp.status_code != 200:
            msg = 'Error refreshing user token! Server responded with %s: %s' % (token_resp.status_code, token_resp.content)
            logger.error(msg)
            raise errors.RepoCLIError(msg)
        new_token = token_resp.json()['token']
        logger.debug('[ACCESS_TOKEN] Refreshed with token..{}')
        return new_token

    return None


def login_user(username='john', password='password', base_url='http://conda.rocks') -> requests.Response:
    """Login  and returns the token."""
    data = {
        'username': username,
        'password': password
    }
    s = requests.Session()
    url = join(base_url, 'auth', 'login')
    token_url = join(base_url, 'account', 'tokens')
    resp = s.post(url, data=json.dumps(data), headers={
        'Content-Type': 'application/json'
    })

    jwt_token = resp.json()['token']
    user_token = get_access_token(jwt_token, token_url)

    if not user_token:
        # Looks like user doesn't have any valid token. Let's create a new one
        user_token = create_access_token(jwt_token, token_url)
        # user_token = get_access_tokens(jwt_token, token_url)
        if resp.status_code != 200:
            msg = 'Unable to request user tokens. Server was unable to return any valid token!'
            logger.error(msg)
            raise errors.RepoCLIError(msg)
    
    # TODO: we are assuming the first token is the one we need... We need to improve this waaaaay more
    return {"user": user_token, "jwt": jwt_token}


def interactive_get_token(args, fail_if_already_exists=True):
    # bs = get_server_api(args.token, args.site)
    config = get_config(site=args.site)

    token = None
    # This function could be called from a totally different CLI, so we don't
    # know if the attribute hostname exists.
    # args.site or config.get('default_site')
    url = config.get('url', DEFAULT_URL)
    if getattr(args, 'login_username', None):
        username = args.login_username
    else:
        username = input('Username: ')
    #
    password = getattr(args, 'login_password', None)

    for _ in range(3):
        try:
            if password is None:
                password = getpass.getpass(stream=sys.stderr)

            token = login_user(username, password, url)
            if not token:
                msg = 'Unable to request the user token. Server was unable to return any valid token!'
                logger.error(msg)
                raise errors.RepoCLIError(msg)
            return token['user']

        except errors.Unauthorized:
            logger.error('Invalid Username password combination, please try again')
            password = None
            continue

    return token['user']


def interactive_login(args):
    token = interactive_get_token(args)
    # import pdb; pdb.set_trace()
    store_token(token, args)
    logger.info('login successful')
    return token#['id']


def main(args):
    interactive_login(args)


def add_parser(subparsers):
    subparser = subparsers.add_parser('login', help='Authenticate a user', description=__doc__)
    subparser.add_argument('--hostname', default=platform.node(),
                           help="Specify the host name of this login, this should be unique (default: %(default)s)")
    subparser.add_argument('--username', dest='login_username',
                           help="Specify your username. If this is not given, you will be prompted")
    subparser.add_argument('--password', dest='login_password',
                           help="Specify your password. If this is not given, you will be prompted")
    subparser.set_defaults(main=main)
