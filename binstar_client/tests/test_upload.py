'''
Created on Feb 18, 2014

@author: sean
'''
from __future__ import unicode_literals
from binstar_client.scripts.cli import main
from binstar_client.tests.fixture import CLITestCase
from binstar_client.tests.urlmock import urlpatch
import unittest
from binstar_client import errors

class Test(CLITestCase):

    @urlpatch
    def test_upload_bad_package(self, registry):

        registry.register(method='GET', path='/user', content='{"login": "eggs"}')
        registry.register(method='GET', path='/package/eggs/foo', content='{}', status=404)
        registry.register(method='POST', path='/package/eggs/foo', content='{}', status=200)
        registry.register(method='GET', path='/release/eggs/foo/0.1', content='{}')
        registry.register(method='GET', path='/dist/eggs/foo/0.1/osx-64/foo-0.1-0.tar.bz2', status=404, content='{}')

        content = {"post_url": "http://s3_url.com/s3_url", "form_data": {}, "dist_id": "dist_id"}
        registry.register(method='POST', path='/stage/eggs/foo/0.1/osx-64/foo-0.1-0.tar.bz2', content=content)

        registry.register(method='POST', path='/s3_url', status=201)
        registry.register(method='POST', path='/commit/eggs/foo/0.1/osx-64/foo-0.1-0.tar.bz2', status=200, content={})

        main(['--show-traceback', 'upload', self.data_dir('foo-0.1-0.tar.bz2')], False)

        registry.assertAllCalled()


    @urlpatch
    def test_upload_bad_package_no_register(self, registry):

        registry.register(method='GET', path='/user', content='{"login": "eggs"}')
        registry.register(method='GET', path='/package/eggs/foo', status=404)

        with self.assertRaises(errors.UserError):
            main(['--show-traceback', 'upload', '--no-register', self.data_dir('foo-0.1-0.tar.bz2')], False)

        registry.assertAllCalled()

    @urlpatch
    def test_upload_conda(self, registry):

        registry.register(method='GET', path='/user', content='{"login": "eggs"}')
        registry.register(method='GET', path='/package/eggs/foo', content='{}')
        registry.register(method='GET', path='/release/eggs/foo/0.1', content='{}')
        registry.register(method='GET', path='/dist/eggs/foo/0.1/osx-64/foo-0.1-0.tar.bz2', status=404, content='{}')

        content = {"post_url": "http://s3_url.com/s3_url", "form_data": {}, "dist_id": "dist_id"}
        registry.register(method='POST', path='/stage/eggs/foo/0.1/osx-64/foo-0.1-0.tar.bz2', content=content)

        registry.register(method='POST', path='/s3_url', status=201)
        registry.register(method='POST', path='/commit/eggs/foo/0.1/osx-64/foo-0.1-0.tar.bz2', status=200, content={})

        main(['--show-traceback', 'upload', self.data_dir('foo-0.1-0.tar.bz2')], False)

        registry.assertAllCalled()

    @urlpatch
    def test_upload_pypi(self, registry):

        registry.register(method='GET', path='/user', content='{"login": "eggs"}')
        registry.register(method='GET', path='/package/eggs/test-package34', content='{}')
        registry.register(method='GET', path='/release/eggs/test-package34/0.3.1', content='{}')
        registry.register(method='GET', path='/dist/eggs/test-package34/0.3.1/test_package34-0.3.1.tar.gz', status=404, content='{}')

        content = {"post_url": "http://s3_url.com/s3_url", "form_data": {}, "dist_id": "dist_id"}
        registry.register(method='POST', path='/stage/eggs/test-package34/0.3.1/test_package34-0.3.1.tar.gz', content=content)

        registry.register(method='POST', path='/s3_url', status=201)
        registry.register(method='POST', path='/commit/eggs/test-package34/0.3.1/test_package34-0.3.1.tar.gz', status=200, content={})

        main(['--show-traceback', 'upload', self.data_dir('test_package34-0.3.1.tar.gz')], False)

        registry.assertAllCalled()

    @urlpatch
    def test_upload_file(self, registry):
        registry.register(method='GET', path='/user', content='{"login": "eggs"}')
        registry.register(method='GET', path='/package/eggs/test-package34', content='{}')
        registry.register(method='GET', path='/release/eggs/test-package34/0.3.1', content='{}')
        registry.register(method='GET', path='/dist/eggs/test-package34/0.3.1/test_package34-0.3.1.tar.gz', status=404, content='{}')

        content = {"post_url": "http://s3_url.com/s3_url", "form_data": {}, "dist_id": "dist_id"}
        registry.register(method='POST', path='/stage/eggs/test-package34/0.3.1/test_package34-0.3.1.tar.gz', content=content)

        registry.register(method='POST', path='/s3_url', status=201)
        registry.register(method='POST', path='/commit/eggs/test-package34/0.3.1/test_package34-0.3.1.tar.gz', status=200, content={})

        main(['--show-traceback', 'upload',
              '--package-type', 'file',
              '--package', 'test-package34',
              '--version', '0.3.1',
              self.data_dir('test_package34-0.3.1.tar.gz')], False)

        registry.assertAllCalled()

if __name__ == '__main__':
    unittest.main()
