# -*- coding: utf-8 -*-

# pylint: disable=unspecified-encoding,missing-module-docstring,missing-class-docstring,missing-function-docstring

from __future__ import unicode_literals

import unittest

from collections import namedtuple

from freezegun import freeze_time

from binstar_client.inspect_package.ipynb import inspect_ipynb_package
from tests.utils.utils import data_dir


class InspectIPYNBPackageTest(unittest.TestCase):
    def test_package_data(self):
        with open(data_dir('notebook.ipynb')) as file:
            package_data, _, _ = inspect_ipynb_package('notebook.ipynb', file)

        self.assertEqual({
            'name': 'notebook',
            'description': 'ipynb description',
            'summary': 'ipynb summary',
        }, package_data)

    def test_package_data_no_metadata(self):
        with open(data_dir('notebook-no-metadata.ipynb')) as file:
            package_data, _, _ = inspect_ipynb_package('notebook.ipynb', file)

        self.assertEqual({
            'name': 'notebook',
            'description': 'Jupyter Notebook',
            'summary': 'Jupyter Notebook',
        }, package_data)

    def test_package_data_normalized_name(self):
        with open(data_dir('notebook.ipynb')) as file:
            package_data, _, _ = inspect_ipynb_package('test nótëbOOk.ipynb', file)

        self.assertIn('name', package_data)
        self.assertEqual(package_data['name'], 'test-notebook')

    def test_package_thumbnail(self):
        parser_args = namedtuple('parser_args', ['thumbnail'])(data_dir('43c9b994a4d96f779dad87219d645c9f.png'))
        with open(data_dir('notebook.ipynb')) as file:
            package_data, _, _ = inspect_ipynb_package('notebook.ipynb', file, parser_args=parser_args)

        self.assertIn('thumbnail', package_data)

    def test_release_data(self):
        with freeze_time('2018-02-01 09:10:00', tz_offset=0):
            with open(data_dir('notebook.ipynb')) as file:
                _, release_data, _ = inspect_ipynb_package('notebook.ipynb', file)

        self.assertEqual({
            'version': '2018.02.01.0910',
            'description': 'ipynb description',
            'summary': 'ipynb summary',
        }, release_data)

    def test_release_data_no_metadata(self):
        with freeze_time('2018-05-03 12:30:00', tz_offset=0):
            with open(data_dir('notebook-no-metadata.ipynb')) as file:
                _, release_data, _ = inspect_ipynb_package('notebook-no-metadata.ipynb', file)

        self.assertEqual({
            'version': '2018.05.03.1230',
            'description': 'Jupyter Notebook',
            'summary': 'Jupyter Notebook',
        }, release_data)

    def test_file_data(self):
        with open(data_dir('notebook.ipynb')) as file:
            _, _, file_data = inspect_ipynb_package('notebook.ipynb', file)

        self.assertEqual({
            'basename': 'notebook.ipynb',
            'attrs': {}
        }, file_data)
