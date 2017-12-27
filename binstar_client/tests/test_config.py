from __future__ import unicode_literals

from os.path import join, exists
import os
import unittest
import shutil
import tempfile
import subprocess
import sys

from binstar_client.scripts import cli
from binstar_client.tests.fixture import CLITestCase


class Test(CLITestCase):

    def test_write_env(self):
        tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmpdir)

        env = dict(os.environ)
        env['BINSTAR_CONFIG_DIR'] = str(tmpdir)

        def main(*args):
            return subprocess.check_output((sys.executable, cli.__file__) + args, env=env)

        main('config', '--set', 'url', 'http://localhost:5000')

        self.assertTrue(exists(join(tmpdir, 'data')))
        self.assertTrue(exists(join(tmpdir, 'data', 'config.yaml')))

        with open(join(tmpdir, 'data', 'config.yaml')) as f:
            config_output = f.read()
        expected_config_output = 'url: http://localhost:5000\n'
        self.assertEqual(config_output, expected_config_output)

        show_sources_output = main('config', '--show-sources')
        expected_show_sources_output = '==> {config} <==\nurl: http://localhost:5000\n\n'.format(
            config=join(tmpdir, 'data', 'config.yaml')).encode('utf-8')

        self.assertEqual(show_sources_output, expected_show_sources_output)


if __name__ == '__main__':
    unittest.main()
