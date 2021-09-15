from __future__ import unicode_literals

import json

from binstar_client import errors
from binstar_client.scripts.cli import main
from binstar_client.tests.fixture import CLITestCase
from binstar_client.tests.urlmock import urlpatch
from binstar_client.utils.test.utils import data_dir


with open(data_dir('metadata.json'), 'r') as f:
    json_test_data = json.load(f)


package_test_data = {
    'public_attrs': {
        'license': 'custom',
        'name': 'test-package34',
        'summary': 'Python test package for binstar client'
    }
}
release_test_data = {
    'public_attrs': {
        'description': 'longer description of the package',
        'home_page': 'http://github.com/binstar/binstar_pypi',
        'version': '0.3.1'
    }
}


class TestUpdate(CLITestCase):

    @urlpatch
    def test_update_package_from_json(self, urls):
        urls.register(method='HEAD', path='/', status=200)
        update = urls.register(method='PATCH', path='/package/owner/package_name', content=json_test_data, status=200)
        main(['update', 'owner/package_name', data_dir('metadata.json')], False)

        urls.assertAllCalled()
        req = json.loads(update.req.body)
        self.assertEqual(req, json_test_data)

    @urlpatch
    def test_update_package_from_file(self, urls):
        urls.register(method='HEAD', path='/', status=200)
        update = urls.register(method='PATCH', path='/package/owner/package_name',
                               content=package_test_data, status=200)
        main(['update', 'owner/package_name', data_dir('test_package34-0.3.1.tar.gz')], False)

        urls.assertAllCalled()
        req = json.loads(update.req.body)
        self.assertEqual(req, package_test_data)

    @urlpatch
    def test_update_release_from_json(self, urls):
        urls.register(method='HEAD', path='/', status=200)
        update = urls.register(method='PATCH', path='/release/owner/package_name/1.0.0',
                               content=json_test_data, status=200)
        main(['update', 'owner/package_name/1.0.0', data_dir('metadata.json'), '--release'], False)

        urls.assertAllCalled()
        req = json.loads(update.req.body)
        self.assertEqual(req, json_test_data)

    @urlpatch
    def test_update_release_from_file(self, urls):
        urls.register(method='HEAD', path='/', status=200)
        update = urls.register(method='PATCH', path='/release/owner/package_name/1.0.0',
                               content=release_test_data, status=200)
        main(['update', 'owner/package_name/1.0.0', data_dir('test_package34-0.3.1.tar.gz'), '--release'], False)

        urls.assertAllCalled()
        req = json.loads(update.req.body)
        self.assertEqual(req, release_test_data)

    @urlpatch
    def test_update_local_file_not_found(self, urls):
        urls.register(method='HEAD', path='/', status=200)
        urls.register(method='PATCH', path='/package/owner/package_name', content=package_test_data, status=404)

        with self.assertRaises(SystemExit):
            main(['update', 'owner/package_name', data_dir('not_existing.tar.gz')], False)

    @urlpatch
    def test_update_package_not_found(self, urls):
        urls.register(method='HEAD', path='/', status=200)
        urls.register(method='PATCH', path='/package/owner/package_name', content=package_test_data, status=404)

        with self.assertRaises(errors.NotFound):
            main(['update', 'owner/package_name', data_dir('test_package34-0.3.1.tar.gz')], False)

    @urlpatch
    def test_update_release_missing_version(self, urls):
        urls.register(method='HEAD', path='/', status=200)
        urls.register(method='PATCH', path='/release/owner/package_name/1.0.0', content=package_test_data, status=200)
        with self.assertRaises(errors.UserError):
            main(['update', 'owner/package_name', data_dir('test_package34-0.3.1.tar.gz'), '--release'], False)

    @urlpatch
    def test_update_release_not_found(self, urls):
        urls.register(method='HEAD', path='/', status=200)
        urls.register(method='PATCH', path='/release/owner/package_name/1.0.0', content=package_test_data, status=404)

        with self.assertRaises(errors.NotFound):
            main(['update', 'owner/package_name/1.0.0', data_dir('test_package34-0.3.1.tar.gz'), '--release'], False)
