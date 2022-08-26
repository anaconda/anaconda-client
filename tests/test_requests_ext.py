# -*- coding: utf-8 -*-

# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring

import io
import unittest

from binstar_client import requests_ext


class TestMultiPart(unittest.TestCase):
    def test_unicode_read(self):
        body = io.BytesIO('Unicode™'.encode('utf-8'))
        multipart = requests_ext.MultiPartIO([body])
        self.assertEqual('Unicode™'.encode('utf-8'), multipart.read())


if __name__ == '__main__':
    unittest.main()
