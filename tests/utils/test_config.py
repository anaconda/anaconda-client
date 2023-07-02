# -*- coding: utf8 -*-
# pylint: disable=missing-class-docstring,missing-function-docstring

"""Test anaconda-client configuration set/get."""

from __future__ import annotations

__all__ = ()

import os
import shutil
import tempfile
import unittest.mock

import yaml

from binstar_client.errors import BinstarError
from binstar_client.utils import config


class Test(unittest.TestCase):
    CONFIG_DATA = {'ssl_verify': False}  # pylint: disable=invalid-name

    def create_config_dirs(self):
        tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmpdir)
        system_dir = os.path.join(tmpdir, 'system')
        user_dir = os.path.join(tmpdir, 'user')
        os.mkdir(system_dir)
        os.mkdir(user_dir)
        return user_dir, system_dir

    def test_defaults(self):
        user_dir, system_dir = self.create_config_dirs()
        with open(os.path.join(user_dir, 'config.yaml'), 'wb') as file:
            file.write(b'')

        with unittest.mock.patch('binstar_client.utils.config.SEARCH_PATH', [system_dir, user_dir]):
            cfg = config.get_config()
            self.assertEqual(cfg, config.DEFAULT_CONFIG)

    def test_global_url(self):
        """
        Test regression reported on:

        https://github.com/Anaconda-Platform/anaconda-client/issues/464
        """
        user_dir, system_dir = self.create_config_dirs()
        with open(os.path.join(user_dir, 'config.yaml'), 'wb') as file:
            file.write(b'')

        url_data = {'url': 'https://blob.org'}
        config_data = config.DEFAULT_CONFIG.copy()
        config_data.update(url_data)

        with unittest.mock.patch('binstar_client.utils.config.SEARCH_PATH', [system_dir, user_dir]):
            config.save_config(url_data, os.path.join(user_dir, 'config.yaml'))
            cfg = config.get_config()
            self.assertEqual(cfg, config_data)

    def test_merge(self):
        user_dir, system_dir = self.create_config_dirs()
        with open(os.path.join(system_dir, 'config.yaml'), 'wb') as file:
            file.write(b'''
ssl_verify: false
sites:
    develop:
        url: http://develop.anaconda.org
            ''')

        with open(os.path.join(user_dir, 'config.yaml'), 'wb') as file:
            file.write(b'''
ssl_verify: true
sites:
    develop:
        ssl_verify: false
            ''')

        with unittest.mock.patch('binstar_client.utils.config.SEARCH_PATH', [system_dir, user_dir]), \
                unittest.mock.patch('binstar_client.utils.config.DEFAULT_CONFIG', {}):
            cfg = config.get_config()

            self.assertEqual(cfg, {
                'ssl_verify': True,
                'sites': {
                    'develop': {
                        'url': 'http://develop.anaconda.org',
                        'ssl_verify': False,
                    }
                }
            })

    def test_support_tags(self):
        user_dir, system_dir = self.create_config_dirs()  # pylint: disable=unused-variable

        with open(os.path.join(user_dir, 'config.yaml'), 'wb') as file:
            file.write(b'''
!!python/unicode 'sites':
   !!python/unicode 'alpha': {!!python/unicode 'url': !!python/unicode 'foobar'}
   !!python/unicode 'binstar': {!!python/unicode 'url': !!python/unicode 'barfoo'}
ssl_verify: False
''')

        with unittest.mock.patch('binstar_client.utils.config.SEARCH_PATH', [user_dir]), \
                unittest.mock.patch('binstar_client.utils.config.DEFAULT_CONFIG', {}):
            cfg = config.get_config()

            self.assertEqual(cfg, {
                'ssl_verify': False,
                'sites': {
                    'alpha': {
                        'url': 'foobar',
                    },
                    'binstar': {
                        'url': 'barfoo',
                    },
                }
            })

    @unittest.mock.patch('binstar_client.utils.config.warnings')
    @unittest.mock.patch('binstar_client.utils.config.yaml_load', wraps=config.yaml_load)
    def test_load_config(self, mock_yaml_load, mock_warnings):
        tmpdir = tempfile.mkdtemp()
        tmp_config = os.path.join(tmpdir, 'config.yaml')

        with open(tmp_config, 'w', encoding='utf-8') as file:
            config.yaml_dump(self.CONFIG_DATA, file)

        with self.subTest('OK'):
            self.assertEqual(self.CONFIG_DATA, config.load_config(tmp_config))
            mock_warnings.warn.assert_not_called()

        with self.subTest('yaml.YAMLError'):
            mock_yaml_load.side_effect = yaml.YAMLError
            self.assertEqual({}, config.load_config(tmp_config))
            self.assertTrue(os.path.exists(tmp_config + '.bak'))
            os.remove(tmp_config + '.bak')
            mock_warnings.warn.assert_called()

        mock_warnings.reset_mock()
        with self.subTest('PermissionError'):
            mock_yaml_load.side_effect = PermissionError

            self.assertEqual({}, config.load_config(tmp_config))
            mock_warnings.warn.assert_called()

        mock_warnings.reset_mock()
        with self.subTest('OSError'):
            mock_yaml_load.side_effect = OSError

            self.assertEqual({}, config.load_config(tmp_config))
            mock_warnings.warn.assert_not_called()

        shutil.rmtree(tmpdir)

    @unittest.mock.patch('binstar_client.utils.config.os.makedirs', wraps=os.makedirs)
    @unittest.mock.patch('binstar_client.utils.config.os.replace', wraps=os.replace)
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

        with self.subTest('OSError'), tempfile.TemporaryDirectory() as test_config_dir:
            mock_os_replace.side_effect = OSError

            config_path = os.path.join(test_config_dir, config_filename)
            with self.assertRaises(BinstarError):
                config.save_config(self.CONFIG_DATA, config_path)

            self.assertFalse(os.path.exists(config_path))
            mock_os_makedirs.assert_called_once_with(test_config_dir, exist_ok=True)
            mock_os_replace.assert_called_once_with(config_path + '~', config_path)
