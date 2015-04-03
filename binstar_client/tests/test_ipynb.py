'''
Created on Mar 02, 2014

@author: malev
'''
from __future__ import unicode_literals
import unittest
from binstar_client.tests.fixture import CLITestCase
from binstar_client.inspect_package.ipynb import inspect_ipynb_package


class Test(CLITestCase):
    def test_inspect_ipynb_3_package(self):
        with open(self.data_dir('test-3.0.ipynb')) as fileobj:
            package_data, release_data, file_data = inspect_ipynb_package('test.ipynb', fileobj)

        self.assertEqual({
            'name': 'test',
            'summary': 'IPython notebook'
        },package_data)

        self.assertEqual({
            'version': '1.0',
            'description': ''
        }, release_data)

        self.assertEqual({
            'basename': 'test.ipynb',
            'attrs': {}
        }, file_data)

    def test_inspect_ipynb_2_package(self):
        with open(self.data_dir('test-2.0.ipynb')) as fileobj:
            package_data, release_data, file_data = inspect_ipynb_package('test.ipynb', fileobj)

        self.assertEqual({
            'name': 'test',
            'summary': 'IPython notebook'
        },package_data)

        self.assertEqual({
            'version': '1.0',
            'description': ''
        }, release_data)

        self.assertEqual({
            'basename': 'test.ipynb',
            'attrs': {}
        }, file_data)


if __name__ == '__main__':
    unittest.main()
