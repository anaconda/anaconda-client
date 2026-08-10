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
    Artifact,
    ArtifactFile,
    Channel,
    ChannelCreationResponse,
    ChannelUpdateResponse,
    Namespace,
)
from binstar_client.repocore.package_utils import PackageType

logger = logging.getLogger(__name__)

REPO_API_PATH = "/api/repo"
AUTH_API_PATH = "/api/auth"
ACCOUNT_API_PATH = "/api"


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
    def _account_api_base(self):
        return self._base_uri + ACCOUNT_API_PATH

    @property
    def _channels_url(self):
        return join(self._api_base, "channels")

    @property
    def _account_channels_url(self):
        return join(self._api_base, "account", "channels")

    @property
    def account(self):
        """Get user account information."""
        url = join(self._account_api_base, "account")
        response = self.get(url)
        data, error = self._manage_response(response, "getting account information")
        if error:
            raise error
        return data

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

    def _manage_response(self, response, action="", success_codes=[200], empty_success_codes=[204]):
        """Manages server responses

        Defaults to success_codes of only 200 and No Content success code of 204.
        Callers can pass their own success codes and empty success codes (No Content).

        Resolution order:
          1. If status code has no content (empty success code), return (None, None)
          2. If status code is a non empty success code, return (response.json(), None)
          3. Extract error message
          4. If status code is 401 or 403, return (response.json(), Unauthorized error)
          5. If status code is any other, return (response.json(), RepoCoreError)

        Returns:
            tuple: (response_data, error) where:
                - response_data: The response JSON or None
                - error: Exception to raise if not None, None if successful
        """
        response_data = None
        try:
            response_data = response.json()
        except (ValueError, KeyError):
            pass

        if response.status_code in success_codes:
            if response.status_code in empty_success_codes:
                return None, None
            return response_data, None

        msg = self._extract_error_message(response, action)

        if response.status_code in (401, 403):
            return response_data, Unauthorized(msg)

        return response_data, RepoCoreError(msg)

    def list_user_organizations(self) -> list[Namespace]:
        url = join(self._auth_api_base, "organizations", "my")
        response = self.get(url)
        data, error = self._manage_response(response, "getting user organizations")
        if error:
            raise error
        return [Namespace(**org) for org in data or []]

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
        result, error = self._manage_response(response, f"creating channel {channel}", success_codes=[201])
        return result, error

    def remove_channel(self, channel: str):
        url = self._get_channel_url(channel)
        response = self.delete(url)
        result, error = self._manage_response(
            response, f"removing channel {channel}", success_codes=[200, 202, 204], empty_success_codes=[200, 202, 204]
        )
        return result, error

    def get_namespace_channel(self, channel: str) -> tuple[Optional[Channel], Optional[Exception]]:
        url = self._get_channel_url(channel)
        response = self.get(url)
        data, error = self._manage_response(response, f"getting channel {channel}")
        if error:
            return None, error
        return Channel(**data), None

    def update_channel(self, channel: str, **data) -> tuple[Optional[ChannelUpdateResponse], Optional[Exception]]:
        """Update a channel; ``changed`` reflects the endpoint's ``{"changed": bool}``
        body (``false`` when the channel already held every submitted value)."""
        url = self._get_channel_url(channel)
        response = self.put(url, json=data)
        result, error = self._manage_response(response, f"updating channel {channel}", success_codes=[200])
        if error:
            return None, error
        return ChannelUpdateResponse(changed=bool((result or {}).get("changed", False))), None

    def list_all_channels(
        self, offset: int = 0, limit: int = 100, include_subchannels: bool = True
    ) -> tuple[list[Channel], int, Optional[Exception]]:
        """List every channel the caller can read, including channels shared with them.

        Hits ``GET /channels`` — the server scopes the result to the token's
        permissions (its own namespaces plus any channels shared with the user)

        Returns the page of channels, the server's total count (for paging), and
        any error. On error the page is empty and the count is zero.
        """
        response = self.get(
            self._channels_url,
            params={
                "offset": offset,
                "limit": limit,
                "include_subchannels": include_subchannels,
            },
        )
        data, error = self._manage_response(response, "listing channels")
        if error:
            return [], 0, error
        items = [Channel(**item) for item in (data or {}).get("items", [])]
        return items, (data or {}).get("total_count", len(items)), None

    def list_my_channels(
        self, offset: int = 0, limit: int = 100, include_subchannels: bool = True
    ) -> tuple[list[Channel], int, Optional[Exception]]:
        """List only the channels the caller owns or has had shared with them.

        Hits ``GET /account/channels`` — unlike ``list_all_channels`` this excludes
        public channels the caller merely has read access to, returning just the
        user's own namespaces plus channels explicitly shared with them.

        Returns the page of channels, the server's total count (for paging), and
        any error. On error the page is empty and the count is zero.
        """
        response = self.get(
            self._account_channels_url,
            params={
                "offset": offset,
                "limit": limit,
                "include_subchannels": include_subchannels,
            },
        )
        data, error = self._manage_response(response, "listing account channels")
        if error:
            return [], 0, error
        items = [Channel(**item) for item in (data or {}).get("items", [])]
        return items, (data or {}).get("total_count", len(items)), None

    def get_channels(self, channel: str, offset: int = 0, limit: int = 50) -> tuple[list[Channel], Optional[Exception]]:
        url = join(self._channels_url, channel, "subchannels")
        response = self.get(url, params={"offset": offset, "limit": limit})
        data, error = self._manage_response(response, f"getting channel {channel} subchannels")
        if error:
            return [], error
        return [Channel(**item) for item in (data or {}).get("items", [])], None

    def create_namespace_channel(
        self, channel_name: str, namespace: Optional[str] = None, privacy: str = "private"
    ) -> tuple[Optional[ChannelCreationResponse], Optional[Exception]]:
        url = join(self._api_base, "namespace-channels")
        data = {"channel_name": channel_name, "privacy": privacy}

        if namespace:
            data["namespace"] = namespace
        response = self.post(url, json=data)
        result, error = self._manage_response(
            response, f"creating namespace channel {channel_name}", success_codes=[200, 201]
        )
        if error:
            return None, error
        return ChannelCreationResponse(status_code=response.status_code, **result), None

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

        result, error = self._manage_response(response, f"uploading {filename}", success_codes=[200, 201])
        return result, error

    def _artifacts_url(self, channel: str) -> str:
        """Base ``.../artifacts`` URL for a channel or subchannel.

        Reuses ``_get_channel_url`` so subchannels resolve to the
        ``/channels/{parent}/subchannels/{sub}`` form the server expects.
        """
        return join(self._get_channel_url(channel), "artifacts")

    def list_artifacts(
        self,
        channel: str,
        offset: int = 0,
        limit: int = 100,
        query: Optional[str] = None,
        artifact_family: Optional[str] = None,
        platform: Optional[str] = None,
        sort: Optional[str] = None,
    ) -> tuple[list[Artifact], int]:
        """List packages (artifacts) in a channel.

        Each item is a *package* grouped by family + name — not an individual
        file. Returns the page of artifacts and the server's total count.
        """
        params: dict = {"offset": offset, "limit": limit}
        if query:
            params["q"] = query
        if artifact_family:
            params["artifact_family"] = artifact_family
        if platform:
            params["platform"] = platform
        if sort:
            params["sort"] = sort

        response = self.get(self._artifacts_url(channel), params=params)
        data, error = self._manage_response(response, f"listing artifacts in {channel}")
        if error:
            raise error
        items = [Artifact(**item) for item in data.get("items", [])]
        return items, data.get("total_count", len(items))

    def list_artifact_files(
        self,
        channel: str,
        artifact_family: str,
        artifact_name: str,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[list[ArtifactFile], int]:
        """List the individual files of a package in a channel."""
        url = join(self._artifacts_url(channel), artifact_family, artifact_name, "files")
        response = self.get(url, params={"offset": offset, "limit": limit})
        data, error = self._manage_response(
            response, f"listing files for {artifact_family}/{artifact_name} in {channel}"
        )
        if error:
            raise error
        items = [ArtifactFile(**item) for item in data.get("items", [])]
        return items, data.get("total_count", len(items))

    def delete_artifact_file(self, channel: str, artifact_family: str, artifact_name: str, ckey: str):
        """Delete a single file (identified by ``ckey``) from a channel.

        Uses the bulk endpoint with a ``ckey`` so only that one file (route) is
        removed, rather than the whole package that ``DELETE .../{family}/{name}``
        would drop. Returns on the server's 202 Accepted.
        """
        url = join(self._artifacts_url(channel), "bulk")
        data = {
            "action": "delete",
            "items": [{"name": artifact_name, "family": artifact_family, "ckey": ckey}],
        }
        response = self.put(url, json=data)
        result, error = self._manage_response(
            response,
            f"removing {ckey} from {channel}",
            success_codes=[200, 202, 204],
            empty_success_codes=[200, 202, 204],
        )
        if error:
            raise error
        return result

    def share_channel(self, namespace: str, channel_name: str, user: str, action: str = "share", grant: str = "read"):
        url = join(self._api_base, "namespaces", namespace, "channels", channel_name, "sharing")
        data = {"action": action, "user": user}
        if action == "share":
            data["grant"] = grant

        response = self.post(url, json=data)
        channel_path = f"{namespace}/{channel_name}"
        action_verb = "sharing" if action == "share" else "unsharing"
        result, error = self._manage_response(
            response, f"{action_verb} channel {channel_path} with {user}", success_codes=[200]
        )
        return result, error
