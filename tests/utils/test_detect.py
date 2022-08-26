# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring

import unittest

from binstar_client.utils.detect import is_project
from tests.utils.utils import example_path


class IsProjectTestCase(unittest.TestCase):
    def test_python_file(self):
        is_project(example_path('bokeh-apps/timeout.py'))

    def test_dir_project(self):
        is_project(example_path('bokeh-apps/weather'))


if __name__ == '__main__':
    unittest.main()
