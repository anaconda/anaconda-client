# -*- coding: utf8 -*-
# pylint: disable=missing-function-docstring

"""Tests for whoami command."""

import json
import os
import unittest.mock

import requests.utils

from tests.fixture import CLITestCase, main
from tests.urlmock import urlpatch
from tests.utils.utils import data_dir


class Test(CLITestCase):
    """Tests for whoami command."""

    @urlpatch
    def test_whoami_anon(self, urls):
        user = urls.register(method='GET', path='/user', status=401)
        main(['--show-traceback', 'whoami'])
        self.assertIn('Anonymous User', self.stream.getvalue())

        user.assertCalled()

    @urlpatch
    def test_whoami(self, urls):
        content = json.dumps({'login': 'eggs', 'created_at': '1/2/2000'})
        user = urls.register(method='GET', path='/user', content=content)

        main(['--show-traceback', 'whoami'])
        self.assertIn('eggs', self.stream.getvalue())

        user.assertCalled()

    @urlpatch
    def test_netrc_ignored(self, urls):
        # Disable token authentication
        self.load_token.return_value = None
        os.environ.pop('BINSTAR_API_TOKEN', None)
        os.environ.pop('ANACONDA_API_TOKEN', None)

        # requests.get_netrc_auth uses expanduser to find the netrc file, point to our test file
        expanduser = unittest.mock.Mock(return_value=data_dir('netrc'))
        with unittest.mock.patch('os.path.expanduser', expanduser):
            auth = requests.utils.get_netrc_auth('http://localhost', raise_errors=True)
        self.assertEqual(auth, ('anonymous', 'pass'))

        user = urls.register(path='/user', status=401)

        main(['--show-traceback', 'whoami'])

        # Not called because token is missing.
        user.assertNotCalled()
        self.assertIsNone(user.req)
