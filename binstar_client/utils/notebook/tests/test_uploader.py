import unittest
try:
    from unittest import mock
except ImportError:
    import mock
from binstar_client import errors
from binstar_client.utils.notebook import Uploader


class UploaderTestCase(unittest.TestCase):
    def test_release(self):
        binstar = mock.MagicMock()
        binstar.release.return_value = 'release'
        uploader = Uploader(binstar, 'notebook')
        self.assertEqual(uploader.release, 'release')

    def test_release_not_exist(self):
        binstar = mock.MagicMock()
        binstar.release.side_effect = errors.NotFound([])
        binstar.add_release.return_value = 'release'
        uploader = Uploader(binstar, 'project')
        self.assertEqual(uploader.release, 'release')

    def test_package(self):
        binstar = mock.MagicMock()
        binstar.package.side_effect = errors.NotFound([])
        binstar.add_package.return_value = 'package'
        uploader = Uploader(binstar, 'project')
        self.assertEqual(uploader.package, 'package')

    def test_version(self):
        binstar = mock.MagicMock
        uploader = Uploader(binstar, 'project', version='version')
        self.assertEqual(uploader.version, 'version')

        uploader = Uploader(binstar, 'project')
        self.assertIsInstance(uploader.version, str)


if __name__ == '__main__':
    unittest.main()
