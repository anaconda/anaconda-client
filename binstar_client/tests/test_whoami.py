'''
Created on Feb 18, 2014

@author: sean
'''
import unittest
import mock
from binstar_client.scripts.cli import main
import logging
import io
from binstar_client import errors
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
        
    @mock.patch('binstar_client.Binstar.session')
    def test_whoami_anon(self, session):
        
        session.get().status_code = 401 
        main(['--show-traceback', 'whoami'], False)
        self.assertIn('Anonymous User', self.stream.getvalue()) 
        
    @mock.patch('binstar_client.Binstar.session')
    def test_whoami(self, session):
        
        session.get().status_code = 200
        session.get().json.return_value = {'login': 'eggs', 'created_at':'1/2/2000'}
         
        main(['--show-traceback', 'whoami'], False)
        self.assertIn('eggs', self.stream.getvalue()) 

        
        
if __name__ == '__main__':
    unittest.main()
