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
from os.path import join, dirname
from binstar_client import tests
from httmock import urlmatch, HTTMock
import requests
from contextlib import contextmanager
from functools import wraps

requests.Response
test_data = join(dirname(tests.__file__), 'data')

def filter_request(m, prepared_request):
    if m[0] and  m[0] != prepared_request.url:
        return False
    
    if m[1] and  m[1] != prepared_request.path_url:
        return False

    if m[2] and m[2] != prepared_request.method:
        return False
    
    return True
    
class Registry(object):
    def __init__(self):
        self._map = []
        
    def __enter__(self):
        self.real_send = requests.Session.send
        requests.Session.send = self.mock_send
        
        return self
    
    def __exit__(self, *exec_info):
        requests.Session.send = self.real_send
        return 

    def mock_send(self, prepared_request, *args, **kwargs):
        print 'prepared_request', prepared_request.method
        
        rule = next((m for m in self._map[::-1] if filter_request(m, prepared_request)), None)

        if rule is None:
            raise Exception('No matching rule found for url [%s] %s' %(prepared_request.method,
                                                                          prepared_request.url, 
                                                                          ))
        
        res = requests.models.Response()
        res.status_code = rule[-2]
        res._content_consumed = True
        res._content = rule[-1]
        return res
    
    def register(self, url=None, path=None, method=None, status=200, content=''):
        self._map.append((url, path, method, status, content))
        
def urlpatch(func):
    @wraps(func)
    def inner(self, *args, **kwargs):
        with Registry() as r:
            return func(self, r, *args, **kwargs)
    return inner
    

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
