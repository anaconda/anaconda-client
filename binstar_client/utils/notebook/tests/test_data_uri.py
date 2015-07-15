import unittest
from os.path import join, dirname
from binstar_client.utils.notebook.data_uri import DataURIConverter


class DataURIConverterTestCase(unittest.TestCase):
    def data_dir(self, filename):
        test_data = join(dirname(__file__), 'data')
        return join(test_data, filename)

    def test_local_image(self):
        location = self.data_dir('bokeh-logo.png')
        output = DataURIConverter(location)()
        self.assertEqual(output[0:5], "iVBOR")

    def test_remote_image(self):
        location = 'http://continuum.io/media/img/anaconda_server_logo.png'
        output = DataURIConverter(location)()
        self.assertEqual(output[0:5], "iVBOR")

    def test_file_not_found(self):
        location = self.data_dir('no-exists.png')
        with self.assertRaises(IOError):
            DataURIConverter(location)()

    def test_is_python_3(self):
        output = DataURIConverter('')
        self.assertIsInstance(output.is_py3(), bool)

    def test_is_url(self):
        location = 'http://docs.continuum.io/_static/img/continuum_analytics_logo.png'
        self.assertTrue(DataURIConverter(location).is_url())

        location = self.data_dir('bokeh-logo.png')
        self.assertNotEqual(DataURIConverter(location).is_url(), True)
