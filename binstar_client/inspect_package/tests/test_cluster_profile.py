from __future__ import print_function, unicode_literals

import unittest
from os import path
from binstar_client.inspect_package import profile
from pprint import pprint

def data_path(filename):
    return path.join(path.dirname(__file__), 'data', filename)

expected_package_data = {'name': 'test_profile',
                         'summary': 'Anaconda Cluster Profile'}


expected_version_data = {'version': 1.0, 'description': ''}

expected_file_data = {'attrs': {'test_profile':
                                        {'node_type': 'm1.medium',
                                        'node_id': 'ami-08faa660',
                                        'user': 'ubuntu',
                                        'provider': 'aws_east',
                                        'plugins': [{'notebook': {'directory': '/opt/notebooks',
                                                                  'password': 1234,
                                                                  'port': 8800}}],
                                        'num_nodes': 3}},
                     'basename': 'test_profile.yaml',
                     }




class Test(unittest.TestCase):


    def test_profile(self):
        filename = data_path('test_profile.yaml')
        with open(filename, 'rb') as fd:
            package_data, version_data, file_data = profile.inspect_profile_package(filename, fd)

        self.assertEqual(expected_package_data, package_data)
        self.assertEqual(expected_version_data, version_data)
        self.assertEqual(expected_file_data, file_data)


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
