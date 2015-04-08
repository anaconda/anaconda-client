from __future__ import print_function, unicode_literals

import unittest
from os import path
from binstar_client.inspect_package import conda
from pprint import pprint

def data_path(filename):
    return path.join(path.dirname(__file__), 'data', filename)

expected_package_data = {'license': None,
                         'name': 'conda_gc_test',
                         'summary': 'This is a simple meta-package'}


expected_version_data = {'description': '', 'home_page': None, 'version': '1.2.1'}

expected_file_data = {'attrs': {'arch': 'x86_64',
                               'build': 'py27_3',
                               'build_number': 3,
                               'depends': ['foo ==3*', 'python ==2.7.8'],
                               'license': None,
                               'machine': 'x86_64',
                               'operatingsystem': 'darwin',
                               'platform': 'osx',
                               'subdir': 'osx-64',
                               'target-triplet': 'x86_64-any-darwin'},
                     'basename': 'osx-64/conda_gc_test-1.2.1-py27_3.tar.bz2',
                     'dependencies': {'depends': [{'name': 'foo', 'specs': [['==', '3']]},
                                                  {'name': 'python',
                                                   'specs': [['==', '2.7.8']]}]}}



class Test(unittest.TestCase):


    def test_conda(self):
        filename = data_path('conda_gc_test-1.2.1-py27_3.tar.bz2')
        with open(filename, 'rb') as fd:
            package_data, version_data, file_data = conda.inspect_conda_package(filename, fd)

        self.assertEqual(expected_package_data, package_data)
        self.assertEqual(expected_version_data, version_data)
        self.assertEqual(expected_file_data, file_data)


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
