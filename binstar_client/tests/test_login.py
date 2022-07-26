# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
from __future__ import unicode_literals

# Third party imports
from unittest.mock import patch

# Local imports
from binstar_client.scripts.cli import main
from binstar_client.tests.fixture import CLITestCase
from binstar_client.tests.urlmock import urlpatch


# Standard library imports


class Test(CLITestCase):
    @patch('binstar_client.commands.login.store_token')
    @patch('getpass.getpass')
    @patch('binstar_client.commands.login.input')
    @urlpatch
    def test_login(self, urls, data, getpass, store_token):
        data.return_value = 'test_user'
        getpass.return_value = 'password'

        urls.register(path='/', method='HEAD', status=200)
        urls.register(path='/authentication-type', content='{"authentication_type": "password"}')

        auth = urls.register(method='POST', path='/authentications', content='{"token": "a-token"}')
        main(['--show-traceback', 'login'], False)
        self.assertIn('login successful', self.stream.getvalue())

        auth.assertCalled()

        self.assertIn('Authorization', auth.req.headers)
        self.assertIn('Basic ', auth.req.headers['Authorization'])

        self.assertTrue(store_token.called)
        self.assertEqual(store_token.call_args[0][0], 'a-token')

    @patch('binstar_client.commands.login.store_token')
    @patch('getpass.getpass')
    @patch('binstar_client.commands.login.input')
    @urlpatch
    def test_login_compatible(self, urls, data, getpass, store_token):
        data.return_value = 'test_user'
        getpass.return_value = 'password'

        urls.register(path='/', method='HEAD', status=200)
        urls.register(path='/authentication-type', status=404)

        auth = urls.register(method='POST', path='/authentications', content='{"token": "a-token"}')
        main(['--show-traceback', 'login'], False)
        self.assertIn('login successful', self.stream.getvalue())

        auth.assertCalled()

        self.assertIn('Authorization', auth.req.headers)
        self.assertIn('Basic ', auth.req.headers['Authorization'])

        self.assertTrue(store_token.called)
        self.assertEqual(store_token.call_args[0][0], 'a-token')
