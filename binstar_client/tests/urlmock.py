'''
Created on Feb 22, 2014

@author: sean
'''
from __future__ import unicode_literals
import requests
from functools import wraps
import json

try:
    unicode
except NameError:
    unicode = str
    
def filter_request(m, prepared_request):
    if m[0] and  m[0] != prepared_request.url:
        return False
    
    if m[1] and  m[1] != prepared_request.path_url:
        return False

    if m[2] and m[2] != prepared_request.method:
        return False
    
    return True
    
class Responses(object):
    def __init__(self):
        self._resps = []
        
    def append(self, res):
        self._resps.append(res)
    
    @property
    def called(self):
        return bool(len(self._resps))

    @property
    def req(self):
        if self._resps:
            return self._resps[0][1]
        
    def assertCalled(self):
        assert self.called, "The url was not called"
        
    def assertNotCalled(self):
        assert not self.called, "The url was called"
        
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
        
        rule = next((m for m in self._map[::-1] if filter_request(m, prepared_request)), None)

        if rule is None:
            raise Exception('No matching rule found for url [%s] %s' % (prepared_request.method,
                                                                          prepared_request.url,
                                                                          ))
            
        content = rule[-2]
        if isinstance(content, dict):
            content = json.dumps(content)
        if isinstance(content, unicode):
            content = content.encode()
            
        res = requests.models.Response()
        res.status_code = rule[-3]
        res._content_consumed = True
        res._content = content
        res.encoding = 'utf-8'
        rule[-1].append((res, prepared_request))
        return res
    
    def register(self, url=None, path=None, method='GET', status=200, content=b''):
        res = Responses() 
        self._map.append((url, path, method, status, content, res))
        return res
         
        
def urlpatch(func):
    @wraps(func)
    def inner(self, *args, **kwargs):
        with Registry() as r:
            return func(self, r, *args, **kwargs)
    return inner
    
