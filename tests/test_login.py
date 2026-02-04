# -*- coding: utf8 -*-

"""Tests for authentication commands."""

import json
import unittest.mock

from binstar_client import errors

from tests.fixture import CLITestCase, main
from tests.urlmock import urlpatch
from tests.utils.utils import data_dir


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

    @unittest.mock.patch('binstar_client.commands.login.get_config')
    @unittest.mock.patch('binstar_client.utils.config.get_config')
    @unittest.mock.patch('binstar_client.utils.config.load_token')
    @unittest.mock.patch('binstar_client.commands.login._do_auth_flow')
    @unittest.mock.patch('binstar_client.commands.login.store_token')
    @urlpatch
    def test_login_unified(self, urls, store_token, _do_auth_flow, load_token, get_config, get_config2):
        get_config.return_value = {
            "site": {"mocked": {"url": "https://api.mocked"}},
            "auto_register": True,
            "default_site": "mocked",
            "url": "https://api.mocked",
            "ssl_verify": True,
            "verify_ssl": True,
        }
        get_config2.return_value = get_config.return_value

        load_token.return_value = None
        _do_auth_flow.return_value = "dot-com-access-token"

        urls.register(path='/', method='HEAD', status=200)
        well_known = urls.register(
            path='/.well-known/openid-configuration',
            method='GET',
            status=200,
            content='{"authorization_endpoint": "https://auth.unified/auth", "token_endpoint": "https://auth.unified/token"}',
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
        self.assertIn('Username/password login is deprecated', self.stream.getvalue())

        auth.assertCalled()

        self.assertFalse(_do_auth_flow.called)

        self.assertIn('Authorization', auth.req.headers)
        self.assertIn('Basic ', auth.req.headers['Authorization'])

        self.assertTrue(store_token.called)
        self.assertEqual(store_token.call_args[0][0], 'a-token')

    @unittest.mock.patch('binstar_client.commands.login.bool_input')
    @unittest.mock.patch('binstar_client.commands.login._do_auth_flow')
    @urlpatch
    @unittest.skip("Cannot accurately test this scenario")
    def test_login_required_args(self, urls, _do_auth_flow, bool_input):
        org_data = {
            "company": "foo",
            "created_at": "2015-11-19 18:22:23.061000+00:00",
            "description": "",
            "location": "here",
            "login": "org-name",
            "name": "Me",
            "url": "",
            "user_type": "org",
        }

        urls.register(method='HEAD', path='/', status=200)
        urls.register(method='GET', path='/user/org-name', content=json.dumps(org_data))
        urls.register(method="GET", path="/dist/org-name/foo/0.1/osx-64/foo-0.1-0.tar.bz2", status=401, content={})

        # We just need make sure we get past the legacy_flag determination
        # We don't need to finish login or upload
        bool_input.return_value = False

        with self.assertRaises(SystemExit):
            main(['--show-traceback', 'upload', "-u", "org-name", data_dir('foo-0.1-0.tar.bz2')])

        self.assertIn("\"org-name\" as upload username", self.stream.getvalue())
        self.assertIn("The action you are performing requires authentication", self.stream.getvalue())
