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
import json

requests.Response
test_data = join(dirname(tests.__file__), 'data')


class Test(unittest.TestCase):
    
    def setUp(self):
        
        self.setup_logging_patch = mock.patch('binstar_client.scripts.cli.setup_logging')
        self.setup_logging_patch.start()
        
        logger = logging.getLogger('binstar')
        logger.setLevel(logging.INFO)
        self.stream = io.StringIO()
        hndlr = logging.StreamHandler(stream=self.stream)
        hndlr.setLevel(logging.INFO)
        logger.addHandler(hndlr)
        
    def tearDown(self):
        self.setup_logging_patch.stop()
        
    @urlpatch
    def test_register_public(self, registry):
        
        r1 = registry.register(method='GET', path='/api/user', content='{"login": "eggs"}')
        r2 = registry.register(method='GET', path='/api/package/eggs/foo', status=404)
        r3 = registry.register(method='POST', path='/api/package/eggs/foo', status=200, content='{"login": "eggs"}')
        
        main(['--show-traceback', 'register', join(test_data, 'foo-0.1-0.tar.bz2')], False)
        
        r1.assertCalled()
        r2.assertCalled()
        r3.assertCalled()
        
        data = json.loads(r3.req.body.decode('base64'))
        self.assertTrue(data['public'])
        self.assertFalse(data['publish'])

    @urlpatch
    def test_register_private(self, registry):
        
        r1 = registry.register(method='GET', path='/api/user', content='{"login": "eggs"}')
        r2 = registry.register(method='GET', path='/api/package/eggs/foo', status=404)
        r3 = registry.register(method='POST', path='/api/package/eggs/foo', status=200, content='{"login": "eggs"}')
        
        main(['--show-traceback', 'register', '--private', join(test_data, 'foo-0.1-0.tar.bz2')], False)
        
        r1.assertCalled()
        r2.assertCalled()
        r3.assertCalled()
        
        data = json.loads(r3.req.body.decode('base64'))
        self.assertFalse(data['public'])
        self.assertFalse(data['publish'])
        
    @urlpatch
    def test_register_publish(self, registry):
        
        r1 = registry.register(method='GET', path='/api/user', content='{"login": "eggs"}')
        r2 = registry.register(method='GET', path='/api/package/eggs/foo', status=404)
        r3 = registry.register(method='POST', path='/api/package/eggs/foo', status=200, content='{"login": "eggs"}')
        
        main(['--show-traceback', 'register', '--publish', join(test_data, 'foo-0.1-0.tar.bz2')], False)
        
        r1.assertCalled()
        r2.assertCalled()
        r3.assertCalled()
        
        data = json.loads(r3.req.body.decode('base64'))
        self.assertTrue(data['public'])
        self.assertTrue(data['publish'])

    @urlpatch
    def test_register_bad_args(self, registry):
        
        r1 = registry.register()
        with self.assertRaises(SystemExit):
            main(['--show-traceback', 'register', '--publish', '--private', 
                  join(test_data, 'foo-0.1-0.tar.bz2')], False)
        
        
if __name__ == '__main__':
    unittest.main()
