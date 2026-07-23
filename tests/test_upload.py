# -*- coding: utf8 -*-
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
            method='POST',
            path='/commit/eggs/mock/2.0.0/osx-64/mock-2.0.0-py37_1000.conda',
            status=200,
            content={},
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
        main(
            [
                '--show-traceback',
                'upload',
                '--package',
                'test_package34',
                '--package-type',
                'pypi',
                data_dir('test_package34-0.3.1.tar.gz'),
            ]
        )
        registry.assertAllCalled()
        self.assertIsNotNone(json.loads(staging_response.req.body).get('sha256'))

    @urlpatch
    def test_upload_conda_package_with_name_override_fails(self, registry):
        registry.register(method='HEAD', path='/', status=200)
        registry.register(method='GET', path='/user', content='{"login": "eggs"}')

        # Passing -o for `file` package_type doesn't override channel
        with self.assertRaises(errors.BinstarError):
            main(
                [
                    '--show-traceback',
                    'upload',
                    '--package',
                    'test_package',
                    '--package-type',
                    'file',
                    data_dir('test_package34-0.3.1.tar.gz'),
                ]
            )

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

        main(
            [
                '--show-traceback',
                'upload',
                '--package-type',
                'file',
                '--package',
                'test-package34',
                '--version',
                '0.3.1',
                data_dir('test_package34-0.3.1.tar.gz'),
            ]
        )

        registry.assertAllCalled()
        self.assertIsNotNone(json.loads(staging_response.req.body).get('sha256'))

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

    def test_upload_channel_and_user_flags_errors(self):
        with self.assertRaises(SystemExit) as ctx:
            main(['--show-traceback', 'upload', '-c', 'mychannel', '-u', 'myorg', data_dir('foo-0.1-0.tar.bz2')])
        self.assertEqual(ctx.exception.code, 1)

    @unittest.mock.patch('binstar_client.commands._repo_channels.upload_command')
    def test_upload_channel_flag_delegates_to_channel_upload(self, mock_upload_command):
        main(['--show-traceback', 'upload', '-c', 'mychannel', data_dir('foo-0.1-0.tar.bz2')])
        mock_upload_command.assert_called_once()
        call_kwargs = mock_upload_command.call_args[1]
        assert call_kwargs['ctx'] is None
        assert call_kwargs['files'] == [data_dir('foo-0.1-0.tar.bz2')]
        assert call_kwargs['channel'] == ['mychannel']
        assert call_kwargs['namespace'] is None
        assert call_kwargs['package_type'] is None
        assert call_kwargs['from_deprecated_channel_flag'] is True
        assert call_kwargs['labels'] == []

    @unittest.mock.patch('binstar_client.commands._repo_channels.upload_command')
    def test_upload_channel_flag_with_package_type_converts_to_enum(self, mock_upload_command):
        from binstar_client.repocore.package_utils import PackageType

        main(
            ['--show-traceback', 'upload', '-c', 'mychannel', '--package-type', 'conda', data_dir('foo-0.1-0.tar.bz2')]
        )

        mock_upload_command.assert_called_once()
        call_kwargs = mock_upload_command.call_args[1]
        assert call_kwargs['package_type'] == PackageType.conda
        assert isinstance(call_kwargs['package_type'], PackageType)
        assert call_kwargs['channel'] == ['mychannel']
        assert call_kwargs['from_deprecated_channel_flag'] is True

    def test_upload_channel_flag_with_invalid_package_type_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            main(
                [
                    '--show-traceback',
                    'upload',
                    '-c',
                    'mychannel',
                    '--package-type',
                    'invalid_type',
                    data_dir('foo-0.1-0.tar.bz2'),
                ]
            )

        error_message = str(ctx.exception)
        self.assertIn("Invalid value for '--package-type'", error_message)
        self.assertIn('invalid_type', error_message)

    @unittest.mock.patch('binstar_client.commands._repo_channels.upload_command')
    def test_upload_namespace_flag_routes_to_repo(self, mock_upload_command):
        main(['--show-traceback', 'upload', '-c', 'prod', '-n', 'myns', data_dir('foo-0.1-0.tar.bz2')])
        mock_upload_command.assert_called_once()
        call_kwargs = mock_upload_command.call_args[1]
        assert call_kwargs['channel'] == ['prod']
        assert call_kwargs['namespace'] == 'myns'

    def test_upload_namespace_without_channel_errors(self):
        with self.assertRaises(SystemExit) as ctx:
            main(['--show-traceback', 'upload', '-n', 'myns', data_dir('foo-0.1-0.tar.bz2')])
        self.assertEqual(ctx.exception.code, 1)

    @unittest.mock.patch('binstar_client.commands._repo_channels._upload_to_dotorg')
    @unittest.mock.patch('binstar_client.commands._repo_channels._process_and_upload_files')
    def test_upload_label_on_repo_channel_warns_not_errors(self, mock_repo_upload, mock_dotorg):
        """A label on a repo-only channel is a no-op, not an error: we warn and
        still upload to the repo channel (labels are dropped for it)."""
        main(['--show-traceback', 'upload', '-c', 'myns/prod', '-l', 'dev', data_dir('foo-0.1-0.tar.bz2')])
        # Repo upload proceeds despite the label; nothing routes to dotorg.
        mock_repo_upload.assert_called_once()
        mock_dotorg.assert_not_called()

    @unittest.mock.patch('binstar_client.commands._repo_channels._upload_to_dotorg')
    @unittest.mock.patch('binstar_client.commands._repo_channels._process_and_upload_files')
    def test_upload_label_with_namespace_flag_warns_not_errors(self, mock_repo_upload, mock_dotorg):
        """`-c prod -n myns -l dev` resolves to a repo channel; the label warns
        rather than aborting the upload."""
        main(['--show-traceback', 'upload', '-c', 'prod', '-n', 'myns', '-l', 'dev', data_dir('foo-0.1-0.tar.bz2')])
        mock_repo_upload.assert_called_once()
        mock_dotorg.assert_not_called()

    @unittest.mock.patch('binstar_client.commands.upload._dotorg_upload')
    @unittest.mock.patch('binstar_client.repocore.resolve.classify_and_resolve')
    def test_upload_channel_org_route_forwards_all_args(self, mock_classify, mock_dotorg):
        """`anaconda upload -c NAME` that resolves to anaconda.org must forward the full
        arg set (e.g. --private, --summary) through to the dotorg Uploader."""
        from binstar_client.repocore import ResolvedChannel

        mock_classify.return_value = ResolvedChannel(
            namespace=None, channel_name='someorg', target='org', owner='someorg'
        )

        main(
            [
                'upload',
                '-c',
                'someorg',
                '-l',
                'dev',
                '--private',
                '--summary',
                'a summary',
                '--package',
                'mypkg',
                '--version',
                '9.9',
                data_dir('foo-0.1-0.tar.bz2'),
            ]
        )

        mock_dotorg.assert_called_once()
        forwarded = mock_dotorg.call_args[0][0]
        assert forwarded.user == 'someorg'
        assert forwarded.labels == ['dev']
        assert forwarded.private is True
        assert forwarded.summary == 'a summary'
        assert forwarded.package == 'mypkg'
        assert forwarded.version == '9.9'
        # channels consumed so it doesn't loop back through the repo path
        assert forwarded.channels == []
