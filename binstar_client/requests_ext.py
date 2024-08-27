# -*- coding: utf8 -*-
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring

from __future__ import annotations

__all__ = ['NullAuth']

import logging
import typing

from requests.auth import AuthBase

logger = logging.getLogger('binstar.requests_ext')


KeyT = typing.TypeVar('KeyT')
ValueT = typing.TypeVar('ValueT')


def iter_fields(
        fields: typing.Union[typing.Mapping[KeyT, ValueT], typing.Iterable[typing.Tuple[KeyT, ValueT]]],
) -> typing.Iterator[typing.Tuple[KeyT, ValueT]]:
    """Iterate over fields."""
    if isinstance(fields, typing.Mapping):
        return iter(fields.items())
    return iter(fields)


class NullAuth(AuthBase):  # pylint: disable=too-few-public-methods
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
