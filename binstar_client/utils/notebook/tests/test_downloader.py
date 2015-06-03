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

        downloader = Downloader(binstar, 'username', 'notebook')
        self.assertEqual(downloader.list_files()[0]['version'], '2')
        self.assertEqual(downloader.list_files()[1]['version'], '2')

    def test_can_download(self):
        package_1 = {'basename': 'notebook.ipynb'}
        package_2 = {'basename': 'NOEXIST'}
        downloader = Downloader('binstar', 'username', 'notebook')
        downloader.output = self.data_dir('')
        self.assertTrue(not downloader.can_download(package_1))
        self.assertTrue(downloader.can_download(package_1, True))
        self.assertTrue(downloader.can_download(package_2))

    def test_list_old_files(self):
        old_files = {'files': [{
            'basename': 'old-notebook',
            'version': '1.0.0',
            'upload_time': '2015-04-02 22:32:31.253000+00:00'
        }]}
        binstar = mock.MagicMock()
        binstar.package = mock.MagicMock(return_value=old_files)

        downloader = Downloader(binstar, 'username', 'notebook')
        self.assertEqual(downloader.list_files()[0]['version'], '1.0.0')

if __name__ == '__main__':
    unittest.main()
