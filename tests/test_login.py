# -*- coding: utf8 -*-
# pylint: disable=missing-function-docstring

"""Tests for authentication commands."""

import unittest.mock

from tests.fixture import CLITestCase, main
from tests.urlmock import urlpatch


class Test(CLITestCase):
    """Tests for authentication commands."""

    @unittest.mock.patch('binstar_client.commands.login.store_token')
    @unittest.mock.patch('getpass.getpass')
    @unittest.mock.patch('binstar_client.commands.login.input')
    @urlpatch
    def test_login(self, urls, data, getpass, store_token):
        data.return_value = 'test_user'
        getpass.return_value = 'password'

        urls.register(path='/', method='HEAD', status=200)
        urls.register(path='/authentication-type', content='{"authentication_type": "password"}')

        auth = urls.register(method='POST', path='/authentications', content='{"token": "a-token"}')
        main(['--show-traceback', 'login'])
        self.assertIn('login successful', self.stream.getvalue())

        auth.assertCalled()

        self.assertIn('Authorization', auth.req.headers)
        self.assertIn('Basic ', auth.req.headers['Authorization'])

        self.assertTrue(store_token.called)
        self.assertEqual(store_token.call_args[0][0], 'a-token')

    @unittest.mock.patch('binstar_client.commands.login.store_token')
    @unittest.mock.patch('getpass.getpass')
    @unittest.mock.patch('binstar_client.commands.login.input')
    @urlpatch
    def test_login_compatible(self, urls, data, getpass, store_token):
        data.return_value = 'test_user'
        getpass.return_value = 'password'

        urls.register(path='/', method='HEAD', status=200)
        urls.register(path='/authentication-type', status=404)

        auth = urls.register(method='POST', path='/authentications', content='{"token": "a-token"}')
        main(['--show-traceback', 'login'])
        self.assertIn('login successful', self.stream.getvalue())

        auth.assertCalled()

        self.assertIn('Authorization', auth.req.headers)
        self.assertIn('Basic ', auth.req.headers['Authorization'])

        self.assertTrue(store_token.called)
        self.assertEqual(store_token.call_args[0][0], 'a-token')
