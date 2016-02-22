import os
import unittest
from binstar_client.utils.detect import is_project


def example_path(example):
    return os.path.join(os.path.dirname(__file__),
                        '../../../example-packages',
                        example)


class IsProjectTestCase(unittest.TestCase):
    def test_python_file(self):
        is_project(example_path('bokeh-apps/timeout.py'))

    def test_dir_project(self):
        is_project(example_path('bokeh-apps/weather'))


if __name__ == '__main__':
    unittest.main()
