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
            'artifacts': join(self.base_url, 'artifacts'),
            'user_channels': join(self.base_url, 'account', 'channels'),
            'token_info': join(self.base_url, 'account', 'token-info'),
            'user_tokens': join(self.base_url, 'account', 'tokens'),
            'scopes': join(self.base_url, 'system', 'scopes'),
            'cves': join(self.base_url, 'cves'),
        }


    def create_access_token(self):
        # TODO: Should we remove expires_at and let the server pick the default?

        data = {
            'name': 'repo-cli-token',
            'expires_at': str(datetime.datetime.now().date() + datetime.timedelta(days=30)),
            'scopes': ['channel:view', 'channel:view-artifacts', 'artifact:view', 'artifact:download',
                       'subchannel:create', 'subchannel:edit', 'subchannel:view', 'subchannel:delete',
                       'subchannel:view-artifacts', 'channel:create', 'artifact:create', 'subchannel:history',
                       'subchannel:manage-groups', 'channel:edit', 'channel:delete', 'channel:history',
                       'channel:manage-groups', 'channel:set-default-channel', 'artifact:edit',
                       'artifact:delete']

        }
        resp = requests.post(self._urls['account_tokens'], data=json.dumps(data), headers=self.bearer_headers)
        if resp.status_code != 200:
            msg = 'Error requesting a new user token! Server responded with %s: %s' % (resp.status_code, resp.content)
            logger.error(msg)
            raise errors.RepoCLIError(msg)

        self._access_token = resp.json()['token']
        return self._access_token

    @property
    def bearer_headers(self):
        headers = {
            'Authorization': f'Bearer {self._jwt}',
            'Content-Type': 'application/json'
        }
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

    def login(self, username, password) -> requests.Response:
        """Login  and returns the token."""
        data = {
            'username': username,
            'password': password
        }
        s = requests.Session()
        logger.debug('[LOGIN] Authenticating user {username}...')
        resp = s.post(self._urls['login'], data=json.dumps(data), headers={'Content-Type': 'application/json'})
        logger.debug('[LOGIN] Done')

        if resp.status_code != 200:
            logger.info('[LOGIN] Error logging in...')
            logger.debug(f'Server responded with response {resp.status_code}\nData: {resp.content}')
            raise errors.Unauthorized()

        self._jwt = jwt_token = resp.json()['token']

        user_token = self.get_access_token()

        if not user_token:
            logger.debug('[LOGIN] Access token not found. Creating one...')
            # Looks like user doesn't have any valid token. Let's create a new one
            user_token = self.create_access_token()
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
        _channel = channel
        logger.debug(f'Creating channel {_channel} on {self.base_url}')
        if '/' in channel:
            # this is a subchannel....
            channel, subchannel = channel.split('/')
            url = join(self._urls['channels'], channel, 'subchannels')
            data = {'name': subchannel}
            headers = self.get_xauth_headers({'Content-Type': 'application/json'})
        else:
            url = join(self._urls['channels'])
            data = {'name': channel}
            headers = self.get_xauth_headers({'Content-Type': 'application/json'})

        response = requests.post(url, json=data, headers=headers)
        return self._manage_reponse(response, f'creating channel {_channel}', success_codes=[201])

    def remove_channel(self, channel):
        url = self._get_channel_url(channel)
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
        # url = join(self._urls['channels'], channel)
        url = self._get_channel_url(channel)
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


    def is_subchannel(self, channel):
        """Return True if channel is a path to a subchannel, False otherwise. For example:

        >> is_subchannel("main")
            False
        >> is_subchannel("main/stage")
            True

        Args:
            channel (str): name of the channel

        Returns:
            (bool)"""
        return '/' in channel

    def _get_channel_url(self, channel):
        """Return a channel url based on the fact that it's a normal channel or
         a subchannel

        Args:
            channel (str): name of the channel

        Returns:
            (str) url
        """
        if self.is_subchannel(channel):
            # this is a subchannel....
            channel, subchannel = channel.split('/')
            url = join(self._urls['channels'], channel, 'subchannels', subchannel)
        else:
            url = join(self._urls['channels'], channel)
        return url

    def get_channel(self, channel):
        logger.debug(f'Getting channel {channel} on {self.base_url}')
        url = self._get_channel_url(channel)
        response = requests.get(url, headers=self.get_xauth_headers({'Content-Type': 'application/json'}))
        return self._manage_reponse(response, f'getting channel {channel}')

    def get_channel_history(self, channel, offset=0, limit=50):
        logger.debug(f'Getting channel {channel} history {self.base_url}')
        url = join(self._get_channel_url(channel), 'history?offset=%s&limit=%s' % (offset, limit))
        response = requests.get(url, headers=self.get_xauth_headers({'Content-Type': 'application/json'}))
        return self._manage_reponse(response, f'getting channel {channel}')

    def list_user_channels(self):
        logger.debug(f'Getting user channels from {self.base_url}')
        response = requests.get(self._urls['user_channels'],
                                headers=self.get_xauth_headers({'Content-Type': 'application/json'}))
        return self._manage_reponse(response, f'getting user channels')

    def get_channel_subchannels(self, channel):
        logger.debug(f'Getting channel {channel} subchannels on {self.base_url}')
        url = join(self._urls['channels'], channel, 'subchannels')
        response = requests.get(url, headers=self.get_xauth_headers({'Content-Type': 'application/json'}))
        return self._manage_reponse(response, f'getting channel {channel} subchannel')

    def create_mirror(self, channel, source_root, name, mode, type_, cron, run_now):
        url = join(self._get_channel_url(channel), 'mirrors')
        mirror_details = {
            "mirror_name": name,
            "source_root": source_root,
            "mirror_mode": mode,
            "cron": cron,
            "mirror_type": type_,
            # "filters": {"subdirs": ["osx-64"]},
            "run_now": run_now,
        }
        resp = requests.post(url, data=json.dumps(mirror_details), headers=self.bearer_headers)
        return self._manage_reponse(resp, f'creating mirror {name} on channel {channel}', success_codes=[201])

    def get_mirrors(self, channel):
        url = join(self._get_channel_url(channel), 'mirrors')
        resp = requests.get(url, headers=self.xauth_headers)
        return self._manage_reponse(resp, f'creating mirrors on channel {channel}')

    def get_mirror(self, channel, mirror_name):
        url = join(self._get_channel_url(channel), 'mirrors', mirror_name)
        resp = requests.get(url, headers=self.xauth_headers)
        return self._manage_reponse(resp, f'Getting mirror {mirror_name} on channel {channel}')

    def delete_mirror(self, channel, mirror_name):
        url = join(self._get_channel_url(channel), 'mirrors', mirror_name)
        resp = requests.delete(url, headers=self.bearer_headers)
        return self._manage_reponse(resp, f'Getting mirror {mirror_name} on channel {channel}',
                                    success_codes=[204])

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
            if response.status_code == 401:
                logger.debug(msg)
            else:
                logger.error(msg)
            if response.status_code in auth_fail_codes:
                raise errors.Unauthorized()
            raise errors.RepoCLIError("%s operation failed.")
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
    def channel_artifacts_bulk_actions(self, channel, action, artifacts, target_channel=None):
        url = join(self._urls['channels'], channel, 'artifacts', 'bulk')
        data = {
            "action": action,
            "items": artifacts
        }
        if target_channel:
            if '/' in target_channel:
                # this is a subchannel....
                data['target_channel'], data['target_subchannel'] = target_channel.split('/')
            else:
                data['target_channel'] = target_channel

        resp = requests.put(url, data=json.dumps(data),
                            headers=self.get_xauth_headers({'Content-Type': 'application/json'}),
                            # headers=self.bearer_headers
                            )
        return self._manage_reponse(resp, "%s articfacts" % action, success_codes=[202],
                                    auth_fail_codes=[401, 403, 404])

    def get_channel_artifacts(self, channel):
        # url = join(self._urls['channels'], channel, 'artifacts')
        url = join(self._get_channel_url(channel), 'artifacts')
        resp = requests.get(url, headers=self.xauth_headers)
        return self._manage_reponse(resp, "getting artifacts").get('items', [])

    def get_channel_artifacts_files(self, channel, family, package=None, version=None, filename=None,
                                    return_raw=False):
        file_family_parsers = {
            'conda': self._parse_conda_file,
            'cran': self._parse_cran_file,
            'python': self._parse_python_file,
        }
        artifact_files = []
        if package:
            packages = [package]
        else:
            # url = join(self._urls['channels'], channel, 'artifacts')
            # resp = requests.get(url, headers=self.xauth_headers)
            # data = self._manage_reponse(resp, "getting articfacts")
            data = self.get_channel_artifacts(channel)
            packages = [pkg['name'] for pkg in data if pkg['file_count'] > 0 and pkg['family'] == family]

        for package in packages:
            url = join(self._get_channel_url(channel), 'artifacts', family, package, 'files')
            # url = join(self._urls['channels'], channel, 'artifacts', family, package, 'files')
            resp = requests.get(url, headers=self.xauth_headers)
            files = self._manage_reponse(resp, "getting articfacts")

            for file_data in files['items']:
                rec = file_family_parsers[family](file_data, version, filename,)
                if rec:
                    artifact_files.append(rec)

        return artifact_files

    def _parse_conda_file(self, file_data, version, filename, return_raw = False):
        meta = file_data['metadata']['index.json']
        # TODO: We need to improve version checking... for now it's exact match
        if version and meta['version'] != version:
            return
        if filename and meta['fn'] != filename:
            return
        if return_raw:
            rec = file_data
        else:
            rec = {'name': file_data['name'], 'ckey': file_data['ckey']}
            rec.update({key: meta.get(key, "") for key in ['version', 'fn', 'platform']})

        return rec

    def _parse_cran_file(self, file_data, version, filename, return_raw=False):
        meta = file_data['metadata']
        fn = file_data['ckey'].split('/')[-1]

        # TODO: We need to improve version checking... for now it's exact match
        if version and meta['Version'] != version:
            return
        if filename and fn != filename:
            return
        if return_raw:
            rec = file_data
        else:
            rec = {'name': file_data['name'], 'ckey': file_data['ckey']}
            # rec.update({key: meta.get(key, "") for key in ['version', 'fn', 'platform']})
            rec.update(meta)
            rec['version'] = rec.pop('Version')
            rec['fn'] = fn
            rec['platform'] = 'n/a'
        return rec

    def _parse_python_file(self, file_data, version, filename, return_raw=False):
        raise NotImplementedError()

    def get_artifacts(self, query, limit=50, offset=0, sort="-download_count"):
        url = "%s?q=%s&limit=%s&offset=%s&sort=%s" %(self._urls['artifacts'], query, limit, offset, sort)
        response = requests.get(url, headers=self.xauth_headers)
        return self._manage_reponse(response, "searching artifacts")


    # CVE related endpoints
    def get_cves(self, offset=0, limit=25):
        url = "%s?offset=%s&limit=%s" % (self._urls['cves'], offset, limit)
        response = requests.get(url, headers=self.xauth_headers)
        return self._manage_reponse(response, "getting cves")

    def get_cve(self, cve_id):
        url = "%s/%s" % (self._urls['cves'], cve_id)
        response = requests.get(url, headers=self.xauth_headers)
        return self._manage_reponse(response, "getting cve id")