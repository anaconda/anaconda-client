# -*- coding: utf-8 -*-
import io
import unittest

from binstar_client import requests_ext


class TestMultiPart(unittest.TestCase):
    def test_unicode_read(self):
        body = io.BytesIO(b'Unicode™')
        multipart = requests_ext.MultiPartIO([body])
        self.assertEqual(b'Unicode™', multipart.read())


if __name__ == "__main__":
    unittest.main()
