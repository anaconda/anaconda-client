# -*- coding: utf8 -*-
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring

from __future__ import annotations

import logging
import typing

from requests.auth import AuthBase

__all__ = ['NullAuth']

logger = logging.getLogger('binstar.requests_ext')

KeyT = typing.TypeVar('KeyT')
ValueT = typing.TypeVar('ValueT')

class NullAuth(AuthBase):  # pylint: disable=too-few-public-methods
    """force requests to ignore the ``.netrc``

    Some sites do not support regular authentication, but we still
    want to store credentials in the ``.netrc`` file and submit them
    as form elements. Without this, requests would otherwise use the
    .netrc which leads, on some sites, to a 401 error.

    https://github.com/psf/requests/issues/2773

    Use with::

        requests.get(url, auth=NullAuth())
    """

    def __call__(self, r):
        return r
