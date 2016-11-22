import unittest

from binstar_client.tests.urlmock import urlpatch
from binstar_client import Binstar


class Test(unittest.TestCase):
    @urlpatch
    def test_licenses_array_param(self, urls):
        api = Binstar()
        urls.register(method='GET',
                      path='/license/?product=produc_1&product=product_2',
                      content='[]')
        licenses = api.user_licenses(products=['product_1', 'product_2'])
        urls.assertAllCalled()


if __name__ == '__main__':
    unittest.main()
