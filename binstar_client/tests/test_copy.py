from __future__ import unicode_literals
# Standard library imports
import json
import unittest

# Local imports
from binstar_client.errors import Conflict
from binstar_client.scripts.cli import main
from binstar_client.tests.urlmock import urlpatch
from binstar_client.tests.fixture import CLITestCase


class Test(CLITestCase):
    @urlpatch
    def test_copy_label(self, urls):
        urls.register(method='GET', path='/channels/u1', content='["dev"]')
        copy = urls.register(
            method='POST', path='/copy/package/u1/p1/1.0/', content='[{"basename": "copied-file_1.0.tgz"}]')

        main(['--show-traceback', 'copy', '--from-label', 'dev', '--to-label', 'release/xyz', 'u1/p1/1.0'], False)

        urls.assertAllCalled()
        req = json.loads(copy.req.body)
        self.assertEqual(req['from_channel'], 'dev')
        self.assertEqual(req['to_channel'], 'release/xyz')

    @urlpatch
    def test_copy_replace(self, urls):
        urls.register(method='GET', path='/channels/u1', content='["dev"]')
        copy = urls.register(
            method='PUT', path='/copy/package/u1/p1/1.0/', content='[{"basename": "copied-file_1.0.tgz"}]')

        main(
            ['--show-traceback', 'copy', '--from-label', 'dev', '--to-label', 'release/xyz', 'u1/p1/1.0', '--replace'],
            False)

        urls.assertAllCalled()
        req = json.loads(copy.req.body)
        self.assertEqual(req['from_channel'], 'dev')
        self.assertEqual(req['to_channel'], 'release/xyz')

    @urlpatch
    def test_copy_update(self, urls):
        urls.register(method='GET', path='/channels/u1', content='["dev"]')
        copy = urls.register(
            method='PATCH', path='/copy/package/u1/p1/1.0/', content='[{"basename": "copied-file_1.0.tgz"}]')

        main(['--show-traceback', 'copy', '--from-label', 'dev', '--to-label', 'release/xyz', 'u1/p1/1.0', '--update'],
             False)

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
            main(['--show-traceback', 'copy', '--from-label', 'dev', '--to-label', 'release/xyz', 'u1/p1/1.0'], False)

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
                '--to-label', 'release/xyz', 'u1/p1/1.0', '--update', '--replace'], False)


if __name__ == '__main__':
    unittest.main()
