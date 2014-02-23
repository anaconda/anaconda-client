'''
Created on Feb 18, 2014

@author: sean
'''
import unittest
import mock
from binstar_client.scripts.cli import main
import logging
import io
from os.path import join, dirname
from binstar_client import tests
import requests
from binstar_client.tests.urlmock import urlpatch

requests.Response
test_data = join(dirname(tests.__file__), 'data')


class Test(unittest.TestCase):
    
    def setUp(self):
        
        self.setup_logging_patch = mock.patch('binstar_client.scripts.cli.setup_logging')
        self.setup_logging_patch.start()
        
        logger = logging.getLogger('binstar')
        logger.setLevel(logging.INFO)
        self.stream = io.BytesIO()
        hndlr = logging.StreamHandler(stream=self.stream)
        hndlr.setLevel(logging.INFO)
        logger.addHandler(hndlr)
        
    def tearDown(self):
        self.setup_logging_patch.stop()
        
    @urlpatch
    def test_register(self, registry):
        
        print registry.register(method='GET', path='/api/user', content='{"login": "eggs"}')
        print registry.register(method='GET', path='/api/package/eggs/foo', status=404)
        
        print registry.register(method='POST', path='/api/package/eggs/foo', status=200, content='{"login": "eggs"}')
        
        main(['--show-traceback', 'register', join(test_data, 'foo-0.1-0.tar.bz2')], False)
        
        
        
if __name__ == '__main__':
    unittest.main()
