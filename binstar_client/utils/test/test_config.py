# -*- coding: utf-8 -*-
"""Test anaconda-client configuration set/get."""

# Standard library imports
from os.path import join
import os
import shutil
import tempfile
import unittest

# Third party imports
import mock

# Local imports
from binstar_client.utils import config


class Test(unittest.TestCase):

    def create_config_dirs(self):
        tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmpdir)
        system_dir = join(tmpdir, 'system')
        user_dir = join(tmpdir, 'user')
        os.mkdir(system_dir)
        os.mkdir(user_dir)
        return user_dir, system_dir

    def test_defaults(self):
        user_dir, system_dir = self.create_config_dirs()
        with open(join(user_dir, 'config.yaml'), 'wb') as fd:
            fd.write(b'')

        with mock.patch('binstar_client.utils.config.SEARCH_PATH',
                        [system_dir, user_dir]):
            cfg = config.get_config()
            self.assertEqual(cfg, config.DEFAULT_CONFIG)

    def test_global_url(self):
        """
        Test regression reported on:

        https://github.com/Anaconda-Platform/anaconda-client/issues/464
        """
        user_dir, system_dir = self.create_config_dirs()
        with open(join(user_dir, 'config.yaml'), 'wb') as fd:
            fd.write(b'')

        url_data = {'url': 'https://blob.org'}
        config_data = config.DEFAULT_CONFIG.copy()
        config_data.update(url_data)

        with mock.patch('binstar_client.utils.config.SEARCH_PATH',
                        [system_dir, user_dir]):
            config.save_config(url_data, join(user_dir, 'config.yaml'))
            cfg = config.get_config()
            self.assertEqual(cfg, config_data)

    def test_merge(self):
        user_dir, system_dir = self.create_config_dirs()
        with open(join(system_dir, 'config.yaml'), 'wb') as fd:
            fd.write(b'''
ssl_verify: false
sites:
    develop:
        url: http://develop.anaconda.org
            ''')

        with open(join(user_dir, 'config.yaml'), 'wb') as fd:
            fd.write(b'''
ssl_verify: true
sites:
    develop:
        ssl_verify: false
            ''')

        with mock.patch('binstar_client.utils.config.SEARCH_PATH', [system_dir, user_dir]), \
                mock.patch('binstar_client.utils.config.DEFAULT_CONFIG', {}):
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
        user_dir, system_dir = self.create_config_dirs()
        with open(join(user_dir, 'config.yaml'), 'wb') as fd:
            fd.write(b'''
!!python/unicode 'sites':
   !!python/unicode 'alpha': {!!python/unicode 'url': !!python/unicode 'foobar'}
   !!python/unicode 'binstar': {!!python/unicode 'url': !!python/unicode 'barfoo'}
ssl_verify: False
''')

        with mock.patch('binstar_client.utils.config.SEARCH_PATH', [user_dir]), \
                mock.patch('binstar_client.utils.config.DEFAULT_CONFIG', {}):
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
