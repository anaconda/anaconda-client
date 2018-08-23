from __future__ import print_function, unicode_literals
import os
import shutil
import tempfile
import unittest
from pprint import pprint

from binstar_client.inspect_package import pypi
from binstar_client.utils.test.utils import data_dir


expected_package_data = {'name': 'test-package34',
                         'license': 'custom',
                         'summary': 'Python test package for binstar client'}

expected_version_data = {'home_page': 'http://github.com/binstar/binstar_pypi',
                         'version': '0.3.1',
                         'description':'longer description of the package'}

expected_dependencies = {'depends': [ {'name': u'python-dateutil', 'specs': []},
                                      {'name': u'pytz', 'specs': []},
                                      {'name': u'pyyaml', 'specs': []},
                                      {'name': u'requests', 'specs': [(u'>=', u'2.0'), (u'<=', u'3.0')]}, ],
                          'extras': [{'depends': [{'name': u'argparse',
                                                   'specs': []}],
                                      'name': u':python_version=="2.6"'},
                                     {'depends': [{'name': u'reportlab',
                                                   'specs': [(u'>=', u'1.2')]},
                                                  {'name': u'rxp', 'specs': []}],
                                      'name': u'PDF'},
                                     {'depends': [{'name': u'docutils',
                                                   'specs': [(u'>=', u'0.3')]}],
                                      'name': u'reST'}],
                          'has_dep_errors': False}

expected_whl_dependencies = {u'depends': [{u'name': u'python-dateutil', u'specs': []},
                                          {u'name': u'pytz', u'specs': []},
                                          {u'name': u'pyyaml', u'specs': []},
                                          {u'name': u'requests',
                                             u'specs': [(u'>=', u'2.0'),
                                                        (u'<=', u'3.0')]}],
                               u'environments': [{u'depends': [{u'name': u'argparse',
                                                                u'specs': []}],
                                                  u'name': u'python_version=="2.6"'}],
                               u'extras': [{u'depends': [{u'name': u'reportlab',
                                                          u'specs': [(u'>=', u'1.2')]},
                                                         {u'name': u'rxp',
                                                          u'specs': []},
                                                         ],
                                            u'name': u'PDF'},
                                           {u'depends': [{u'name': u'docutils',
                                                          u'specs': [(u'>=', u'0.3')]}],
                                            u'name': u'reST'}],
                               u'has_dep_errors': False}

expected_egg_file_data = {'attrs': {'packagetype': 'bdist_egg', 'python_version': 'source'},
                          'basename': 'test_package34-0.3.1-py2.7.egg',
                          'dependencies': expected_dependencies,
                          'platform': None}

class Test(unittest.TestCase):

    maxDiff = None
    def test_sdist(self):
        filename = data_dir('test_package34-0.3.1.tar.gz')
        with open(filename, 'rb') as fd:
            package_data, version_data, file_data = pypi.inspect_pypi_package(filename, fd)


        expected_file_data = {'attrs': {'packagetype': 'sdist', 'python_version': 'source'},
                              'basename': 'test_package34-0.3.1.tar.gz',
                              'dependencies': expected_dependencies}

        self.assertEqual(expected_package_data, package_data)
        self.assertEqual(expected_version_data, version_data)

        self.assertEqual(set(expected_file_data), set(file_data))
        for key in expected_file_data:
            self.assertEqual(expected_file_data[key], file_data[key])

    def test_bdist_wheel(self):
        filename = data_dir('test_package34-0.3.1-py2-none-any.whl')

        with open(filename, 'rb') as fd:
            package_data, version_data, file_data = pypi.inspect_pypi_package(filename, fd)

        expected_file_data = {'attrs': {'abi': None, 'build_no': 0,
                                        'packagetype': 'bdist_wheel',
                                        'python_version': 'py2'},
                             'basename': 'test_package34-0.3.1-py2-none-any.whl',
                             'dependencies': expected_whl_dependencies,
                             'platform': None}

        self.assertEqual(expected_package_data, package_data)
        self.assertEqual(expected_version_data, version_data)

        self.assertEqual(set(expected_file_data), set(file_data))
        for key in expected_file_data:
            print(expected_file_data[key])
            print(file_data[key])
            self.assertEqual(expected_file_data[key], file_data[key])

    def test_bdist_wheel_newer_version(self):
        filename_whl = 'azure_cli_extension-0.2.1-py2.py3-none-any.whl'
        filename = data_dir(filename_whl)

        with open(filename, 'rb') as fd:
            package_data, version_data, file_data = pypi.inspect_pypi_package(filename, fd)

        expected_file_data = {
            'platform': None,
            'basename': filename_whl,
            'dependencies': {
                u'depends': [
                    {u'name': u'azure-cli-command-modules-nspkg', u'specs': [(u'>=', u'2.0.0')]},
                    {u'name': u'azure-cli-core', u'specs': []}, {u'name': u'pip', u'specs': []},
                    {u'name': u'wheel', u'specs': [(u'==', u'0.30.0')]}
                ],
                u'extras': [],
                u'has_dep_errors': False,
                u'environments': []},
            u'attrs': {
                'abi': None,
                'packagetype': u'bdist_wheel',
                'python_version': u'py2.py3',
                'build_no': 0
            }
        }
        expected_package_data = {
            u'name': 'azure-cli-extension',
            u'license': 'MIT',
            u'summary': 'Microsoft Azure Command-Line Tools Extension Command Module',
        }
        expected_version_data = {
            u'home_page': 'https://github.com/Azure/azure-cli',
            u'version': '0.2.1',
            u'description': u"Microsoft Azure CLI 'extension' Command Module",
        }
        self.assertEqual(expected_package_data, package_data)
        self.assertEqual(expected_version_data, version_data)
        self.assertEqual(set(expected_file_data), set(file_data))
        for key in expected_file_data:
            print(expected_file_data[key])
            print(file_data[key])
            self.assertEqual(expected_file_data[key], file_data[key])

    def test_bdist_egg(self):
        filename = data_dir('test_package34-0.3.1-py2.7.egg')

        with open(filename, 'rb') as fd:
            package_data, version_data, file_data = pypi.inspect_pypi_package(filename, fd)


        self.assertEqual(expected_package_data, package_data)
        self.assertEqual(expected_version_data, version_data)

        self.assertEqual(set(expected_egg_file_data), set(file_data))
        for key in expected_egg_file_data:
            self.assertEqual(expected_egg_file_data[key], file_data[key])

    def test_bdist_egg_dashed_path(self):
        filename = data_dir('test_package34-0.3.1-py2.7.egg')
        tmpdir = tempfile.gettempdir()
        dash_count = tmpdir.count('-')
        if dash_count == 0:
            tmpdir = os.path.join(tmpdir, 'has-dash')
            try:
                os.mkdir(tmpdir)
            except (IOError, OSError):
                raise unittest.SkipTest('Cannot create temporary directory %r' % tmpdir)
        elif dash_count > 1:
            raise unittest.SkipTest('Too many dashes in temporary directory path %r' % tmpdir)

        try:
            shutil.copy(filename, tmpdir)
        except (IOError, OSError):
            raise unittest.SkipTest('Cannot copy package to temporary directory')

        tmpfilename = os.path.join(tmpdir, 'test_package34-0.3.1-py2.7.egg')

        with open(tmpfilename, 'rb') as fd:
            package_data, version_data, file_data = pypi.inspect_pypi_package(tmpfilename, fd)

        # If we could create this file, we ought to be able to delete it
        os.remove(tmpfilename)
        if dash_count == 0:
            # We created a temporary directory like /tmp/has-dash, delete it
            os.rmdir(tmpdir)

        self.assertEqual(expected_package_data, package_data)
        self.assertEqual(expected_version_data, version_data)

        self.assertEqual(set(expected_egg_file_data), set(file_data))
        self.assertEqual(expected_egg_file_data['platform'], file_data['platform'])
        self.assertEqual(expected_egg_file_data['attrs']['python_version'],
                         file_data['attrs']['python_version'])

    def test_sdist_distutils(self):
        filename = data_dir('test_package34-distutils-0.3.1.tar.gz')
        with open(filename, 'rb') as fd:
            package_data, version_data, file_data = pypi.inspect_pypi_package(filename, fd)


        expected_file_data = {'attrs': {'packagetype': 'sdist', 'python_version': 'source'},
                              'basename': 'test_package34-distutils-0.3.1.tar.gz',
                              'dependencies': {'depends': [{'name': 'requests',
                                                            'specs': [('>=', '2.0'), ('<=', '3.0')]},
                                                           {'name': 'pyyaml', 'specs': [('==', '2.0')]},
                                                           {'name': 'pytz', 'specs': []}],
                                               'extras': [],
                                               'has_dep_errors': False}}

        dexpected_package_data = expected_package_data.copy()
        dexpected_package_data['name'] = dexpected_package_data['name'].replace('-', '_')
        self.assertEqual(dexpected_package_data, package_data)
        self.assertEqual(expected_version_data, version_data)
        self.assertEqual(set(expected_file_data), set(file_data))

        for key in expected_file_data:
            print(expected_file_data[key])
            print(file_data[key])
            self.assertEqual(expected_file_data[key], file_data[key])



if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
