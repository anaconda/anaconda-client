from __future__ import unicode_literals

import unittest

from mock import patch

from binstar_client import errors
from binstar_client.scripts.cli import main
from binstar_client.tests.fixture import CLITestCase
from binstar_client.tests.urlmock import urlpatch
from binstar_client.utils.test.utils import data_dir


class Test(CLITestCase):
    @urlpatch
    def test_upload_bad_package(self, registry):
        registry.register(method='HEAD', path='/', status=200)
        registry.register(method='GET', path='/user', content='{"login": "eggs"}')
        registry.register(method='GET', path='/package/eggs/foo', content='{}', status=404)
        content = {"package_types": ['conda']}
        registry.register(method='POST', path='/package/eggs/foo', content=content, status=200)
        registry.register(method='GET', path='/release/eggs/foo/0.1', content='{}')
        registry.register(method='GET', path='/dist/eggs/foo/0.1/osx-64/foo-0.1-0.tar.bz2', status=404, content='{}')

        content = {"post_url": "http://s3url.com/s3_url", "form_data": {}, "dist_id": "dist_id"}
        registry.register(method='POST', path='/stage/eggs/foo/0.1/osx-64/foo-0.1-0.tar.bz2', content=content)

        registry.register(method='POST', path='/s3_url', status=201)
        registry.register(method='POST', path='/commit/eggs/foo/0.1/osx-64/foo-0.1-0.tar.bz2', status=200, content={})
        main(['--show-traceback', 'upload', data_dir('foo-0.1-0.tar.bz2')], False)
        registry.assertAllCalled()


    @urlpatch
    def test_upload_bad_package_no_register(self, registry):
        registry.register(method='HEAD', path='/', status=200)
        registry.register(method='GET', path='/user', content='{"login": "eggs"}')
        registry.register(method='GET', path='/package/eggs/foo', status=404)

        with self.assertRaises(errors.UserError):
            main(['--show-traceback', 'upload', '--no-register', data_dir('foo-0.1-0.tar.bz2')], False)

        registry.assertAllCalled()

    @urlpatch
    def test_upload_conda(self, registry):
        registry.register(method='HEAD', path='/', status=200)
        registry.register(method='GET', path='/user', content='{"login": "eggs"}')
        content = {'package_types': ['conda']}
        registry.register(method='GET', path='/package/eggs/foo', content=content)
        registry.register(method='GET', path='/release/eggs/foo/0.1', content='{}')
        registry.register(method='GET', path='/dist/eggs/foo/0.1/osx-64/foo-0.1-0.tar.bz2', status=404, content='{}')

        content = {"post_url": "http://s3url.com/s3_url", "form_data": {}, "dist_id": "dist_id"}
        registry.register(method='POST', path='/stage/eggs/foo/0.1/osx-64/foo-0.1-0.tar.bz2', content=content)

        registry.register(method='POST', path='/s3_url', status=201)
        registry.register(method='POST', path='/commit/eggs/foo/0.1/osx-64/foo-0.1-0.tar.bz2', status=200, content={})

        main(['--show-traceback', 'upload', data_dir('foo-0.1-0.tar.bz2')], False)

        registry.assertAllCalled()

    @urlpatch
    def test_upload_pypi(self, registry):
        registry.register(method='HEAD', path='/', status=200)
        registry.register(method='GET', path='/user', content='{"login": "eggs"}')
        content = {'package_types': 'pypi'}
        registry.register(method='GET', path='/package/eggs/test-package34', content=content)
        registry.register(method='GET', path='/release/eggs/test-package34/0.3.1', content='{}')
        registry.register(method='GET', path='/dist/eggs/test-package34/0.3.1/test_package34-0.3.1.tar.gz', status=404, content='{}')

        content = {"post_url": "http://s3url.com/s3_url", "form_data": {}, "dist_id": "dist_id"}
        registry.register(method='POST', path='/stage/eggs/test-package34/0.3.1/test_package34-0.3.1.tar.gz', content=content)

        registry.register(method='POST', path='/s3_url', status=201)
        registry.register(method='POST', path='/commit/eggs/test-package34/0.3.1/test_package34-0.3.1.tar.gz', status=200, content={})

        main(['--show-traceback', 'upload', data_dir('test_package34-0.3.1.tar.gz')], False)

        registry.assertAllCalled()

    @urlpatch
    def test_upload_file(self, registry):
        registry.register(method='HEAD', path='/', status=200)
        registry.register(method='GET', path='/user', content='{"login": "eggs"}')
        content = {'package_types': ['file']}
        registry.register(method='GET', path='/package/eggs/test-package34', content=content)
        registry.register(method='GET', path='/release/eggs/test-package34/0.3.1', content='{}')
        registry.register(method='GET', path='/dist/eggs/test-package34/0.3.1/test_package34-0.3.1.tar.gz', status=404, content='{}')

        content = {"post_url": "http://s3url.com/s3_url", "form_data": {}, "dist_id": "dist_id"}
        registry.register(method='POST', path='/stage/eggs/test-package34/0.3.1/test_package34-0.3.1.tar.gz', content=content)

        registry.register(method='POST', path='/s3_url', status=201)
        registry.register(method='POST', path='/commit/eggs/test-package34/0.3.1/test_package34-0.3.1.tar.gz', status=200, content={})

        main(['--show-traceback', 'upload',
            '--package-type', 'file',
            '--package', 'test-package34',
            '--version', '0.3.1',
            data_dir('test_package34-0.3.1.tar.gz')], False)

        registry.assertAllCalled()

    @urlpatch
    def test_upload_project(self, registry):
        # there's redundant work between anaconda-client which
        # checks auth and anaconda-project also checks auth;
        # -project has no way to know it was already checked :-/
        registry.register(method='HEAD', path='/', status=200)
        registry.register(method='GET', path='/user/eggs', content='{"login": "eggs"}')
        registry.register(method='GET', path='/user', content='{"login": "eggs"}')
        registry.register(method='GET', path='/apps/eggs/projects/dog', content='{}')
        stage_content = '{"post_url":"http://s3url.com/s3_url", "form_data":{"foo":"bar"}, "dist_id":"dist42"}'
        registry.register(method='POST', path='/apps/eggs/projects/dog/stage',
                          content=stage_content)
        registry.register(method='POST', path='/s3_url', status=201)
        registry.register(method='POST', path='/apps/eggs/projects/dog/commit/dist42', content='{}')

        main(['--show-traceback', 'upload',
              '--package-type', 'project',
              data_dir('bar')], False)

        registry.assertAllCalled()

    @urlpatch
    def test_upload_notebook_as_project(self, registry):
        registry.register(method='HEAD', path='/', status=200)
        registry.register(method='GET', path='/user/eggs', content='{"login": "eggs"}')
        registry.register(method='GET', path='/user', content='{"login": "eggs"}')
        registry.register(method='GET', path='/apps/eggs/projects/foo', content='{}')
        stage_content = '{"post_url":"http://s3url.com/s3_url", "form_data":{"foo":"bar"}, "dist_id":"dist42"}'
        registry.register(method='POST', path='/apps/eggs/projects/foo/stage',
                          content=stage_content)
        registry.register(method='POST', path='/s3_url', status=201)
        registry.register(method='POST', path='/apps/eggs/projects/foo/commit/dist42', content='{}')

        main(['--show-traceback', 'upload',
              '--package-type', 'project',
              data_dir('foo.ipynb')], False)

        registry.assertAllCalled()

    @urlpatch
    def test_upload_project_specifying_user(self, registry):
        registry.register(method='HEAD', path='/', status=200)
        registry.register(method='GET', path='/user/alice', content='{"login": "alice"}')
        registry.register(method='GET', path='/apps/alice/projects/dog', content='{}')
        stage_content = '{"post_url":"http://s3url.com/s3_url", "form_data":{"foo":"bar"}, "dist_id":"dist42"}'
        registry.register(method='POST', path='/apps/alice/projects/dog/stage',
                          content=stage_content)
        registry.register(method='POST', path='/s3_url', status=201)
        registry.register(method='POST', path='/apps/alice/projects/dog/commit/dist42', content='{}')

        main(['--show-traceback', 'upload',
              '--package-type', 'project',
              '--user', 'alice',
              data_dir('bar')], False)

        registry.assertAllCalled()


    @urlpatch
    def test_upload_project_specifying_token(self, registry):
        registry.register(method='HEAD', path='/', status=200)
        registry.register(method='GET', path='/user/eggs', content='{"login": "eggs"}',
                          expected_headers={'Authorization':'token abcdefg'})
        registry.register(method='GET', path='/user', content='{"login": "eggs"}')
        registry.register(method='GET', path='/apps/eggs/projects/dog', content='{}')
        stage_content = '{"post_url":"http://s3url.com/s3_url", "form_data":{"foo":"bar"}, "dist_id":"dist42"}'
        registry.register(method='POST', path='/apps/eggs/projects/dog/stage',
                          content=stage_content)
        registry.register(method='POST', path='/s3_url', status=201)
        registry.register(method='POST', path='/apps/eggs/projects/dog/commit/dist42', content='{}')

        main(['--show-traceback', '--token', 'abcdefg',
              'upload',
              '--package-type', 'project',
              data_dir('bar')], False)

        registry.assertAllCalled()

    @urlpatch
    @patch('binstar_client.commands.upload.bool_input')
    def test_upload_interactive_no_overwrite(self, registry, bool_input):
        # regression test for #364
        registry.register(method='HEAD', path='/', status=200)
        registry.register(method='GET', path='/user', content='{"login": "eggs"}')
        content = {'package_types': 'conda'}
        registry.register(method='GET', path='/package/eggs/foo', content=content)
        registry.register(method='GET', path='/release/eggs/foo/0.1', content='{}')
        registry.register(method='GET', path='/dist/eggs/foo/0.1/osx-64/foo-0.1-0.tar.bz2', status=200, content='{}')

        # don't overwrite
        bool_input.return_value = False

        main(['--show-traceback', 'upload', '-i', data_dir('foo-0.1-0.tar.bz2')], False)

    @urlpatch
    def test_upload_private_package(self, registry):

        registry.register(method='HEAD', path='/', status=200)
        registry.register(method='GET', path='/user', content='{"login": "eggs"}')
        registry.register(method='GET', path='/package/eggs/foo', content='{}', status=404)
        content = {'package_types': ['conda']}
        registry.register(method='POST', path='/package/eggs/foo', content=content, status=200)
        registry.register(method='GET', path='/release/eggs/foo/0.1', content='{}')
        registry.register(method='GET', path='/dist/eggs/foo/0.1/osx-64/foo-0.1-0.tar.bz2', status=404, content='{}')

        content = {"post_url": "http://s3url.com/s3_url", "form_data": {}, "dist_id": "dist_id"}
        registry.register(method='POST', path='/stage/eggs/foo/0.1/osx-64/foo-0.1-0.tar.bz2', content=content)

        registry.register(method='POST', path='/s3_url', status=201)
        registry.register(method='POST', path='/commit/eggs/foo/0.1/osx-64/foo-0.1-0.tar.bz2', status=200, content={})

        main(['--show-traceback', 'upload', '--private', data_dir('foo-0.1-0.tar.bz2')], False)

        registry.assertAllCalled()

    @urlpatch
    def test_upload_private_package_not_allowed(self, registry):

        registry.register(method='HEAD', path='/', status=200)
        registry.register(method='GET', path='/user', content='{"login": "eggs"}')
        registry.register(method='GET', path='/package/eggs/foo', content='{}', status=404)
        registry.register(method='POST', path='/package/eggs/foo', content='{"error": "You can not create a private package."}', status=400)

        with self.assertRaises(errors.BinstarError):
            main(['--show-traceback', 'upload', '--private', data_dir('foo-0.1-0.tar.bz2')], False)


if __name__ == '__main__':
    unittest.main()
