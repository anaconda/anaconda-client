import os
import unittest
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
    def test_ensure_location(self):
        binstar = mock.MagicMock()
        binstar.package = mock.MagicMock(return_value=files)

        downloader = Downloader(binstar, 'username', 'project', 'notebook')
        self.assertEqual(downloader.list_files()[0]['basename'], 'notebook')
        self.assertEqual(downloader.list_files()[0]['version'], '2')
        self.assertEqual(downloader.list_files()[1]['basename'], 'data')


if __name__ == '__main__':
    unittest.main()
