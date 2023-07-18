# -*- coding: utf8 -*-
# pylint: disable=missing-function-docstring

"""Tests for anaconda-client authorizations and token management."""

from binstar_client.errors import BinstarError
from tests.fixture import CLITestCase, main
from tests.urlmock import urlpatch


class Test(CLITestCase):
    """Tests for anaconda-client authorizations and token management."""

    @urlpatch
    def test_remove_token_from_org(self, urls):
        remove_token = urls.register(
            method='DELETE',
            path='/authentications/org/orgname/name/tokenname',
            content='{"token": "a-token"}',
            status=201
        )
        main(['--show-traceback', 'auth', '--remove', 'tokenname', '-o', 'orgname'])
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
        main(['--show-traceback', 'auth', '--remove', 'tokenname'])
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
            main(['--show-traceback', 'auth', '--remove', 'tokenname', '-o', 'wrong_org'])

        remove_token.assertCalled()
