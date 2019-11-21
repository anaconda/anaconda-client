from __future__ import unicode_literals
import json
import datetime
from os.path import join, basename
import logging
import os
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
            'account_me': join(self.base_url, 'account', 'me'),
            'login': join(self.base_url, 'auth', 'login'),
            'logout': join(self.base_url, 'logout'),
            'channels': join(self.base_url, 'channels'),
            'user_channels': join(self.base_url, 'account', 'channels'),
            'token_info': join(self.base_url, 'account', 'token-info'),
            'user_tokens': join(self.base_url, 'account', 'tokens'),
            'scopes': join(self.base_url, 'system', 'scopes'),
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
        headers = {'Authorization': f'Bearer {self._jwt}'}
        if content_type:
            headers['Content-Type'] = content_type
        return headers

    @property
    def xauth_headers(self):
        return self.get_xauth_headers()

    def get_xauth_headers(self, extra_headers=None):
        headers = {'X-Auth': self._access_token}
        if extra_headers:
            headers.update(extra_headers)
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

        self._jwt = jwt_token = resp.json()['token']

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


    def get_default_channel(self):
        url = self._urls['account_me']
        logger.debug(f'[UPLOAD] Getting user default channel from {url}')
        response = requests.get(url, headers=self.xauth_headers)
        return response


    def upload_file(self, filepath, channel):
        url = join(self.base_url, 'channels', channel, 'artifacts')
        statinfo = os.stat(filepath)
        filename = basename(filepath)
        logger.debug(f'[UPLOAD] Using token {self._access_token} on {self.base_url}')
        multipart_form_data = {
            'content': (filename, open(filepath, 'rb')),
            'filetype': (None, 'conda1'),
            'size': (None, statinfo.st_size)
        }
        logger.info(f'Uploading to {url}...')
        response = requests.post(url, files=multipart_form_data, headers=self.xauth_headers)
        return response

    def create_channel(self, channel):
        '''Create a new channel with name `channel` on the repo server at `base_url` using `token`
        to authenticate.

        Args:
              channel(str): name of the channel to be created

        Returns:
              response (http response object)
        '''
        url = self._urls['channels']
        data = {'name': channel}
        logger.debug(f'Creating channel {channel} on {self.base_url}')
        headers = self.get_xauth_headers({'Content-Type': 'application/json'})
        response = requests.post(url, json=data, headers=headers)
        if response.status_code in [201]:
            logger.info(f'Channel {channel} successfully created')
            logger.debug(f'Server responded with {response.status_code}\nData: {response.content}')
        else:
            msg = f'Error creating {channel}.' \
                f'Server responded with status code {response.status_code}.\n' \
                f'Error details: {response.content}'
            logger.error(msg)
            if response.status_code in [403, 401]:
                raise errors.Unauthorized()
        return response

    def remove_channel(self, channel):
        url = join(self._urls['channels'], channel)
        logger.debug(f'Removing channel {channel} on {self.base_url}')
        logger.debug(f'Using token {self._access_token}')
        response = requests.delete(url, headers=self.get_xauth_headers({'Content-Type': 'application/json'}))
        if response.status_code in [202]:
            logger.info(f'Channel {channel} successfully removed')
            logger.debug(f'Server responded with {response.status_code}\nData: {response.content}')
        else:
            msg = f'Error creating {channel}.' \
                f'Server responded with status code {response.status_code}.\n' \
                f'Error details: {response.content}'
            logger.error(msg)
            if response.status_code in [403, 401]:
                raise errors.Unauthorized()
        return response

    def update_channel(self, channel, success_message=None, **data):
        url = join(self._urls['channels'], channel)
        logger.debug(f'Updating channel {channel} on {self.base_url}')
        logger.debug(f'Using token {self._access_token}')
        response = requests.put(url, json=data, headers=self.get_xauth_headers({'Content-Type': 'application/json'}))
        if not success_message:
            success_message = f'Channel {channel} successfully updated.'
        if response.status_code in [200, 204]:
            logger.info(success_message)
            logger.debug(f'Server responded with {response.status_code}\nData: {response.content}')
        else:
            msg = f'Error creating {channel} .' \
                f'Server responded with status code {response.status_code}.\n' \
                f'Error details: {response.content}'
            logger.error(msg)
            if response.status_code in [403, 401]:
                raise errors.Unauthorized()
            # TODO: We should probably need to manage other error states
        return response

    def get_channel(self, channel):
        url = join(self._urls['channels'], channel)
        logger.debug(f'Getting channel {channel} on {self.base_url}')
        response = requests.get(url, headers=self.get_xauth_headers({'Content-Type': 'application/json'}))
        return response

    def list_user_channels(self):
        logger.debug(f'Getting user channels from {self.base_url}')
        response = requests.get(self._urls['user_channels'],
                                headers=self.get_xauth_headers({'Content-Type': 'application/json'}))
        return response


    # TOKEN RELATED URLS
    def _manage_reponse(self, response, action='', success_codes=None, auth_fail_codes=None):
        if not success_codes:
            success_codes = [200]
        if not auth_fail_codes:
            auth_fail_codes = [401, 403]
        if response.status_code in success_codes:
            # deletes shouldn't return anythings
            if response.status_code == 204:
                return
            return response.json()
        else:
            msg = f'Error {action}' \
                f'Server responded with status code {response.status_code}.\n' \
                f'Error details: {response.content}'
            logger.error(msg)
            if response.status_code in auth_fail_codes:
                raise errors.Unauthorized()
            errors.RepoCLIError("%s operation failed.")
        return {}

    def get_token_info(self):
        response = requests.get(self._urls['token_info'], headers=self.xauth_headers)

        if response.status_code in [200, 204]:
            return response.json()
        else:
            msg = f'Error getting token info.' \
                f'Server responded with status code {response.status_code}.\n' \
                f'Error details: {response.content}'
            logger.error(msg)
            if response.status_code in [403, 401]:
                raise errors.Unauthorized()
        return {}

    def get_user_tokens(self):
        response = requests.get(self._urls['account_tokens'], headers=self.bearer_headers)

        if response.status_code in [200, 204]:
            return response.json()
        else:
            msg = f'Error getting user tokens.' \
                f'Server responded with status code {response.status_code}.\n' \
                f'Error details: {response.content}'
            logger.error(msg)
            if response.status_code in [403, 401]:
                raise errors.Unauthorized()
        return []

    def remove_user_token(self, token):
        url = join(self._urls['account_tokens'], token)
        response = requests.delete(url, headers=self.bearer_headers)
        return self._manage_reponse(response, 'removing user token', success_codes=[204])

    def create_user_token(self, name, expiration, scopes=None, resources=None):
        data = {
            'name': name,
            'expires_at': expiration,
        }
        if scopes:
            data['scopes'] = scopes

        if resources:
            data['resources'] = resources

        response = requests.post(self._urls['account_tokens'], data=json.dumps(data),
                                 headers=self.bearer_headers)
        return self._manage_reponse(response, "creating user token", success_codes=[200])

    def get_scopes(self):
        response = requests.get(self._urls['scopes'], headers=self.bearer_headers)
        return self._manage_reponse(response, "getting scopes")

    # --------
    def channel_artifacts_bulk_actions(self, channel, action, artifacts):
        url = join(self._urls['channels'], channel, 'artifacts', 'bulk')
        data = {
            "action": action,
            "items": artifacts
        }
        resp = requests.put(url, data=json.dumps(data),
                            headers=self.get_xauth_headers({'Content-Type': 'application/json'}))
        return self._manage_reponse(resp, "%s articfacts" %action, success_codes=[202])

    def get_channel_artifacts(self, channel):
        url = join(self._urls['channels'], channel, 'artifacts')
        resp = requests.get(url, headers=self.xauth_headers)
        return self._manage_reponse(resp, "getting articfacts").get('items', [])

    def get_channel_artifacts_files(self, channel, family, package=None, version=None, filename=None, return_raw=False):

        artifact_files = []
        if package:
            packages = [package]
        else:
            # url = join(self._urls['channels'], channel, 'artifacts')
            # resp = requests.get(url, headers=self.xauth_headers)
            # data = self._manage_reponse(resp, "getting articfacts")
            data = self.get_channel_artifacts(channel)
            packages = [pkg['name'] for pkg in data]

        for package in packages:
            url = join(self._urls['channels'], channel, 'artifacts', family, package, 'files')
            resp = requests.get(url, headers=self.xauth_headers)
            files = self._manage_reponse(resp, "getting articfacts")

            for file_ in files:
                index_ = file_['metadata']['index.json']
                # TODO: We need to improve version checking... for now it's exact match
                if version and index_['version'] != version:
                    continue
                if filename and index_['fn'] != filename:
                    continue
                if return_raw:
                    artifact_files.append(file_)
                else:
                    rec = {'name': file_['name'], 'ckey': file_['ckey']}
                    rec.update({key: index_[key] for key in ['version', 'fn', 'platform']})
                    artifact_files.append(rec)

        return artifact_files
