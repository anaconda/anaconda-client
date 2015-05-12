import unittest
from os.path import join, dirname
from binstar_client import errors
from binstar_client.utils.notebook import parse, Finder


class ParseTestCase(unittest.TestCase):
    def data_dir(self, filename):
        test_data = join(dirname(__file__), 'data')
        return join(test_data, filename)

    def test_notebook_as_handle(self):
        project, notebook = parse(self.data_dir('notebook.ipynb'))
        self.assertEqual(project, 'notebook')
        self.assertEqual(notebook, 'notebook')

    def test_filename_without_extension(self):
        project, notebook = parse(self.data_dir('notebook'))
        self.assertEqual(project, 'notebook')
        self.assertEqual(notebook, 'notebook')

    def test_non_existing_file(self):
        with self.assertRaises(errors.NotebookNotExist):
            parse('no-exist.ipynb')

    def test_project_slash_notebook(self):
        project, notebook = parse('project:' + self.data_dir('notebook'))
        self.assertEqual(project, 'project')
        self.assertEqual(notebook, 'notebook')


if __name__ == '__main__':
    unittest.main()
