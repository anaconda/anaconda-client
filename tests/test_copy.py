# -*- coding: utf8 -*-
# pylint: disable=missing-function-docstring

"""Tests for package copy operations."""

import json

from binstar_client.errors import Conflict
from tests.urlmock import urlpatch
from tests.fixture import CLITestCase, main


class Test(CLITestCase):
    """Tests for package copy operations."""

    @urlpatch
    def test_copy_label(self, urls):
        urls.register(method='GET', path='/channels/u1', content='["dev"]')
        copy = urls.register(
            method='POST', path='/copy/package/u1/p1/1.0/', content='[{"basename": "copied-file_1.0.tgz"}]')

        main(['--show-traceback', 'copy', '--from-label', 'dev', '--to-label', 'release/xyz', 'u1/p1/1.0'])

        urls.assertAllCalled()
        req = json.loads(copy.req.body)
        self.assertEqual(req['from_channel'], 'dev')
        self.assertEqual(req['to_channel'], 'release/xyz')

    @urlpatch
    def test_copy_replace(self, urls):
        urls.register(method='GET', path='/channels/u1', content='["dev"]')
        copy = urls.register(
            method='PUT', path='/copy/package/u1/p1/1.0/', content='[{"basename": "copied-file_1.0.tgz"}]')

        main(['--show-traceback', 'copy', '--from-label', 'dev', '--to-label', 'release/xyz', 'u1/p1/1.0', '--replace'])

        urls.assertAllCalled()
        req = json.loads(copy.req.body)
        self.assertEqual(req['from_channel'], 'dev')
        self.assertEqual(req['to_channel'], 'release/xyz')

    @urlpatch
    def test_copy_update(self, urls):
        urls.register(method='GET', path='/channels/u1', content='["dev"]')
        copy = urls.register(
            method='PATCH', path='/copy/package/u1/p1/1.0/', content='[{"basename": "copied-file_1.0.tgz"}]')

        main(['--show-traceback', 'copy', '--from-label', 'dev', '--to-label', 'release/xyz', 'u1/p1/1.0', '--update'])

        urls.assertAllCalled()
        req = json.loads(copy.req.body)
        self.assertEqual(req['from_channel'], 'dev')
        self.assertEqual(req['to_channel'], 'release/xyz')

    @urlpatch
    def test_copy_file_conflict(self, urls):
        urls.register(method='GET', path='/channels/u1', content='["dev"]')
        copy = urls.register(
            method='POST', path='/copy/package/u1/p1/1.0/', status=409
        )
        with self.assertRaises(Conflict):
            main(['--show-traceback', 'copy', '--from-label', 'dev', '--to-label', 'release/xyz', 'u1/p1/1.0'])

        urls.assertAllCalled()
        req = json.loads(copy.req.body)
        self.assertEqual(req['from_channel'], 'dev')
        self.assertEqual(req['to_channel'], 'release/xyz')

    @urlpatch
    def test_copy_argument_error(self, urls):
        urls.register(method='GET', path='/channels/u1', content='["dev"]')
        with self.assertRaises(SystemExit):
            main([
                '--show-traceback', 'copy', '--from-label', 'dev',
                '--to-label', 'release/xyz', 'u1/p1/1.0', '--update', '--replace',
            ])
