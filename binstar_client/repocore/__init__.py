"""Repocore API client for Anaconda repository channel management."""

import logging
import os
import re
from os.path import basename
from posixpath import join
from typing import Optional

from anaconda_auth.client import BaseClient

from binstar_client.repocore.config import UPLOAD_TYPE_MAPPING
from binstar_client.repocore.errors import (
    AnacondaLoginRequired,
    InvalidName,
    RepoCoreError,
    Unauthorized,
)

logger = logging.getLogger(__name__)


class RepoCoreClient(BaseClient):
    """HTTP client for the repocore (PSM) API.

    Extends anaconda_auth.BaseClient which handles Bearer token injection automatically.
    """

    _user_agent: str = "anaconda-client-repocore/1.0"

    def __init__(self, base_url: str, site=None, ssl_verify=None):
        kwargs = {}
        if site:
            kwargs["site"] = site
        if ssl_verify is not None:
            kwargs["ssl_verify"] = ssl_verify
        kwargs["base_uri"] = base_url

        super().__init__(**kwargs)
        self._base_url = base_url

    @property
    def _channels_url(self):
        return join(self._base_url, "channels")

    @property
    def _account_url(self):
        return join(self._base_url, "account")

    def is_subchannel(self, channel: str) -> bool:
        return "/" in channel

    def _get_channel_url(self, channel: str) -> str:
        if self.is_subchannel(channel):
            parent, sub = channel.split("/", 1)
            return join(self._channels_url, parent, "subchannels", sub)
        return join(self._channels_url, channel)

    def _validate_channel_name(self, name: str):
        if self.is_subchannel(name):
            try:
                channel, subchannel = name.split("/")
            except ValueError:
                raise InvalidName(
                    f"Channel name {name} is not valid. It contains more than one '/'"
                )
            self._validate_channel_name(channel)
            self._validate_channel_name(subchannel)
            return

        if not re.match(r"^[a-z][a-z0-9_-]*$", name):
            invalid_chars = set(r"""!"#$%&'()*+,./:;<=>?@[\]^`{|}~""")
            invalid_letters = list(invalid_chars.intersection(set(name)))
            error_message = f"Channel name '{name}' is not valid."
            if invalid_letters:
                error_message += f" Invalid characters: {invalid_letters}"
            error_message += " Channel names must start with a lowercase letter and contain only lowercase letters, digits, hyphens, and underscores."
            raise InvalidName(error_message)

    def _manage_response(self, response, action="", success_codes=None):
        if not success_codes:
            success_codes = [200]
        if response.status_code in success_codes:
            if response.status_code == 204:
                return None
            return response.json()

        msg = (
            f"Error {action}. "
            f"Server responded with status code {response.status_code}.\n"
            f"Error details: {response.content or None}\n"
        )

        if response.status_code in [401, 403]:
            try:
                error_data = response.json()
                error_message = error_data.get("message", msg)
            except (ValueError, KeyError):
                error_message = msg

            if response.status_code == 403:
                raise Unauthorized(error_message)
            else:
                domain = getattr(self.config, "domain", None)
                raise AnacondaLoginRequired(domain=domain)

        raise RepoCoreError(msg)

    def list_user_channels(self, offset: int = 0, limit: int = 50):
        url = join(self._account_url, "channels")
        response = self.get(url, params={"offset": offset, "limit": limit})
        return self._manage_response(response, "getting user channels")

    def create_channel(self, channel: str, privacy: Optional[str] = None):
        self._validate_channel_name(channel)

        if self.is_subchannel(channel):
            parent, subchannel = channel.split("/")
            url = join(self._channels_url, parent, "subchannels")
            data = {"name": subchannel}
        else:
            url = self._channels_url
            data = {"name": channel}

        if privacy:
            data["privacy"] = privacy

        response = self.post(url, json=data)
        return self._manage_response(response, f"creating channel {channel}", success_codes=[201])

    def remove_channel(self, channel: str):
        url = self._get_channel_url(channel)
        response = self.delete(url)
        if response.status_code in [200, 202, 204]:
            return None
        if response.status_code in [401, 403]:
            raise Unauthorized()
        raise RepoCoreError(
            f"Error removing {channel}. "
            f"Server responded with status code {response.status_code}.\n"
            f"Error details: {response.content}"
        )

    def get_channel(self, channel: str):
        url = self._get_channel_url(channel)
        response = self.get(url)
        return self._manage_response(response, f"getting channel {channel}")

    def update_channel(self, channel: str, **data):
        url = self._get_channel_url(channel)
        response = self.put(url, json=data)
        if response.status_code in [200, 204]:
            return None
        if response.status_code in [401, 403]:
            raise Unauthorized()
        raise RepoCoreError(
            f"Error updating {channel}. "
            f"Server responded with status code {response.status_code}.\n"
            f"Error details: {response.content}"
        )

    def get_channel_subchannels(self, channel: str):
        url = join(self._channels_url, channel, "subchannels")
        response = self.get(url)
        return self._manage_response(response, f"getting channel {channel} subchannels")

    def get_default_channel(self):
        response = self.get(self._account_url)
        data = self._manage_response(response, "getting account details")
        return data.get("default_channel_name")

    def upload_file(self, filepath: str, channel: str, package_type: str, name=None, version=None):
        if package_type not in UPLOAD_TYPE_MAPPING:
            raise RepoCoreError(f"{package_type} upload is not supported")

        artifact_type = UPLOAD_TYPE_MAPPING[package_type]
        url = join(self._channels_url, channel, "artifacts")
        statinfo = os.stat(filepath)
        filename = basename(filepath)

        multipart_form_data = {
            "content": (filename, open(filepath, "rb")),
            "filetype": (None, artifact_type),
            "size": (None, str(statinfo.st_size)),
        }
        if artifact_type == UPLOAD_TYPE_MAPPING["gra"]:
            multipart_form_data["name"] = (None, name)
            if version:
                multipart_form_data["version"] = (None, version)

        response = self.post(url, files=multipart_form_data)
        return response
