import unittest
from os.path import join, dirname
try:
    from unittest import mock
except ImportError:
    import mock

from binstar_client.utils.notebook import Downloader


files = {'files': [
    {'basename': 'notebook', 'version': '1'},
    {'basename': 'notebook', 'version': '2'},
    {'basename': 'data', 'version': '2'}
]}


class DownloaderTestCase(unittest.TestCase):
    def data_dir(self, filename):
        test_data = join(dirname(__file__), 'data')
        return join(test_data, filename)

    def test_ensure_location(self):
        binstar = mock.MagicMock()
        binstar.package = mock.MagicMock(return_value=files)

        downloader = Downloader(binstar, 'username', 'project', 'notebook')
        self.assertEqual(downloader.list_files()[0]['basename'], 'notebook')
        self.assertEqual(downloader.list_files()[0]['version'], '2')
        self.assertEqual(downloader.list_files()[1]['basename'], 'data')

    def test_can_download(self):
        package_1 = {'basename': 'notebook.ipynb'}
        package_2 = {'basename': 'NOEXIST'}
        downloader = Downloader('binstar', 'username', 'project', 'notebook')
        self.assertTrue(not downloader.can_download(self.data_dir(''), package_1))
        self.assertTrue(downloader.can_download(self.data_dir(''), package_1, True))
        self.assertTrue(downloader.can_download(self.data_dir(''), package_2))


if __name__ == '__main__':
    unittest.main()
