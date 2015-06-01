import unittest
from binstar_client.utils.notebook import parse


class ParseTestCase(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(parse("user/notebook-ipynb")[0], 'user')
        self.assertEqual(parse("user/notebook-ipynb")[1], 'notebook-ipynb')

        self.assertIsNone(parse("notebook")[0])
        self.assertEqual(parse("notebook")[1], 'notebook')
