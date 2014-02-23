'''
Created on Feb 18, 2014

@author: sean
'''
from __future__ import unicode_literals
import unittest
import mock
from binstar_client.scripts.cli import main
from binstar_client.tests.fixture import CLITestCase
from binstar_client.tests.urlmock import urlpatch
import json


class Test(CLITestCase):
    
        
    @urlpatch
    def test_whoami_anon(self, urls):
        
        user = urls.register(method='GET', path='/user', status=401)
        
        main(['--show-traceback', 'whoami'], False)
        self.assertIn('Anonymous User', self.stream.getvalue())
        
        user.assertCalled() 
        
    @urlpatch
    def test_whoami(self, urls):
        
        content = json.dumps({'login': 'eggs', 'created_at':'1/2/2000'})
        user = urls.register(method='GET', path='/user', content=content)
         
        main(['--show-traceback', 'whoami'], False)
        self.assertIn('eggs', self.stream.getvalue()) 

        user.assertCalled() 
        
        
if __name__ == '__main__':
    unittest.main()
