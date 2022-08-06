# pylint: disable=unspecified-encoding,missing-module-docstring,missing-class-docstring,missing-function-docstring

import unittest

from tests.utils.utils import data_dir
from binstar_client.inspect_package.env import EnvInspector, inspect_env_package


class EnvInspectorTestCase(unittest.TestCase):
    def test_package_name(self):
        with open(data_dir('environment.yml')) as fileobj:
            assert EnvInspector('environment.yml', fileobj).name == 'stats'  # nosec

    def test_version(self):
        with open(data_dir('environment.yml')) as fileobj:
            self.assertIsInstance(EnvInspector('environment.yml', fileobj).version, str)


class InspectEnvironmentPackageTest(unittest.TestCase):
    def test_inspect_env_package(self):
        with open(data_dir('environment.yml')) as fileobj:
            package_data, release_data, file_data = inspect_env_package(  # pylint: disable=unused-variable
                'environment.yml', fileobj)

        self.assertEqual({
            'name': 'stats',
            'summary': 'Environment file'
        }, package_data)

        self.assertEqual({
            'basename': 'environment.yml',
            'attrs': {}
        }, file_data)


if __name__ == '__main__':
    unittest.main()
