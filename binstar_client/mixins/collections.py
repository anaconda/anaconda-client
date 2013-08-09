from binstar_client.utils import jencode

class CollectionsMixin(object):
    
    def collections(self, org):
        '''
        list the collections of an organization
        
        :param org: the organization username
        '''
        
        url = '%s/collections/%s' % (self.domain, org)
        res = self.session.get(url, verify=True)
        self._check_response(res, [200])
        return res.json()
         
    def collection(self, org, name):
        '''
        list the collections of an organization
        
        :param org: the organization username
        :param name: the name of the collection
        '''
        
        url = '%s/collections/%s/%s' % (self.domain, org, name)
        res = self.session.get(url, verify=True)
        self._check_response(res, [200])
        return res.json()
         
    def collection_add_packages(self, org, name, owner_package_data=(), owner=None, package=None):
        
        url = '%s/collections/%s/%s/package' % (self.domain, org, name)
        if owner and package:
            payload = dict(package_owner=owner, package_name=package)
        elif owner_package_data:
            payload = owner_package_data
        else:
            raise TypeError('collection_add_packages must spesify argument "owner_package_data"')
            
        data = jencode(payload)
        res = self.session.put(url, data=data, verify=True)
        self._check_response(res, [201])
    

    def collection_remove_packages(self, org, name, owner_package_data=(), owner=None, package=None):
        
        url = '%s/collections/%s/%s/package' % (self.domain, org, name)
        if owner and package:
            payload = dict(package_owner=owner, package_name=package)
        elif owner_package_data:
            payload = owner_package_data
        else:
            raise TypeError('collection_add_packages must spesify argument "owner_package_data"')
            
        data = jencode(payload)
        res = self.session.delete(url, data=data, verify=True)
        self._check_response(res, [201])
        
    def add_collection(self, org, name, public=True, description=''):
        '''
        add a collection to an organization
        
        :param org: the organization username
        :param name: the name of the collection to create
        :param public: make this collection public
        :param description: describe the collection
        '''
        
        url = '%s/collections/%s/%s' % (self.domain, org, name)
        payload = dict(public=public, description=description)
        data = jencode(payload)
        res = self.session.post(url, data=data, verify=True)
        self._check_response(res, [201])
        
    def update_collection(self, org, name, public=None, description=None):
        '''
        update a collection
        '''
        
        url = '%s/collections/%s/%s' % (self.domain, org, name)
        payload = dict(public=public, description=description)
        data = jencode(payload)
        res = self.session.patch(url, data=data, verify=True)
        self._check_response(res, [201])

    def remove_collection(self, org, name):
        '''
        remove a collection from an organization
        
        :param org: the organization username
        :param name: the name of the collection to create
        '''
        
        url = '%s/collections/%s/%s' % (self.domain, org, name)
        res = self.session.delete(url, verify=True)
        self._check_response(res, [201])

    def collection_clone(self, from_org, from_name,
                               to_org, to_name):
        
        url = '%s/collections/%s/%s' % (self.domain, to_org, to_name)
        payload = dict(clone={'owner': from_org, 'collection': from_name})
        data = jencode(payload)
        res = self.session.post(url, data=data, verify=True)
        self._check_response(res, [201])

    def collection_pull(self, from_org, from_name,
                               to_org, to_name):
        
        url = '%s/collections/%s/%s/pull' % (self.domain, to_org, to_name)
        payload = {'from_owner': from_org, 'from_name': from_name}
        data = jencode(payload)
        res = self.session.patch(url, data=data, verify=True)
        self._check_response(res, [201])
    
    
        
