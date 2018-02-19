from os.path import join
import os
import unittest
import inspect
import shutil
import tempfile

import mock

from binstar_client.utils import config


class Test(unittest.TestCase):
    def test_merge(self):
        tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmpdir)

        system_dir = join(tmpdir, 'system')
        user_dir = join(tmpdir, 'user')
        os.mkdir(system_dir)
        os.mkdir(user_dir)

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
