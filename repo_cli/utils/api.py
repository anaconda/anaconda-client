from __future__ import unicode_literals
import json
import datetime
from os.path import join
import logging
import platform
import socket
import sys
import requests

from .. import errors

logger = logging.getLogger('repo_cli')


class RepoApi:
    def __init__(self, base_url):
        self.base_url = base_url
        self._access_token = None
        self._jwt = None
        self._urls = {
            'account': join(self.base_url, 'account'),
            'account_tokens': join(self.base_url, 'account', 'tokens'),
            'login': join(self.base_url, 'auth', 'login'),
            'logout': join(self.base_url, 'logout'),
        }


    def create_access_token(self):
        # TODO: Should we remove expires_at and let the server pick the default?

        data = {
            'name': 'repo-cli-token',
            'expires_at': str(datetime.datetime.now().date() + datetime.timedelta(days=30)),
            'scopes': ['channel:view', 'channel:view-artifacts', 'artifact:view', 'artifact:download',
                       'subchannel:view', 'subchannel:view-artifacts', 'channel:create', 'artifact:create',
                       'channel:edit', 'channel:delete', 'channel:history', 'channel:manage-groups',
                       'channel:set-default-channel',
                       'artifact:edit', 'artifact:delete']

        }
        resp = requests.post(self._urls['account_tokens'], data=json.dumps(data), headers=self.bearer_headers)
        if resp.status_code != 200:
            msg = 'Error requesting a new user token! Server responded with %s: %s' % (resp.status_code, resp.content)
            logger.error(msg)
            raise errors.RepoCLIError(msg)

        self._access_token = resp.json()['token']
        return self._access_token

    @property
    def bearer_headers(self, content_type='application/json'):
        headers = {'Authorization': f'Bearer {self.jwt}'}
        if content_type:
            headers['Content-Type'] = content_type
        return headers

    def get_access_token(self):
        logger.debug('[API] Getting access token.. ')
        token_resp = requests.get(self._urls['account_tokens'], headers=self.bearer_headers)
        if token_resp.status_code != 200:
            msg = 'Error retrieving user token! Server responded with %s: %s' % (
            token_resp.status_code, token_resp.content)
            logger.error(msg)
            raise errors.RepoCLIError(msg)

        user_tokens = token_resp.json().get('items', [])
        logger.debug(f'[LOGIN] Access token retrieved.. {len(user_tokens)}')
        if user_tokens:
            # ok, we got the token. Now we need to refresh it
            token_to_refresh = user_tokens[0]['id']
            refresh_url = join(self._urls['account_tokens'], token_to_refresh)
            logger.debug('[ACCESS_TOKEN] Refreshing token.. {token_to_refresh}')
            token_resp = requests.put(refresh_url, headers=self.bearer_headers)
            if token_resp.status_code != 200:
                msg = 'Error refreshing user token! Server responded with %s: %s' % (
                token_resp.status_code, token_resp.content)
                logger.error(msg)
                raise errors.RepoCLIError(msg)
            self._access_token = new_token = token_resp.json()['token']
            logger.debug('[ACCESS_TOKEN] Token Refreshed')
            return new_token

        return None

    def login(self, username='john', password='password') -> requests.Response:
        """Login  and returns the token."""
        data = {
            'username': username,
            'password': password
        }
        s = requests.Session()
        # url = join(self.base_url, 'auth', 'login')
        # token_url = join(self.base_url, 'account', 'tokens')
        logger.debug('[LOGIN] Authenticating user {username}...')
        resp = s.post(self._urls['login'], data=json.dumps(data), headers={'Content-Type': 'application/json'})
        logger.debug('[LOGIN] Done')

        if resp.status_code != 200:
            logger.info('[LOGIN] Error logging in...')
            logger.debug(f'Server responded with response {resp.status_code}\nData: {resp.content}')
            raise errors.Unauthorized()

        self.jwt = jwt_token = resp.json()['token']

        # user_token = self.get_access_token(jwt_token, self._urls['account_tokens'])
        user_token = self.get_access_token()

        if not user_token:
            logger.debug('[LOGIN] Access token not found. Creating one...')
            # Looks like user doesn't have any valid token. Let's create a new one
            # user_token = self.create_access_token(jwt_token, self._urls['account_tokens'])
            user_token = self.create_access_token()#jwt_token, self._urls['account_tokens'])
            logger.debug('[LOGIN] Done.')
            if resp.status_code != 200:
                msg = 'Unable to request user tokens. Server was unable to return any valid token!'
                logger.error(msg)
                raise errors.RepoCLIError(msg)

        # TODO: we are assuming the first token is the one we need... We need to improve this waaaaay more
        return {"user": user_token, "jwt": jwt_token}