import logging
from unittest import mock

import requests

from binstar_client import Binstar


def _response(headers):
    res = requests.Response()
    res.status_code = 200
    res.headers.update(headers)
    res.request = requests.Request('GET', 'https://api.example.com/download/u/p/1/f').prepare()
    return res


def _download(headers):
    api = Binstar(domain='https://api.example.com')
    with mock.patch.object(api.session, 'get', return_value=_response(headers)):
        api.download('u', 'p', '1', 'f')


def test_download_warns_on_deprecation(caplog):
    with caplog.at_level(logging.WARNING, logger='binstar'):
        _download({
            'Deprecation': 'true',
            'Sunset': 'Sat, 01 May 2027 00:00:00 GMT',
            'Link': '<https://conda.example.com/u/linux-64/f>; rel="successor-version"',
        })
    assert 'deprecated' in caplog.text
    assert 'Sat, 01 May 2027' in caplog.text
    assert 'https://conda.example.com/u/linux-64/f' in caplog.text


def test_download_no_warning_without_header(caplog):
    with caplog.at_level(logging.WARNING, logger='binstar'):
        _download({})
    assert 'deprecated' not in caplog.text
