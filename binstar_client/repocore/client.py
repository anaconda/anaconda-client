"""Repocore API client for Anaconda repository channel management."""

import logging
import os
import re
from os.path import basename
from posixpath import join
from typing import Optional

from anaconda_auth.client import BaseClient

from binstar_client.repocore.errors import InvalidName, RepoCoreError, Unauthorized
from binstar_client.repocore.models import (
    Channel,
    Namespace,
    NamespaceChannel,
)
from binstar_client.repocore.package_utils import PackageType

logger = logging.getLogger(__name__)

REPO_API_PATH = "/api/repo"
AUTH_API_PATH = "/api/auth"


class RepoCoreClient(BaseClient):
    """HTTP client for the repocore (PSM) API.

    Extends anaconda_auth.BaseClient which handles domain resolution,
    Bearer token injection, and login-required prompting automatically.
    """

    def __init__(self, site=None, ssl_verify=None, version=None):
        kwargs = {}
        if site:
            kwargs["site"] = site
        if ssl_verify is not None:
            kwargs["ssl_verify"] = ssl_verify

        super().__init__(**kwargs)

        if version:
            self._user_agent = f"anaconda-client/{version}"

    @property
    def _api_base(self):
        return self._base_uri + REPO_API_PATH

    @property
    def _auth_api_base(self):
        return self._base_uri + AUTH_API_PATH

    @property
    def _channels_url(self):
        return join(self._api_base, "channels")

    @property
    def account(self):
        """Get user account information."""
        url = join(self._auth_api_base, "account", "me")
        response = self.get(url)
        return self._manage_response(response, "getting account information")

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
                raise InvalidName(f"Channel name {name} is not valid. It contains more than one '/'")
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

    def _extract_error_message(self, response, action=""):
        """Extract a user-friendly error message from a response."""
        try:
            data = response.json()
            if isinstance(data, dict):
                error = data.get("error")
                if isinstance(error, dict):
                    error = error.get("message") or error.get("detail") or ""
                return data.get("message") or data.get("detail") or str(error or "")
        except (ValueError, KeyError):
            pass
        return f"Error {action} (status {response.status_code})"

    def _manage_response(self, response, action="", success_codes=None):
        if not success_codes:
            success_codes = [200]
        if response.status_code in success_codes:
            if response.status_code == 204:
                return None
            return response.json()

        msg = self._extract_error_message(response, action)

        if response.status_code in (401, 403):
            raise Unauthorized(msg)

        raise RepoCoreError(msg)

    def list_user_organizations(self) -> list[Namespace]:
        url = join(self._auth_api_base, "organizations", "my")
        response = self.get(url)
        data = self._manage_response(response, "getting user organizations")
        return [Namespace(**org) for org in data]

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
        msg = self._extract_error_message(response, f"removing channel {channel}")
        if response.status_code == 403:
            raise Unauthorized(msg)
        raise RepoCoreError(msg)

    def get_namespace_channel(self, channel: str) -> NamespaceChannel:
        url = self._get_channel_url(channel)
        response = self.get(url)
        data = self._manage_response(response, f"getting channel {channel}")
        return NamespaceChannel(**data)

    def update_channel(self, channel: str, **data):
        url = self._get_channel_url(channel)
        response = self.put(url, json=data)
        if response.status_code in [200, 204]:
            return None
        msg = self._extract_error_message(response, f"updating channel {channel}")
        if response.status_code == 403:
            raise Unauthorized(msg)
        raise RepoCoreError(msg)

    def get_channels(self, channel: str, offset: int = 0, limit: int = 50) -> list[Channel]:
        url = join(self._channels_url, channel, "subchannels")
        response = self.get(url, params={"offset": offset, "limit": limit})
        data = self._manage_response(response, f"getting channel {channel} subchannels")
        return [Channel(**item) for item in data.get("items", [])]

    def create_namespace_channel(self, channel_name: str, namespace: Optional[str] = None, privacy: str = "private"):
        url = join(self._api_base, "namespace-channels")
        data = {"channel_name": channel_name, "privacy": privacy}

        if namespace:
            data["namespace"] = namespace
        response = self.post(url, json=data)
        return self._manage_response(response, f"creating namespace channel {channel_name}", success_codes=[200, 201])

    def upload_file(self, filepath: str, channel: str, package_type: str):
        try:
            pkg_type = PackageType(package_type)
        except ValueError:
            raise RepoCoreError(f"{package_type} upload is not supported")

        artifact_type = pkg_type.upload_type
        url = join(self._channels_url, channel, "artifacts")
        statinfo = os.stat(filepath)
        filename = basename(filepath)

        with open(filepath, "rb") as f:
            multipart_form_data: list[tuple[str, tuple[str | None, str | bytes]]] = [
                ("content", (filename, f.read())),
                ("filetype", (None, artifact_type)),
                ("size", (None, str(statinfo.st_size))),
            ]
            response = self.post(url, files=multipart_form_data)

        return response
