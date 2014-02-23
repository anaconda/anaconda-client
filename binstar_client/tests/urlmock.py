'''
Created on Feb 22, 2014

@author: sean
'''
import requests
from functools import wraps

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
    
