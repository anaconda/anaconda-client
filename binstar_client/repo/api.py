"""HTTP client for repo-core (v6) service.

This module provides the RepoApi class for interacting with the repo v6 service.

"""

from __future__ import annotations

import json
import logging
import os
from os.path import basename
from posixpath import join
from typing import Optional

from binstar_client import errors
from binstar_client._version import __version__

from anaconda_auth.client import BaseClient

logger = logging.getLogger('binstar.repo')


class RepoApi:
    """API client for repo-core (v6) servers."""

    def __init__(
        self,
        base_url: str,
        user_token: Optional[str] = None,
        verify_ssl: bool = True,
    ):
        self.base_url = base_url.rstrip('/')
        self._access_token = user_token
        self._client = self._create_client(verify_ssl)
        self._urls: Optional[dict] = None

    def _create_client(self, verify_ssl: bool):
        """Create the HTTP client, via anaconda-auth, which handles
        domain construction, authentication, and configuration more broadly.
        """
        return BaseClient(
            domain=self.base_url,
            ssl_verify=verify_ssl,
            user_agent=f'anaconda-client/{__version__}',
        )

    @property
    def urls(self) -> dict:
        """Lazily construct URL endpoints."""
        if self._urls is None:
            self._urls = {
                'channels': join(self.base_url, 'channels'),
            }
        return self._urls

    def _handle_response(
        self,
        response,
        action: str = '',
        success_codes: Optional[list] = None,
    ):
        """Handle API response, raising appropriate errors."""
        if success_codes is None:
            success_codes = [200, 201]

        if response.status_code in success_codes:
            if response.status_code == 204:
                return None
            try:
                return response.json()
            except ValueError:
                return response.text

        if response.status_code == 401:
            raise errors.Unauthorized('Authentication required')
        if response.status_code == 403:
            raise errors.Unauthorized('Permission denied')
        if response.status_code == 404:
            raise errors.NotFound(f'Not found: {action}')

        msg = (
            f'Error {action}. '
            f'Server responded with status code {response.status_code}.\n'
            f'Error details: {response.content or None}\n'
        )
        raise errors.BinstarError(msg)

    def _get_channel_url(self, channel: str) -> str:
        """Get the URL for a channel, handling subchannels."""
        if '/' in channel:
            parent, subchannel = channel.split('/', 1)
            return join(self.urls['channels'], parent, 'subchannels', subchannel)
        return join(self.urls['channels'], channel)

    def upload_file(
        self,
        filepath: str,
        channel: str,
        package_type: str = 'conda1',
        name: Optional[str] = None,
        version: Optional[str] = None,
    ):
        """Upload a file to a channel.

        Args:
            filepath: Path to the file to upload
            channel: Channel name (can include subchannel as 'channel/subchannel')
            package_type: Type of package (conda1, gra_file, etc.)
            name: Package name (required for general artifacts)
            version: Package version (optional for general artifacts)

        Returns:
            Response from the server
        """
        url = join(self._get_channel_url(channel), 'artifacts')
        statinfo = os.stat(filepath)
        filename = basename(filepath)

        logger.debug(f'Uploading {filename} to {url}')

        multipart_form_data = {
            'content': (filename, open(filepath, 'rb')),
            'filetype': (None, package_type),
            'size': (None, str(statinfo.st_size)),
        }

        if name:
            multipart_form_data['name'] = (None, name)
        if version:
            multipart_form_data['version'] = (None, version)

        logger.info(f'Uploading {package_type} artifact to {url}...')
        response = self._client.post(
            url,
            files=multipart_form_data,
        )
        return response

    def create_channel(self, channel: str):
        """Create a new channel.

        Args:
            channel: Channel name (can include subchannel as 'channel/subchannel')

        Returns:
            Response data from the server
        """
        logger.debug(f'Creating channel {channel} on {self.base_url}')

        if '/' in channel:
            parent, subchannel = channel.split('/', 1)
            url = join(self.urls['channels'], parent, 'subchannels')
            data = {'name': subchannel}
        else:
            url = self.urls['channels']
            data = {'name': channel}

        response = self._client.post(url, json=data)
        return self._handle_response(
            response,
            f'creating channel {channel}',
            success_codes=[201],
        )

    def remove_channel(self, channel: str):
        """Remove a channel.

        Args:
            channel: Channel name (can include subchannel as 'channel/subchannel')
        """
        url = self._get_channel_url(channel)
        logger.debug(f'Removing channel {channel} on {self.base_url}')

        response = self._client.delete(url)

        if response.status_code == 202:
            logger.info(f'Channel {channel} successfully removed')
            return

        if response.status_code in [401, 403]:
            raise errors.Unauthorized()

        msg = (
            f'Error removing {channel}. '
            f'Server responded with status code {response.status_code}.\n'
            f'Error details: {response.content}'
        )
        raise errors.BinstarError(msg)
