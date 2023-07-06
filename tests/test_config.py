# -*- coding: utf8 -*-
# pylint: disable=missing-function-docstring

"""Tests for configuration management."""

import shutil
import tempfile
import os
import unittest.mock

from tests.fixture import CLITestCase, main


class Test(CLITestCase):
    """Tests for configuration management."""

    def test_write_env(self):
        tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmpdir)

        with unittest.mock.patch('binstar_client.commands.config.USER_CONFIG', os.path.join(tmpdir, 'config.yaml')), \
                unittest.mock.patch('binstar_client.commands.config.SEARCH_PATH', [tmpdir]):
            main(['config', '--set', 'url', 'http://localhost:5000'])

            self.assertTrue(os.path.exists(os.path.join(tmpdir, 'config.yaml')))

            with open(os.path.join(tmpdir, 'config.yaml'), encoding='utf-8') as conf_file:
                config_output = conf_file.read()
            expected_config_output = 'url: http://localhost:5000\n'
            self.assertEqual(config_output, expected_config_output)

            main(['config', '--show-sources'])
            expected_show_sources_output = '==> {config} <==\nurl: http://localhost:5000\n\n'.format(
                config=os.path.join(tmpdir, 'config.yaml'),
            )

            self.assertIn(expected_show_sources_output, self.stream.getvalue())
