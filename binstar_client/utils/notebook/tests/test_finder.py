import unittest
from os.path import join, dirname
from binstar_client.utils.notebook.finder import Finder


class FinderTestCase(unittest.TestCase):
    def data_dir(self, filename):
        test_data = join(dirname(__file__), 'data')
        return join(test_data, filename)

    def test_one_directory(self):
        finder_1 = Finder(['.'])
        finder_2 = Finder([self.data_dir('')])
        self.assertTrue(finder_1.one_directory())
        self.assertTrue(finder_2.one_directory())

    def test_is_valid(self):
        finder = Finder(['.'])
        self.assertTrue(finder.is_valid(self.data_dir('notebook.ipynb')))
        self.assertEqual(finder.is_valid(self.data_dir('virus.exe')), False)
        self.assertEqual(finder.is_valid(self.data_dir('no-exist.ipynb')), False)

    def test_parse(self):
        finder = Finder([self.data_dir('')])
        valid, invalid = finder.parse()
        self.assertEqual(valid, ['notebook.ipynb'])
        self.assertEqual(invalid, ['virus.exe'])

        finder = Finder([self.data_dir('notebook.ipynb')])
        valid, invalid = finder.parse()
        self.assertTrue(valid[0].endswith('notebook.ipynb'))
        self.assertEqual(invalid, [])

    def test_autoparse(self):
        finder = Finder([self.data_dir('')])
        self.assertTrue(finder.prefix.endswith('data/'))
        self.assertEqual(finder.valid, ['notebook.ipynb'])
        self.assertEqual(finder.invalid, ['virus.exe'])


if __name__ == '__main__':
    unittest.main()
