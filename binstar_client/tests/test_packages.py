import unittest

from binstar_client.tests.urlmock import urlpatch
from binstar_client import Binstar


class Test(unittest.TestCase):
    @urlpatch
    def test_packages_array_param(self, urls):
        api = Binstar()
        urls.register(method='GET', path='/packages/u1?package_type=conda&package_type=pypi', content='[]')

        packages = api.user_packages('u1', package_type=['conda', 'pypi'])

        urls.assertAllCalled()

    @urlpatch
    def test_packages_parameters(self, urls):
        api = Binstar()
        urls.register(method='GET', path='/packages/u1?platform=osx-64&package_type=conda&type=app', content='[]')

        packages = api.user_packages('u1', platform='osx-64', type_='app', package_type='conda')

        urls.assertAllCalled()

    @urlpatch
    def test_packages_empty(self, urls):
        api = Binstar()
        urls.register(method='GET', path='/packages/u1', content='[]')

        packages = api.user_packages('u1')

        self.assertEqual(packages, [])
        urls.assertAllCalled()


if __name__ == '__main__':
    unittest.main()
