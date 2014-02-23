'''
Created on Feb 18, 2014

@author: sean
'''
from __future__ import unicode_literals
from binstar_client.scripts.cli import main
from binstar_client.tests.fixture import CLITestCase
from binstar_client.tests.urlmock import urlpatch
import base64
import json
import unittest
from binstar_client import errors

class Test(CLITestCase):
        
    @urlpatch
    def test_upload_bad_package(self, registry):
        
        r1 = registry.register(method='GET', path='/user', content='{"login": "eggs"}')
        r2 = registry.register(method='GET', path='/package/eggs/foo', status=404)
        
        with self.assertRaises(errors.UserError):
            main(['--show-traceback', 'upload', self.data_dir('foo-0.1-0.tar.bz2')], False)
        
        r1.assertCalled()
        r2.assertCalled()

    @urlpatch
    def test_upload(self, registry):
        
        r1 = registry.register(method='GET', path='/user', content='{"login": "eggs"}')
        r2 = registry.register(method='GET', path='/package/eggs/foo', content='{}')
        r3 = registry.register(method='GET', path='/release/eggs/foo/0.1', content='{}')
        r4 = registry.register(method='GET', path='/dist/eggs/foo/0.1/osx-64/foo-0.1-0.tar.bz2', status=404, content='{}')
        r5 = registry.register(method='GET', path='/dist/eggs/foo/0.1/osx-64/foo-0.1-0.tar.bz2', status=404, content='{}')
        
        content = {"s3_url": "http://s3_url.com/s3_url", "s3form_data": {}, "dist_id": "dist_id"}
        r6 = registry.register(method='POST', path='/stage/eggs/foo/0.1/osx-64/foo-0.1-0.tar.bz2', content=content)

        r7 = registry.register(method='POST', path='/s3_url', status=201)
        r8 = registry.register(method='POST', path='/commit/eggs/foo/0.1/osx-64/foo-0.1-0.tar.bz2', status=200, content={})
        
        main(['--show-traceback', 'upload', self.data_dir('foo-0.1-0.tar.bz2')], False)
        
        r1.assertCalled()
        r2.assertCalled()

        
        
if __name__ == '__main__':
    unittest.main()
