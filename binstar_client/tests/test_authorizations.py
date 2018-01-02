from __future__ import unicode_literals
from binstar_client.scripts.cli import main
from binstar_client.tests.fixture import CLITestCase
from binstar_client.tests.urlmock import urlpatch
from binstar_client.errors import BinstarError
import unittest
from mock import patch


class Test(CLITestCase):
    @urlpatch
    def test_remove_token_from_org(self, urls):
        remove_token = urls.register(
            method='DELETE',
            path='/authentications/org/orgname/name/tokenname',
            content='{"token": "a-token"}',
            status=201
        )
        main(['--show-traceback', 'auth', '--remove', 'tokenname', '-o', 'orgname'], False)
        self.assertIn('Removed token tokenname', self.stream.getvalue())

        remove_token.assertCalled()

    @urlpatch
    def test_remove_token(self, urls):
        remove_token = urls.register(
            method='DELETE',
            path='/authentications/name/tokenname',
            content='{"token": "a-token"}',
            status=201
        )
        main(['--show-traceback', 'auth', '--remove', 'tokenname'], False)
        self.assertIn('Removed token tokenname', self.stream.getvalue())

        remove_token.assertCalled()


    @urlpatch
    def test_remove_token_forbidden(self, urls):
        remove_token = urls.register(
            method='DELETE',
            path='/authentications/org/wrong_org/name/tokenname',
            content='{"token": "a-token"}',
            status=403
        )
        with self.assertRaises(BinstarError):
            main(['--show-traceback', 'auth', '--remove', 'tokenname', '-o', 'wrong_org'], False)

        remove_token.assertCalled()


if __name__ == '__main__':
    unittest.main()
