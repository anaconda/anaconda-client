"""API client methods for conda channel notices."""

from __future__ import annotations

from typing import Any, Dict, Optional

import requests

from binstar_client.utils import jencode


def notice_error_message(data: dict, fallback: str) -> str:
    """Parse structured notice API errors or fall back to generic error text."""
    if 'code' in data and 'message' in data:
        msg = f"{data['code']}: {data['message']}"
        request_id = data.get('requestId')
        if request_id:
            msg += f' (requestId: {request_id})'
        return msg
    return data.get('error', fallback)


class NoticesMixin:
    def _check_notice_response(self, res, allowed=None):
        self._check_response(res, allowed, parse_error=notice_error_message)

    def _anonymous_headers(self) -> Dict[str, str]:
        return {key: value for key, value in self.session.headers.items() if key.lower() != 'authorization'}

    def _notice_url(self, owner: str, notice_id: str, action: Optional[str] = None) -> str:
        url = f'{self.domain}/{owner}/notices/{notice_id}'
        if action:
            url = f'{url}/{action}'
        return url

    def list_active_notices(self, owner: Optional[str] = None) -> Dict[str, Any]:
        """List published, non-expired notices (public endpoint)."""
        url = f'{self.domain}/notices/active'
        params: Dict[str, str] = {}
        if owner:
            params['owner'] = owner

        request = requests.Request('GET', url, params=params or None, headers=self._anonymous_headers())
        prepared = self.session.prepare_request(request)
        prepared.headers.pop('Authorization', None)
        res = self.session.send(prepared)
        self._check_notice_response(res, [200])
        return res.json()

    def list_notices(
        self,
        owner: str,
        status: Optional[str] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """List notices for a channel owner (admin, paginated)."""
        url = f'{self.domain}/notices'
        params: Dict[str, Any] = {'owner': owner, 'offset': offset, 'limit': limit}
        if status:
            params['status'] = status

        res = self.session.get(url, params=params)
        self._check_notice_response(res, [200])
        return res.json()

    def get_notice(self, owner: str, notice_id: str) -> Dict[str, Any]:
        """Get a single notice (admin)."""
        res = self.session.get(self._notice_url(owner, notice_id))
        self._check_notice_response(res, [200])
        return res.json()

    def create_notice(
        self,
        owner: str,
        notice_id: str,
        message: str,
        level: str,
        expires_at: str,
    ) -> Dict[str, Any]:
        """Create a draft notice."""
        url = f'{self.domain}/{owner}/notices'
        data, headers = jencode(
            notice_id=notice_id,
            message=message,
            level=level,
            expires_at=expires_at,
        )
        res = self.session.post(url, data=data, headers=headers)
        self._check_notice_response(res, [201])
        return res.json()

    def update_notice(self, owner: str, notice_id: str, **fields: Optional[str]) -> Dict[str, Any]:
        """Update a notice (partial)."""
        payload = {key: value for key, value in fields.items() if value is not None}
        data, headers = jencode(**payload)
        res = self.session.patch(self._notice_url(owner, notice_id), data=data, headers=headers)
        self._check_notice_response(res, [200])
        return res.json()

    def delete_notice(self, owner: str, notice_id: str) -> None:
        """Soft-delete a notice."""
        res = self.session.delete(self._notice_url(owner, notice_id))
        self._check_notice_response(res, [204])

    def _lifecycle_notice(self, owner: str, notice_id: str, action: str) -> Dict[str, Any]:
        res = self.session.post(self._notice_url(owner, notice_id, action))
        self._check_notice_response(res, [200])
        return res.json()

    def publish_notice(self, owner: str, notice_id: str) -> Dict[str, Any]:
        """Publish a draft notice."""
        return self._lifecycle_notice(owner, notice_id, 'publish')

    def archive_notice(self, owner: str, notice_id: str) -> Dict[str, Any]:
        """Archive a notice."""
        return self._lifecycle_notice(owner, notice_id, 'archive')
