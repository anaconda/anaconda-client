"""
Authenticate a user
"""
from __future__ import unicode_literals
import json
import getpass
from os.path import join
import logging
import platform
import sys
import requests
from six.moves import input

from ..utils.config import store_token, get_config, DEFAULT_URL
from .. import errors
from ..utils.api import RepoApi
from .base import SubCommandBase

logger = logging.getLogger('repo_cli')


def login_user(username='john', password='password', base_url='http://conda.rocks') -> requests.Response:
    """Login  and returns the token."""
    data = {
        'username': username,
        'password': password
    }
    s = requests.Session()
    url = join(base_url, 'auth', 'login')
    token_url = join(base_url, 'account', 'tokens')
    logger.debug('[LOGIN] Authenticating user {username}...')
    resp = s.post(url, data=json.dumps(data), headers={
        'Content-Type': 'application/json'
    })
    logger.debug('[LOGIN] Done')
    jwt_token = resp.json()['token']

    user_token = get_access_token(jwt_token, token_url)

    if not user_token:
        logger.debug('[LOGIN] Access token not found. Creating one...')
        # Looks like user doesn't have any valid token. Let's create a new one
        user_token = create_access_token(jwt_token, token_url)
        logger.debug('[LOGIN] Done.')
        if resp.status_code != 200:
            msg = 'Unable to request user tokens. Server was unable to return any valid token!'
            logger.error(msg)
            raise errors.RepoCLIError(msg)
    
    # TODO: we are assuming the first token is the one we need... We need to improve this waaaaay more
    return {"user": user_token, "jwt": jwt_token}


def get_login_and_password(args):
    if getattr(args, 'login_username', None):
        username = args.login_username
    else:
        username = input('Username: ')
    #
    password = getattr(args, 'login_password', None)
    return username, password


def interactive_get_token(args, fail_if_already_exists=True):
    # bs = get_server_api(args.token, args.site)
    config = get_config(site=args.site)

    token = None
    # This function could be called from a totally different CLI, so we don't
    # know if the attribute hostname exists.
    # args.site or config.get('default_site')
    url = config.get('url', DEFAULT_URL)
    username, password = get_login_and_password(args)

    for _ in range(3):
        try:
            if password is None:
                password = getpass.getpass(stream=sys.stderr)

            api = RepoApi(base_url=url)
            token = api.login(username, password)

            # token = login_user(username, password, url)
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
    store_token(token, args)
    logger.info('login successful')
    return token


def main(args):
    interactive_login(args)


class SubCommand(SubCommandBase):
    name = "login"
    manages_auth = True

    def main(self):
        self.login()

    def login(self):
        token = self.interactive_get_token()
        store_token(token, self.args)
        self.log.info('login successful')
        return token  # ['id']


    def get_login_and_password(self):
        if getattr(self.args, 'login_username', None):
            username = self.args.login_username
        else:
            username = input('Username: ')
        self.username = username
        password = getattr(self.args, 'login_password', None)
        return username, password


    def interactive_get_token(self):
        username, password = self.get_login_and_password()
        for _ in range(3):
            try:
                if password is None:
                    password = getpass.getpass(stream=sys.stderr)

                token = self.api.login(username, password)

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

    def add_parser(self, subparsers):
        self.subparser = subparser = subparsers.add_parser('login', help='Authenticate a user', description=__doc__)
        subparser.add_argument('--hostname', default=platform.node(),
                               help="Specify the host name of this login, this should be unique (default: %(default)s)")
        subparser.add_argument('--username', dest='login_username',
                               help="Specify your username. If this is not given, you will be prompted")
        subparser.add_argument('--password', dest='login_password',
                               help="Specify your password. If this is not given, you will be prompted")
        subparser.set_defaults(main=self.main)


def add_parser(subparsers):
    subparser = subparsers.add_parser('login', help='Authenticate a user', description=__doc__)
    subparser.add_argument('--hostname', default=platform.node(),
                           help="Specify the host name of this login, this should be unique (default: %(default)s)")
    subparser.add_argument('--username', dest='login_username',
                           help="Specify your username. If this is not given, you will be prompted")
    subparser.add_argument('--password', dest='login_password',
                           help="Specify your password. If this is not given, you will be prompted")
    subparser.set_defaults(main=main)
