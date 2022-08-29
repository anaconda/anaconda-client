# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring

from __future__ import unicode_literals

import shutil
import tempfile
from os.path import join, exists

from unittest import mock

from binstar_client.scripts.cli import main
from tests.fixture import CLITestCase


class Test(CLITestCase):
    def test_write_env(self):
        tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmpdir)

        with mock.patch('binstar_client.commands.config.USER_CONFIG', join(tmpdir, 'config.yaml')), \
                mock.patch('binstar_client.commands.config.SEARCH_PATH', [tmpdir]):
            main(['config', '--set', 'url', 'http://localhost:5000'], False)

            self.assertTrue(exists(join(tmpdir, 'config.yaml')))

            with open(join(tmpdir, 'config.yaml'), encoding='utf-8') as conf_file:
                config_output = conf_file.read()
            expected_config_output = 'url: http://localhost:5000\n'
            self.assertEqual(config_output, expected_config_output)

            main(['config', '--show-sources'], False)
            expected_show_sources_output = '==> {config} <==\nurl: http://localhost:5000\n\n'.format(
                config=join(tmpdir, 'config.yaml'))

            self.assertIn(expected_show_sources_output, self.stream.getvalue())
