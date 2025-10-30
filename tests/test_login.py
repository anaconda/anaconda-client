# -*- coding: utf8 -*-

"""Tests for authentication commands."""

import unittest
import unittest.mock

from tests.fixture import CLITestCase, main
from tests.urlmock import urlpatch


class Test(CLITestCase):
    """Tests for authentication commands."""

    @unittest.mock.patch('binstar_client.commands.login.store_token')
    @unittest.mock.patch('getpass.getpass')
    @unittest.mock.patch('binstar_client.commands.login.input')
    @unittest.mock.patch('binstar_client.commands.login.LEGACY_INTERACTIVE_LOGIN', True)
    @urlpatch
    def test_login_legacy(self, urls, data, getpass, store_token):
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

    @unittest.mock.patch('binstar_client.commands.login._do_auth_flow')
    @unittest.mock.patch('binstar_client.commands.login.store_token')
    @urlpatch
    def test_login_unified(self, urls, store_token, _do_auth_flow):
        _do_auth_flow.return_value = "dot-com-access-token"

        urls.register(path='/', method='HEAD', status=200)
        well_known = urls.register(
            path='/.well-known/openid-configuration',
            method='GET',
            status=200,
            content='{"authorization_endpoint": "/auth", "token_endpoint": "/token"}',
        )

        auth = urls.register(method='POST', path='/authentications', content='{"token": "a-token"}')
        main(['--show-traceback', 'login'])
        self.assertIn('login successful', self.stream.getvalue())

        well_known.assertCalled()
        auth.assertCalled()

        self.assertIn('Authorization', auth.req.headers)
        self.assertIn('Bearer dot-com-access-token', auth.req.headers['Authorization'])

        self.assertTrue(_do_auth_flow.called)

        self.assertTrue(store_token.called)
        self.assertEqual(store_token.call_args[0][0], 'a-token')

    @unittest.mock.patch('binstar_client.commands.login.store_token')
    @unittest.mock.patch('getpass.getpass')
    @unittest.mock.patch('binstar_client.commands.login.input')
    @unittest.mock.patch('binstar_client.commands.login.LEGACY_INTERACTIVE_LOGIN', True)
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

    @unittest.mock.patch('binstar_client.commands.login._do_auth_flow')
    @unittest.mock.patch('binstar_client.commands.login.store_token')
    @urlpatch
    def test_legacy_login_user_pass_flags(self, urls, store_token, _do_auth_flow):
        urls.register(path='/', method='HEAD', status=200)
        urls.register(path='/authentication-type', status=404)

        auth = urls.register(method='POST', path='/authentications', content='{"token": "a-token"}')
        main(['--show-traceback', 'login', "--username", "test-user", "--password", "test-pass"])
        self.assertIn('login successful', self.stream.getvalue())

        auth.assertCalled()

        self.assertFalse(_do_auth_flow.called)

        self.assertIn('Authorization', auth.req.headers)
        self.assertIn('Basic ', auth.req.headers['Authorization'])

        self.assertTrue(store_token.called)
        self.assertEqual(store_token.call_args[0][0], 'a-token')
