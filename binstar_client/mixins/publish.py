
from binstar_client.utils import jencode

class PublishMixin(object):
    '''
    Add publish functionality to binstar client
    '''
    
    def published(self, username, name):
        '''
        test if a package is published
        '''
        url = '%s/publish/%s/%s' % (self.domain, username, name)
        res = self.session.get(url, verify=True)
        self._check_response(res)
        return res.json().get('published',False)
    
    def publish(self, username, name):
        '''
        publish a package to the global repository
        '''
        url = '%s/publish/%s/%s' % (self.domain, username, name)
        res = self.session.put(url, verify=True)
        self._check_response(res, [201])
        return

    def unpublish(self, username, name):
        '''
        remove a package from the global repository
        '''
        url = '%s/publish/%s/%s' % (self.domain, username, name)
        res = self.session.delete(url, verify=True)
        self._check_response(res, [201])
        return
