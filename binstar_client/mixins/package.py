'''
Created on May 23, 2014

@author: sean
'''
from binstar_client.utils import jencode

class PackageMixin(object):

    def copy(self, owner, package, version, basename=None,
                     to_owner=None, from_channel='main', to_channel='main'):
        url = '%s/copy/package/%s/%s/%s' % (self.domain, owner, package, version)
        if basename:
            url += '/%s' % basename

        payload = dict(to_owner=to_owner, from_channel=from_channel, to_channel=to_channel)
        data, headers = jencode(payload)
        res = self.session.post(url, data=data, headers=headers)
        self._check_response(res)
        return res.json()

