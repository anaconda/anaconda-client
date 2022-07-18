from __future__ import unicode_literals

import logging
import requests

logger = logging.getLogger('binstar.requests_ext')


class NullAuth(requests.auth.AuthBase):
    """force requests to ignore the ``.netrc``

    Some sites do not support regular authentication, but we still
    want to store credentials in the ``.netrc`` file and submit them
    as form elements. Without this, requests would otherwise use the
    .netrc which leads, on some sites, to a 401 error.

    https://github.com/kennethreitz/requests/issues/2773

    Use with::

        requests.get(url, auth=NullAuth())
    """
    def __call__(self, r):
        return r
