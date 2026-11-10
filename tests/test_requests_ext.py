import io
import unittest

from binstar_client import requests_ext


class TestMultiPart(unittest.TestCase):
    def test_unicode_read(self):
        body = io.BytesIO('Unicode™'.encode())
        multipart = requests_ext.MultiPartIO([body])
        self.assertEqual('Unicode™'.encode(), multipart.read())


if __name__ == '__main__':
    unittest.main()
