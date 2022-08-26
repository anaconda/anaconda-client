# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring

import unittest

from tests.urlmock import urlpatch
from binstar_client import Binstar


class Test(unittest.TestCase):
    @urlpatch
    def test_licenses_array_param(self, urls):
        api = Binstar()
        urls.register(method='GET', path='/license', content='[]')
        api.user_licenses()
        urls.assertAllCalled()


if __name__ == '__main__':
    unittest.main()
