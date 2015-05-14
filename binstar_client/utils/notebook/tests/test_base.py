import unittest
from binstar_client.utils.notebook import parse


class ParseTestCase(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(parse("user/project")[0], 'user')
        self.assertEqual(parse("user/project")[1], 'project')
        self.assertIsNone(parse("user/project")[2])

        self.assertEqual(parse("user/project:notebook")[0], 'user')
        self.assertEqual(parse("user/project:notebook")[1], 'project')
        self.assertEqual(parse("user/project:notebook")[2], 'notebook')

        self.assertIsNone(parse("project")[0])
        self.assertEqual(parse("project")[1], 'project')
        self.assertIsNone(parse("project")[2])
