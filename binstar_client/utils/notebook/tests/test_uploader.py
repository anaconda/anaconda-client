import unittest
try:
    from unittest import mock
except ImportError:
    import mock
from binstar_client import errors
from binstar_client.utils.notebook import Uploader


class UploaderTestCase(unittest.TestCase):
    def test_release(self):
        aserver_api = mock.MagicMock()
        aserver_api.release.return_value = 'release'
        uploader = Uploader(aserver_api, 'notebook')
        self.assertEqual(uploader.release, 'release')

    def test_release_not_exist(self):
        aserver_api = mock.MagicMock()
        aserver_api.release.side_effect = errors.NotFound([])
        aserver_api.add_release.return_value = 'release'
        uploader = Uploader(aserver_api, 'project')
        self.assertEqual(uploader.release, 'release')

    def test_package(self):
        aserver_api = mock.MagicMock()
        aserver_api.package.side_effect = errors.NotFound([])
        aserver_api.add_package.return_value = 'package'
        uploader = Uploader(aserver_api, 'project')
        self.assertEqual(uploader.package, 'package')

    def test_version(self):
        aserver_api = mock.MagicMock
        uploader = Uploader(aserver_api, 'project', version='version')
        self.assertEqual(uploader.version, 'version')

        uploader = Uploader(aserver_api, 'project')
        self.assertIsInstance(uploader.version, str)

    def test_package_name(self):
        aserver_api = mock.MagicMock()
        uploader = Uploader(aserver_api, '~/notebooks/my notebook.ipynb')
        self.assertEqual(uploader.project, 'my-notebook')


if __name__ == '__main__':
    unittest.main()
