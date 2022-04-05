import os
import tempfile
from unittest import TestCase, mock

import yaml

from binstar_client.utils import config


class TestConfigUtils(TestCase):
    CONFIG_DATA = {'ssl_verify': False}

    @mock.patch('binstar_client.utils.config.logger')
    @mock.patch('binstar_client.utils.config.yaml_load', return_value=CONFIG_DATA)
    def test_load_config(self, mock_yaml_load, mock_logger):
        tmp_config = tempfile.NamedTemporaryFile(mode='w')
        config.yaml_dump(self.CONFIG_DATA, tmp_config.file)

        with self.subTest('OK'):
            self.assertEqual(self.CONFIG_DATA, config.load_config(tmp_config.name))
            mock_yaml_load.has_called_once(tmp_config.name)
            mock_logger.warning.assert_not_called()
            mock_logger.exception.assert_not_called()

        mock_yaml_load.reset_mock()
        with self.subTest('yaml.YAMLError'):
            mock_yaml_load.side_effect = yaml.YAMLError
            self.assertEqual({}, config.load_config(tmp_config.name))
            self.assertTrue(os.path.exists(tmp_config.name + '.bak'))
            mock_logger.warning.assert_called()
            mock_logger.exception.assert_not_called()
            os.remove(tmp_config.name + '.bak')

        mock_yaml_load.reset_mock()
        mock_logger.reset_mock()
        with self.subTest('PermissionError'):
            mock_yaml_load.side_effect = PermissionError

            self.assertEqual({}, config.load_config(tmp_config.name))
            mock_logger.warning.assert_not_called()
            mock_logger.exception.assert_called_once()
            self.assertEqual(2, len(mock_logger.exception.call_args.args))

        mock_yaml_load.reset_mock()
        mock_logger.reset_mock()
        with self.subTest('OSError'):
            mock_yaml_load.side_effect = OSError

            self.assertEqual({}, config.load_config(tmp_config.name))
            mock_logger.warning.assert_not_called()
            mock_logger.exception.assert_called_once()
            self.assertEqual(1, len(mock_logger.exception.call_args.args))

        tmp_config.close()

    @mock.patch('binstar_client.utils.config.os.makedirs', wraps=os.makedirs)
    @mock.patch('binstar_client.utils.config.os.replace', wraps=os.replace)
    def test_save_config(self, mock_os_replace, mock_os_makedirs):
        config_filename = 'config.yaml'

        with self.subTest('OK'), tempfile.TemporaryDirectory() as test_config_dir:
            config_path = os.path.join(test_config_dir, config_filename)
            config.save_config(self.CONFIG_DATA, config_path)

            self.assertEqual(self.CONFIG_DATA, config.load_config(config_path))
            mock_os_makedirs.assert_called_once_with(test_config_dir, exist_ok=True)
            mock_os_replace.assert_called_once_with(config_path + '~', config_path)

        mock_os_replace.reset_mock()
        mock_os_makedirs.reset_mock()

        with self.subTest('OSError'), tempfile.TemporaryDirectory() as test_config_dir, \
                mock.patch('binstar_client.utils.config.logger') as mock_logger:
            mock_os_replace.side_effect = OSError

            config_path = os.path.join(test_config_dir, config_filename)
            config.save_config(self.CONFIG_DATA, config_path)

            self.assertFalse(os.path.exists(config_path))
            mock_os_makedirs.assert_called_once_with(test_config_dir, exist_ok=True)
            mock_os_replace.assert_called_once_with(config_path + '~', config_path)
            mock_logger.exception.has_called()
