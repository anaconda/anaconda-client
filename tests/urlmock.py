# pylint: disable=too-many-arguments,invalid-name,missing-module-docstring,missing-class-docstring
# pylint: disable=missing-function-docstring

"""
Created on Feb 22, 2014

@author: sean
"""

from __future__ import unicode_literals

import json
from collections import namedtuple
from functools import wraps

import requests

Rule = namedtuple(
    'Rule', ('url', 'path', 'method', 'status', 'content', 'side_effect', 'res', 'headers', 'expected_headers'))


class Responses:
    def __init__(self):
        self._resps = []

    def append(self, res):
        self._resps.append(res)

    @property
    def called(self):
        return len(self._resps)

    @property
    def req(self):  # pylint: disable=inconsistent-return-statements
        if self._resps:
            return self._resps[0][1]

    def assertCalled(self, url=''):
        assert self.called, 'The url %s was not called' % url  # nosec

    def assertNotCalled(self, url=''):
        assert not self.called, 'The url %s was called' % url  # nosec


class Registry:
    def __init__(self):
        self._map = []

    def __enter__(self):
        self.real_send = requests.Session.send  # pylint: disable=attribute-defined-outside-init
        requests.Session.send = self.mock_send

        return self

    def __exit__(self, *exec_info):
        requests.Session.send = self.real_send

    @staticmethod
    def filter_request(rule, prepared_request):
        if rule.url and rule.url != prepared_request.url:
            return False

        if rule.path and rule.path != prepared_request.path_url:
            return False

        if rule.method and rule.method != prepared_request.method:
            return False

        return True

    def find_rule(self, prepared_request):
        return next((stored_rule for stored_rule in self._map[::-1]
                     if self.filter_request(stored_rule, prepared_request)), None)

    def mock_send(self, prepared_request, *args, **kwargs):  # pylint: disable=unused-argument

        rule = self.find_rule(prepared_request)

        if rule is None:
            raise Exception(  # pylint: disable=broad-exception-raised
                'No matching rule found for url [%s] %s' % (prepared_request.method, prepared_request.url),
            )

        if rule.expected_headers:
            for header, value in rule.expected_headers.items():
                if header not in prepared_request.headers:
                    raise Exception(  # pylint: disable=broad-exception-raised
                        '{}: header {} expected in {}'.format(prepared_request.url, header, prepared_request.headers),
                    )

                if prepared_request.headers[header] != value:
                    raise Exception(  # pylint: disable=broad-exception-raised
                        '{}: header {} has unexpected value {} was expecting {}'.format(
                            prepared_request.url, header, prepared_request.headers[header], value,
                        ),
                    )

        content = rule.content
        if isinstance(content, dict):
            content = json.dumps(content)
        if isinstance(content, str):
            content = content.encode()

        res = requests.models.Response()
        res.status_code = rule.status
        res._content_consumed = True  # pylint: disable=protected-access
        res._content = content  # pylint: disable=protected-access
        res.encoding = 'utf-8'
        res.request = prepared_request
        res.headers.update(rule.headers or {})
        rule.res.append((res, prepared_request))

        if rule.side_effect:
            rule.side_effect()

        return res

    def register(self, url=None, path=None, method='GET', status=200, content=b'',
                 side_effect=None, headers=None, expected_headers=None):
        res = Responses()
        self._map.append(Rule(url, path, method, status, content, side_effect, res, headers, expected_headers))
        return res

    def unregister(self, res):
        for item in list(self._map):
            if res == item.res:
                self._map.remove(item)
                return

    def assertAllCalled(self):
        for item in self._map:
            res = item.res
            res.assertCalled('[%s] %s%s' % (item.method or 'any', item.url or 'http://<any>', item.path))


def urlpatch(func):
    @wraps(func)
    def inner(self, *args, **kwargs):
        with Registry() as registry:
            return func(self, registry, *args, **kwargs)

    return inner
