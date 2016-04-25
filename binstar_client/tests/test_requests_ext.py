# -*- coding: utf-8 -*-
import io
import unittest

from binstar_client import requests_ext


class TestMultiPart(unittest.TestCase):
    def test_unicode_read(self):
        body = io.BytesIO(u'Unicode™'.encode('utf-8'))
        multipart = requests_ext.MultiPartIO([body])
        self.assertEqual(u'Unicode™'.encode('utf-8'), multipart.read())


if __name__ == "__main__":
    unittest.main()
