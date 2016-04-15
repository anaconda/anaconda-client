import unittest
from binstar_client.utils.test.utils import example_path
from binstar_client.utils.detect import is_project


class IsProjectTestCase(unittest.TestCase):
    def test_python_file(self):
        is_project(example_path('bokeh-apps/timeout.py'))

    def test_dir_project(self):
        is_project(example_path('bokeh-apps/weather'))


if __name__ == '__main__':
    unittest.main()
