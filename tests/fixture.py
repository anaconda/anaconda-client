# -*- coding: utf8 -*-

"""Base components to use in tests."""

from __future__ import annotations

__all__ = ['main', 'AnyIO', 'CLITestCase']

import io
import logging
import typing
import unittest.mock

from binstar_client.scripts import cli


def main(args: typing.Sequence[str]) -> None:
    """Alternative entrypoint to use in tests."""
    cli.main(args, allow_plugin_main=False, exit_=False)


class AnyIO(io.StringIO):  # pylint: disable=missing-class-docstring

    def write(self, msg):
        if hasattr('msg', 'decode'):
            msg = msg.decode()
        return io.StringIO.write(self, msg)


class CLITestCase(unittest.TestCase):  # pylint: disable=too-many-instance-attributes,missing-class-docstring

    def setUp(self):
        self.get_config_patch = unittest.mock.patch('binstar_client.utils.get_config')
        self.get_config = self.get_config_patch.start()
        self.get_config.return_value = {}

        self.load_token_patch = unittest.mock.patch('binstar_client.utils.config.load_token')
        self.load_token = self.load_token_patch.start()
        self.load_token.return_value = '123'

        self.store_token_patch = unittest.mock.patch('binstar_client.utils.config.store_token')
        self.store_token = self.store_token_patch.start()

        self.setup_logging_patch = unittest.mock.patch('binstar_client.utils.logging_utils.setup_logging')
        self.setup_logging_patch.start()

        self.logger = logger = logging.getLogger('binstar')
        logger.setLevel(logging.INFO)
        self.stream = AnyIO()
        self.hndlr = hndlr = logging.StreamHandler(stream=self.stream)
        hndlr.setLevel(logging.INFO)
        logger.addHandler(hndlr)

    def tearDown(self):
        self.setup_logging_patch.stop()
        self.get_config_patch.stop()
        self.load_token_patch.stop()
        self.store_token_patch.stop()

        self.logger.removeHandler(self.hndlr)
