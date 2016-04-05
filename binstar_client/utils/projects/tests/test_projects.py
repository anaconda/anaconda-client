import unittest
from binstar_client.utils.test.utils import example_path
from binstar_client.utils.projects import get_files


def test_get_files():
    pfiles = get_files(example_path('bokeh-apps/weather'))
    assert len(pfiles) == 5
    assert pfiles[0]['basename'] == '.projectignore'
    assert pfiles[0]['relativepath'] == '.projectignore'
    assert pfiles[0]['size'] == 23


if __name__ == '__main__':
    unittest.main()
