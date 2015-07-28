import unittest

from binstar_client.inspect_package.conda import get_subdir


class TestGetSubdir(unittest.TestCase):

    def test_noarch(self):
        index = {'subdir': 'noarch'}
        self.assertEqual(get_subdir(index), 'noarch')

        index = {'arch': None}
        self.assertEqual(get_subdir(index), 'noarch')

        index = {}
        self.assertEqual(get_subdir(index), 'noarch')

        index = {'arch': 'x86_64', 'platform': None, 'subdir': 'noarch'}
        self.assertEqual(get_subdir(index), 'noarch')

    def test_linux64(self):
        index = {'arch': 'x86_64', 'platform': 'linux'}
        self.assertEqual(get_subdir(index), 'linux-64')

    def test_osx32(self):
        index = {'arch': 'x86', 'platform': 'osx'}
        self.assertEqual(get_subdir(index), 'osx-32')

    def test_ppc64(self):
        index = {'arch': 'ppc64le', 'platform': 'linux'}
        self.assertEqual(get_subdir(index), 'linux-ppc64le')

        index = {'subdir': 'linux-ppc64le'}
        self.assertEqual(get_subdir(index), 'linux-ppc64le')


if __name__ == '__main__':
    unittest.main()
