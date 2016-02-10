'''
Created on Feb 18, 2014

@author: sean
'''
from __future__ import unicode_literals
from binstar_client.scripts.cli import main
from binstar_client.tests.fixture import CLITestCase
from binstar_client.tests.urlmock import urlpatch
import unittest
from mock import patch


class Test(CLITestCase):
    @patch('binstar_client.commands.login.store_token')
    @patch('getpass.getpass')
    @patch('binstar_client.commands.login.input')
    @urlpatch
    def test_login(self, urls, input, getpass, store_token):
        input.return_value = 'test_user'
        getpass.return_value = 'password'

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
    def test_login_compatible(self, urls, input, getpass, store_token):
        input.return_value = 'test_user'
        getpass.return_value = 'password'

        urls.register(path='/authentication-type', status=404)

        auth = urls.register(method='POST', path='/authentications', content='{"token": "a-token"}')
        main(['--show-traceback', 'login'], False)
        self.assertIn('login successful', self.stream.getvalue())

        auth.assertCalled()

        self.assertIn('Authorization', auth.req.headers)
        self.assertIn('Basic ', auth.req.headers['Authorization'])

        self.assertTrue(store_token.called)
        self.assertEqual(store_token.call_args[0][0], 'a-token')

    @patch('binstar_client.commands.login.store_token')
    @urlpatch
    def test_login_kerberos(self, urls, store_token):

        urls.register(path='/authentication-type', content='{"authentication_type": "kerberos"}')

        def update_authentications():
            # The second request should succeed
            auth_success = urls.register(
                method='POST',
                path='/authentications',
                content='{"token": "a-token"}',
                headers={'WWW-Authenticate': 'Negotiate STOKEN'},
            )

        auth_fail = urls.register(method='POST', path='/authentications', status=401, headers={'WWW-Authenticate': 'Negotiate'}, side_effect=update_authentications)

        main(['--show-traceback', 'login'], False)
        self.assertIn('login successful', self.stream.getvalue())

        urls.assertAllCalled()
        self.assertTrue(store_token.called)
        self.assertEqual(store_token.call_args[0][0], 'a-token')


if __name__ == '__main__':
    unittest.main()
