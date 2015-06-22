import unittest
from os.path import join, dirname
from binstar_client.utils.notebook import DataURIConverter


class DataURIConverterTestCase(unittest.TestCase):
    def data_dir(self, filename):
        test_data = join(dirname(__file__), 'data')
        return join(test_data, filename)

    def test_local_image(self):
        location = self.data_dir('bokeh-logo.png')
        output = DataURIConverter(location)()
        self.assertEqual(output[0:24], "data:image/png;base64,iV")

    def test_remote_image(self):
        location = 'http://docs.continuum.io/_static/img/continuum_analytics_logo.png'
        output = DataURIConverter(location)()
        self.assertEqual(output[0:24], "data:image/png;base64,77")
