import unittest

from binstar_client.errors import BinstarError
from binstar_client.utils.notebook import notebook_url, parse, has_environment
from binstar_client.utils.test.utils import data_dir


class ParseTestCase(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(parse("user/notebook-ipynb")[0], 'user')
        self.assertEqual(parse("user/notebook-ipynb")[1], 'notebook-ipynb')

        self.assertIsNone(parse("notebook")[0])
        self.assertEqual(parse("notebook")[1], 'notebook')


class NotebookURLTestCase(unittest.TestCase):
    def test_anaconda_org_installation(self):
        upload_info = {'url': 'http://anaconda.org/darth/deathstart-ipynb'}
        url = 'http://notebooks.anaconda.org/darth/deathstart-ipynb'
        self.assertEqual(notebook_url(upload_info), url)

    def test_anaconda_server_installation(self):
        upload_info = {'url': 'http://custom/darth/deathstart-ipynb'}
        url = 'http://custom/notebooks/darth/deathstart-ipynb'
        self.assertEqual(notebook_url(upload_info), url)


class HasEnvironmentTestCase(unittest.TestCase):
    def test_has_no_environment(self):
        self.assertFalse(has_environment(data_dir('notebook.ipynb')))

    def test_has_environment(self):
        self.assertTrue(has_environment(data_dir('notebook_with_env.ipynb')))

    def test_no_file(self):
        self.assertFalse(has_environment("no-file"))


if __name__ == '__main__':
    unittest.main()
