'''
Created on Aug 1, 2013

@author: sean
'''
from binstar_client.utils import jencode

class BuildMixin(object):
    '''
    Add build functionality to binstar client
    '''
    
    def trigger_build(self, username, package, build_resources):
        url = '%s/publish/%s/%s' % (self.domain, username, package)
        
        data = jencode(build_resources)
        res = self.session.post(url, data=data, verify=True)
        self._check_response(res, [201])
        return

