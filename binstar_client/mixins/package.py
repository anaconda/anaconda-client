'''
Created on May 23, 2014

@author: sean
'''
from binstar_client.utils import jencode
from binstar_client.errors import Conflict


class PackageMixin(object):

    def copy(self, owner, package, version, basename=None,
             to_owner=None, from_label='main', to_label='main', replace=False, update=False):
        url = '%s/copy/package/%s/%s/%s' % (self.domain, owner, package, version)
        if basename:
            url += '/%s' % basename

        payload = dict(to_owner=to_owner, from_channel=from_label, to_channel=to_label)
        data, headers = jencode(payload)

        if replace:
            res = self.session.put(url, data=data, headers=headers)
        elif update:
            res = self.session.patch(url, data=data, headers=headers)
        else:
            res = self.session.post(url, data=data, headers=headers)

        try:
            self._check_response(res)
        except Conflict as err:
            raise Conflict('File conflict while copying! Try to use --replace or --update options for force copying')

        return res.json()

