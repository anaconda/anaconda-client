# -*- coding: utf8 -*-
# pylint: disable=missing-function-docstring

"""Tests for package upload commands."""

import json
import unittest.mock

import pytest

from binstar_client import errors
from tests.fixture import CLITestCase, main
from tests.urlmock import urlpatch
from tests.utils.utils import data_dir


class Test(CLITestCase):
    """Tests for package upload commands."""

    @urlpatch
    def test_upload_bad_package(self, registry):
        registry.register(method='HEAD', path='/', status=200)
        registry.register(method='GET', path='/user', content='{"login": "eggs"}')
        registry.register(method='GET', path='/package/eggs/foo', content='{}', status=404)
        registry.register(method='POST', path='/package/eggs/foo', content={'package_types': ['conda']}, status=200)
        registry.register(method='GET', path='/release/eggs/foo/0.1', content='{}')
        registry.register(method='GET', path='/dist/eggs/foo/0.1/osx-64/foo-0.1-0.tar.bz2', status=404, content='{}')
        staging_response = registry.register(
            method='POST',
            path='/stage/eggs/foo/0.1/osx-64/foo-0.1-0.tar.bz2',
            content={'post_url': 'http://s3url.com/s3_url', 'form_data': {}, 'dist_id': 'dist_id'},
        )
        registry.register(method='POST', path='/s3_url', status=201)
        registry.register(method='POST', path='/commit/eggs/foo/0.1/osx-64/foo-0.1-0.tar.bz2', status=200, content={})

        main(['--show-traceback', 'upload', data_dir('foo-0.1-0.tar.bz2')])

        self.assertIsNotNone(json.loads(staging_response.req.body).get('sha256'))

    @urlpatch
    def test_upload_bad_package_no_register(self, registry):
        registry.register(method='HEAD', path='/', status=200)
        registry.register(method='GET', path='/user', content='{"login": "eggs"}')
        registry.register(method='GET', path='/dist/eggs/foo/0.1/osx-64/foo-0.1-0.tar.bz2', status=404)
        registry.register(method='GET', path='/package/eggs/foo', status=404)

        with self.assertRaises(errors.UserError):
            main(['--show-traceback', 'upload', '--no-register', data_dir('foo-0.1-0.tar.bz2')])

        registry.assertAllCalled()

    @urlpatch
    def test_upload_conda(self, registry):
        registry.register(method='HEAD', path='/', status=200)
        registry.register(method='GET', path='/user', content='{"login": "eggs"}')
        registry.register(method='GET', path='/dist/eggs/foo/0.1/osx-64/foo-0.1-0.tar.bz2', status=404)
        registry.register(method='GET', path='/package/eggs/foo', content={'package_types': ['conda']})
        registry.register(method='GET', path='/release/eggs/foo/0.1', content='{}')
        staging_response = registry.register(
            method='POST',
            path='/stage/eggs/foo/0.1/osx-64/foo-0.1-0.tar.bz2',
            content={'post_url': 'http://s3url.com/s3_url', 'form_data': {}, 'dist_id': 'dist_id'},
        )
        registry.register(method='POST', path='/s3_url', status=201)
        registry.register(method='POST', path='/commit/eggs/foo/0.1/osx-64/foo-0.1-0.tar.bz2', status=200, content={})

        main(['--show-traceback', 'upload', data_dir('foo-0.1-0.tar.bz2')])

        registry.assertAllCalled()
        self.assertIsNotNone(json.loads(staging_response.req.body).get('sha256'))

    @urlpatch
    def test_upload_conda_v2(self, registry):
        registry.register(method='HEAD', path='/', status=200)
        registry.register(method='GET', path='/user', content='{"login": "eggs"}')
        registry.register(method='GET', path='/dist/eggs/mock/2.0.0/osx-64/mock-2.0.0-py37_1000.conda', status=404)
        registry.register(method='GET', path='/package/eggs/mock', content={'package_types': ['conda']})
        registry.register(method='GET', path='/release/eggs/mock/2.0.0', content='{}')
        staging_response = registry.register(
            method='POST',
            path='/stage/eggs/mock/2.0.0/osx-64/mock-2.0.0-py37_1000.conda',
            content={'post_url': 'http://s3url.com/s3_url', 'form_data': {}, 'dist_id': 'dist_id'},
        )
        registry.register(method='POST', path='/s3_url', status=201)
        registry.register(
            method='POST', path='/commit/eggs/mock/2.0.0/osx-64/mock-2.0.0-py37_1000.conda', status=200, content={},
        )

        main(['--show-traceback', 'upload', data_dir('mock-2.0.0-py37_1000.conda')])

        registry.assertAllCalled()
        self.assertIsNotNone(json.loads(staging_response.req.body).get('sha256'))

    @urlpatch
    def test_upload_use_pkg_metadata(self, registry):
        registry.register(method='HEAD', path='/', status=200)
        registry.register(method='GET', path='/user', content='{"login": "eggs"}')
        registry.register(method='GET', path='/dist/eggs/mock/2.0.0/osx-64/mock-2.0.0-py37_1000.conda', status=404)
        registry.register(method='GET', path='/package/eggs/mock', content={'package_types': ['conda']})
        registry.register(method='GET', path='/release/eggs/mock/2.0.0', content='{}')
        registry.register(method='PATCH', path='/release/eggs/mock/2.0.0', content='{}')
        staging_response = registry.register(
            method='POST',
            path='/stage/eggs/mock/2.0.0/osx-64/mock-2.0.0-py37_1000.conda',
            content={'post_url': 'http://s3url.com/s3_url', 'form_data': {}, 'dist_id': 'dist_id'},
        )
        registry.register(method='POST', path='/s3_url', status=201)
        registry.register(
            method='POST',
            path='/commit/eggs/mock/2.0.0/osx-64/mock-2.0.0-py37_1000.conda',
            status=200,
            content={},
        )

        main(['--show-traceback', 'upload', '--force-metadata-update', data_dir('mock-2.0.0-py37_1000.conda')])

        registry.assertAllCalled()
        self.assertIsNotNone(json.loads(staging_response.req.body).get('sha256'))

    @urlpatch
    def test_upload_pypi(self, registry):
        registry.register(method='HEAD', path='/', status=200)
        registry.register(method='GET', path='/user', content='{"login": "eggs"}')
        registry.register(method='GET', path='/dist/eggs/test-package34/0.3.1/test_package34-0.3.1.tar.gz', status=404)
        registry.register(method='GET', path='/package/eggs/test-package34', content={'package_types': ['pypi']})
        registry.register(method='GET', path='/release/eggs/test-package34/0.3.1', content='{}')
        staging_response = registry.register(
            method='POST',
            path='/stage/eggs/test-package34/0.3.1/test_package34-0.3.1.tar.gz',
            content={'post_url': 'http://s3url.com/s3_url', 'form_data': {}, 'dist_id': 'dist_id'},
        )
        registry.register(method='POST', path='/s3_url', status=201)
        registry.register(
            method='POST',
            path='/commit/eggs/test-package34/0.3.1/test_package34-0.3.1.tar.gz',
            status=200,
            content={},
        )

        main(['--show-traceback', 'upload', data_dir('test_package34-0.3.1.tar.gz')])

        registry.assertAllCalled()
        self.assertIsNotNone(json.loads(staging_response.req.body).get('sha256'))

    @urlpatch
    def test_upload_pypi_with_conda_package_name_allowed(self, registry):
        registry.register(method='HEAD', path='/', status=200)
        registry.register(method='GET', path='/user', content='{"login": "eggs"}')
        registry.register(method='GET', path='/dist/eggs/test_package34/0.3.1/test_package34-0.3.1.tar.gz', status=404)
        registry.register(method='GET', path='/package/eggs/test_package34', content={'package_types': ['pypi']})
        registry.register(method='GET', path='/release/eggs/test_package34/0.3.1', content='{}')
        staging_response = registry.register(
            method='POST',
            path='/stage/eggs/test_package34/0.3.1/test_package34-0.3.1.tar.gz',
            content={'post_url': 'http://s3url.com/s3_url', 'form_data': {}, 'dist_id': 'dist_id'},
        )
        registry.register(method='POST', path='/s3_url', status=201)
        registry.register(
            method='POST',
            path='/commit/eggs/test_package34/0.3.1/test_package34-0.3.1.tar.gz',
            status=200,
            content={},
        )

        # Pass -o to override the channel/package pypi package should go to
        main([
            '--show-traceback', 'upload', '--package', 'test_package34', '--package-type', 'pypi',
            data_dir('test_package34-0.3.1.tar.gz'),
        ])
        registry.assertAllCalled()
        self.assertIsNotNone(json.loads(staging_response.req.body).get('sha256'))

    @urlpatch
    def test_upload_conda_package_with_name_override_fails(self, registry):
        registry.register(method='HEAD', path='/', status=200)
        registry.register(method='GET', path='/user', content='{"login": "eggs"}')

        # Passing -o for `file` package_type doesn't override channel
        with self.assertRaises(errors.BinstarError):
            main([
                '--show-traceback', 'upload', '--package', 'test_package', '--package-type', 'file',
                data_dir('test_package34-0.3.1.tar.gz'),
            ])

        registry.assertAllCalled()

    @urlpatch
    def test_upload_pypi_with_random_name(self, registry):
        registry.register(method='HEAD', path='/', status=200)
        registry.register(method='GET', path='/user', content='{"login": "eggs"}')

        with self.assertRaises(errors.BinstarError):
            main(['--show-traceback', 'upload', '--package', 'alpha_omega', data_dir('test_package34-0.3.1.tar.gz')])

        registry.assertAllCalled()

    @urlpatch
    def test_upload_file(self, registry):
        registry.register(method='HEAD', path='/', status=200)
        registry.register(method='GET', path='/user', content='{"login": "eggs"}')
        registry.register(method='GET', path='/dist/eggs/test-package34/0.3.1/test_package34-0.3.1.tar.gz', status=404)
        registry.register(method='GET', path='/package/eggs/test-package34', content={'package_types': ['file']})
        registry.register(method='GET', path='/release/eggs/test-package34/0.3.1', content='{}')
        staging_response = registry.register(
            method='POST',
            path='/stage/eggs/test-package34/0.3.1/test_package34-0.3.1.tar.gz',
            content={'post_url': 'http://s3url.com/s3_url', 'form_data': {}, 'dist_id': 'dist_id'},
        )
        registry.register(method='POST', path='/s3_url', status=201)
        registry.register(
            method='POST',
            path='/commit/eggs/test-package34/0.3.1/test_package34-0.3.1.tar.gz',
            status=200,
            content={},
        )

        main([
            '--show-traceback', 'upload', '--package-type', 'file', '--package', 'test-package34', '--version', '0.3.1',
            data_dir('test_package34-0.3.1.tar.gz'),
        ])

        registry.assertAllCalled()
        self.assertIsNotNone(json.loads(staging_response.req.body).get('sha256'))

    @pytest.mark.xfail(reason='anaconda-project removed')
    @urlpatch
    def test_upload_project(self, registry):
        # there's redundant work between anaconda-client which checks auth and anaconda-project also checks auth;
        # -project has no way to know it was already checked :-/
        registry.register(method='HEAD', path='/', status=200)
        registry.register(method='GET', path='/user/eggs', content='{"login": "eggs"}')
        registry.register(method='GET', path='/user', content='{"login": "eggs"}')
        registry.register(method='GET', path='/apps/eggs/projects/dog', content='{}')
        registry.register(
            method='POST',
            path='/apps/eggs/projects/dog/stage',
            content='{"post_url":"http://s3url.com/s3_url", "form_data":{"foo":"bar"}, "dist_id":"dist42"}',
        )
        registry.register(method='POST', path='/s3_url', status=201)
        registry.register(method='POST', path='/apps/eggs/projects/dog/commit/dist42', content='{}')

        main(['--show-traceback', 'upload', '--package-type', 'project', data_dir('bar')])

        registry.assertAllCalled()

    @pytest.mark.xfail(reason='anaconda-project removed')
    @urlpatch
    def test_upload_notebook_as_project(self, registry):
        registry.register(method='HEAD', path='/', status=200)
        registry.register(method='GET', path='/user/eggs', content='{"login": "eggs"}')
        registry.register(method='GET', path='/user', content='{"login": "eggs"}')
        registry.register(method='GET', path='/apps/eggs/projects/foo', content='{}')
        registry.register(
            method='POST',
            path='/apps/eggs/projects/foo/stage',
            content='{"post_url":"http://s3url.com/s3_url", "form_data":{"foo":"bar"}, "dist_id":"dist42"}',
        )
        registry.register(method='POST', path='/s3_url', status=201)
        registry.register(method='POST', path='/apps/eggs/projects/foo/commit/dist42', content='{}')

        main(['--show-traceback', 'upload', '--package-type', 'project', data_dir('foo.ipynb')])

        registry.assertAllCalled()

    @pytest.mark.xfail(reason='anaconda-project removed')
    @urlpatch
    def test_upload_project_specifying_user(self, registry):
        registry.register(method='HEAD', path='/', status=200)
        registry.register(method='GET', path='/user/alice', content='{"login": "alice"}')
        registry.register(method='GET', path='/apps/alice/projects/dog', content='{}')
        registry.register(
            method='POST',
            path='/apps/alice/projects/dog/stage',
            content='{"post_url":"http://s3url.com/s3_url", "form_data":{"foo":"bar"}, "dist_id":"dist42"}',
        )
        registry.register(method='POST', path='/s3_url', status=201)
        registry.register(method='POST', path='/apps/alice/projects/dog/commit/dist42', content='{}')

        main(['--show-traceback', 'upload', '--package-type', 'project', '--user', 'alice', data_dir('bar')])

        registry.assertAllCalled()

    @pytest.mark.xfail(reason='anaconda-project removed')
    @urlpatch
    def test_upload_project_specifying_token(self, registry):
        registry.register(method='HEAD', path='/', status=200)
        registry.register(
            method='GET',
            path='/user/eggs',
            content='{"login": "eggs"}',
            expected_headers={'Authorization': 'token abcdefg'},
        )
        registry.register(method='GET', path='/user', content='{"login": "eggs"}')
        registry.register(method='GET', path='/apps/eggs/projects/dog', content='{}')
        registry.register(
            method='POST',
            path='/apps/eggs/projects/dog/stage',
            content='{"post_url":"http://s3url.com/s3_url", "form_data":{"foo":"bar"}, "dist_id":"dist42"}',
        )
        registry.register(method='POST', path='/s3_url', status=201)
        registry.register(method='POST', path='/apps/eggs/projects/dog/commit/dist42', content='{}')

        main(['--show-traceback', '--token', 'abcdefg', 'upload', '--package-type', 'project', data_dir('bar')])

        registry.assertAllCalled()

    @urlpatch
    @unittest.mock.patch('binstar_client.commands.upload.bool_input')
    def test_upload_interactive_no_overwrite(self, registry, bool_input):
        # regression test for #364
        registry.register(method='HEAD', path='/', status=200)
        registry.register(method='GET', path='/user', content='{"login": "eggs"}')
        registry.register(method='GET', path='/dist/eggs/foo/0.1/osx-64/foo-0.1-0.tar.bz2', content='{}')

        bool_input.return_value = False  # do not overwrite package

        main(['--show-traceback', 'upload', '-i', data_dir('foo-0.1-0.tar.bz2')])

        registry.assertAllCalled()

    @urlpatch
    @unittest.mock.patch('binstar_client.commands.upload.bool_input')
    def test_upload_interactive_overwrite(self, registry, bool_input):
        registry.register(method='HEAD', path='/', status=200)
        registry.register(method='GET', path='/user', content='{"login": "eggs"}')
        registry.register(method='GET', path='/dist/eggs/foo/0.1/osx-64/foo-0.1-0.tar.bz2', content='{}')
        registry.register(method='DELETE', path='/dist/eggs/foo/0.1/osx-64/foo-0.1-0.tar.bz2', content='{}')
        registry.register(method='GET', path='/package/eggs/foo', content={'package_types': ['conda']})
        registry.register(method='GET', path='/release/eggs/foo/0.1', content='{}')
        staging_response = registry.register(
            method='POST',
            path='/stage/eggs/foo/0.1/osx-64/foo-0.1-0.tar.bz2',
            content={'post_url': 'http://s3url.com/s3_url', 'form_data': {}, 'dist_id': 'dist_id'},
        )
        registry.register(method='POST', path='/s3_url', status=201)
        registry.register(method='POST', path='/commit/eggs/foo/0.1/osx-64/foo-0.1-0.tar.bz2', status=200, content={})

        bool_input.return_value = True

        main(['--show-traceback', 'upload', '-i', data_dir('foo-0.1-0.tar.bz2')])

        registry.assertAllCalled()
        self.assertIsNotNone(json.loads(staging_response.req.body).get('sha256'))

    @urlpatch
    def test_upload_private_package(self, registry):
        registry.register(method='HEAD', path='/', status=200)
        registry.register(method='GET', path='/user', content='{"login": "eggs"}')
        registry.register(method='GET', path='/dist/eggs/foo/0.1/osx-64/foo-0.1-0.tar.bz2', status=404)
        registry.register(method='GET', path='/package/eggs/foo', content='{}', status=404)
        registry.register(method='POST', path='/package/eggs/foo', content={'package_types': ['conda']}, status=200)
        registry.register(method='GET', path='/release/eggs/foo/0.1', content='{}')
        staging_response = registry.register(
            method='POST',
            path='/stage/eggs/foo/0.1/osx-64/foo-0.1-0.tar.bz2',
            content={'post_url': 'http://s3url.com/s3_url', 'form_data': {}, 'dist_id': 'dist_id'},
        )
        registry.register(method='POST', path='/s3_url', status=201)
        registry.register(method='POST', path='/commit/eggs/foo/0.1/osx-64/foo-0.1-0.tar.bz2', status=200, content={})

        main(['--show-traceback', 'upload', '--private', data_dir('foo-0.1-0.tar.bz2')])

        registry.assertAllCalled()
        self.assertIsNotNone(json.loads(staging_response.req.body).get('sha256'))

    @urlpatch
    def test_upload_private_package_not_allowed(self, registry):
        registry.register(method='HEAD', path='/', status=200)
        registry.register(method='GET', path='/user', content='{"login": "eggs"}')
        registry.register(method='GET', path='/dist/eggs/foo/0.1/osx-64/foo-0.1-0.tar.bz2', status=404)
        registry.register(method='GET', path='/package/eggs/foo', content='{}', status=404)
        registry.register(
            method='POST',
            path='/package/eggs/foo',
            content='{"error": "You can not create a private package."}',
            status=400,
        )

        with self.assertRaises(errors.BinstarError):
            main(['--show-traceback', 'upload', '--private', data_dir('foo-0.1-0.tar.bz2')])
