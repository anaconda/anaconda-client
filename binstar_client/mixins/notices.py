"""API client methods for conda channel notices."""

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


def conda_notices_base_url(api_domain: str) -> str:
    """Base URL for notices.json — prod maps the API host to the conda CDN."""
    domain = api_domain.rstrip('/')
    if 'api.anaconda.org' in domain:
        return 'https://conda.anaconda.org'
    return domain


class NoticesMixin:
    def _check_notice_response(self, res, allowed=None):
        self._check_response(res, allowed, parse_error=notice_error_message)

    def _anonymous_headers(self):
        return {
            str(key): str(value) for key, value in self.session.headers.items() if str(key).lower() != 'authorization'
        }

    def _notice_url(self, channel, notice_id, action=None):
        url = f'{self.domain}/{channel}/notices/{notice_id}'
        if action:
            url = f'{url}/{action}'
        return url

    def fetch_conda_notices(self, channel):
        """Fetch published notices (replaces GET /notices/active)."""
        base = conda_notices_base_url(self.domain)
        url = f'{base}/{channel}/notices.json'
        request = requests.Request('GET', url, headers=self._anonymous_headers())
        prepared = self.session.prepare_request(request)
        prepared.headers.pop('Authorization', None)
        res = self.session.send(prepared)
        if res.status_code == 404:
            return {'notices': []}
        self._check_notice_response(res, [200])
        return res.json()

    def list_notices(self, channel, status=None, offset=0, limit=20):
        """List notices for a channel (admin, paginated)."""
        url = f'{self.domain}/{channel}/notices'
        params = {'offset': offset, 'limit': limit}
        if status:
            params['status'] = status

        res = self.session.get(url, params=params)
        self._check_notice_response(res, [200])
        return res.json()

    def get_notice(self, channel, notice_id):
        """Get a single notice (admin)."""
        res = self.session.get(self._notice_url(channel, notice_id))
        self._check_notice_response(res, [200])
        return res.json()

    def create_notice(self, channel, message, level, expires_at):
        """Create a draft notice (server assigns notice_id)."""
        url = f'{self.domain}/{channel}/notices'
        data, headers = jencode(
            message=message,
            level=level,
            expires_at=expires_at,
        )
        res = self.session.post(url, data=data, headers=headers)
        self._check_notice_response(res, [201])
        return res.json()

    def update_notice(self, channel, notice_id, **fields):
        """Update a notice (partial)."""
        payload = {key: value for key, value in fields.items() if value is not None}
        data, headers = jencode(**payload)
        res = self.session.patch(self._notice_url(channel, notice_id), data=data, headers=headers)
        self._check_notice_response(res, [200])
        return res.json()

    def delete_notice(self, channel, notice_id):
        """Soft-delete a notice."""
        res = self.session.delete(self._notice_url(channel, notice_id))
        self._check_notice_response(res, [204])

    def _lifecycle_notice(self, channel, notice_id, action):
        res = self.session.post(self._notice_url(channel, notice_id, action))
        self._check_notice_response(res, [200])
        return res.json()

    def publish_notice(self, channel, notice_id):
        """Publish a draft notice."""
        return self._lifecycle_notice(channel, notice_id, 'publish')

    def archive_notice(self, channel, notice_id):
        """Archive a notice."""
        return self._lifecycle_notice(channel, notice_id, 'archive')
