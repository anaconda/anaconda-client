import unittest
from binstar_client.utils.notebook import inflection


class InflectorsTestCase(unittest.TestCase):
    def test_one_directory(self):
        self.assertEqual(inflection.parameterize(u"Donald E. Knuth"), 'donald-e-knuth')


if __name__ == '__main__':
    unittest.main()
