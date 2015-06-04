import unittest
from binstar_client.utils.notebook import notebook_url, parse


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


if __name__ == '__main__':
    unittest.main()
