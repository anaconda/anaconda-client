'''
Created on Feb 22, 2014

@author: sean
'''
import logging
import io
import unittest
import mock

from binstar_client import tests


class AnyIO(io.StringIO):
    def write(self, msg):
        if hasattr('msg', 'decode'):
            msg = msg.decode()
        return io.StringIO.write(self, msg)


class CLITestCase(unittest.TestCase):
    def setUp(self):
        self.get_config_patch = mock.patch('binstar_client.utils.get_config')
        self.get_config = self.get_config_patch.start()
        self.get_config.return_value = {}

        self.load_token_patch = mock.patch('binstar_client.utils.config.load_token')
        self.load_token = self.load_token_patch.start()
        self.load_token.return_value = '123'

        self.store_token_patch = mock.patch('binstar_client.utils.config.store_token')
        self.store_token = self.store_token_patch.start()

        self.setup_logging_patch = mock.patch('binstar_client.scripts.cli._setup_logging')
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
