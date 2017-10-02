import unittest

from binstar_client.utils.notebook.data_uri import DataURIConverter
from binstar_client.utils.test.utils import data_dir


class DataURIConverterTestCase(unittest.TestCase):
    def test_local_image(self):
        location = data_dir('bokeh-logo.png')
        output = DataURIConverter(location)()
        self.assertEqual(output[0:5], "iVBOR")

    def test_file_not_found(self):
        location = data_dir('no-exists.png')
        with self.assertRaises(IOError):
            DataURIConverter(location)()

    def test_is_python_3(self):
        output = DataURIConverter('')
        self.assertIsInstance(output.is_py3(), bool)

    def test_is_url(self):
        location = 'http://docs.continuum.io/_static/img/continuum_analytics_logo.png'
        self.assertTrue(DataURIConverter(location).is_url())

        location = data_dir('bokeh-logo.png')
        self.assertNotEqual(DataURIConverter(location).is_url(), True)
