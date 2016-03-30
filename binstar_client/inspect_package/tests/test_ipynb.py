
from os import path
import unittest

from binstar_client.inspect_package.ipynb import IPythonNotebook, inspect_ipynb_package
import io


def data_path(filename):
    return path.join(path.dirname(__file__), 'data', filename)


class IPythonNotebookTestCase(unittest.TestCase):
    def test_package_name(self):

        fileobj = io.StringIO()
        self.assertEqual(IPythonNotebook('notebook.ipynb', fileobj).name, 'notebook')

    def test_package_name_unicode(self):

        fileobj = io.StringIO()
        self.assertEqual(IPythonNotebook(b'na\xcc\x83o.ipynb', fileobj).name, 'nao')

    def test_version(self):
        with open(data_path('notebook.ipynb')) as fileobj:
            self.assertIsInstance(IPythonNotebook('notebook.ipynb', fileobj).version, str)


class InspectIPYNBPackageTest(unittest.TestCase):
    def test_inspect_ipynb_package(self):
        with open(data_path('notebook.ipynb')) as fileobj:
            package_data, release_data, file_data = inspect_ipynb_package('notebook.ipynb', fileobj)

        self.assertEqual({
            'name': 'notebook',
            'summary': 'IPython notebook'
        }, package_data)

        self.assertEqual({
            'basename': 'notebook.ipynb',
            'attrs': {}
        }, file_data)


if __name__ == '__main__':
    unittest.main()
