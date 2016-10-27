from os.path import join
import os
import unittest
import inspect
import shutil
import tempfile

import mock

from binstar_client.utils import config


class Test(unittest.TestCase):
    def test_signature(self):
        from binstar_client.utils import get_config, set_config

        # make sure that our exported methods have the same interface
        spec = inspect.getargspec(get_config)
        self.assertEqual(spec.args, ['user', 'site', 'remote_site'])
        self.assertEqual(spec.defaults, (True, True, None))

        spec = inspect.getargspec(set_config)
        self.assertEqual(spec.args, ['data', 'user'])
        self.assertEqual(spec.defaults, (True,))

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



