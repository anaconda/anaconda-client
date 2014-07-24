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

class Test(CLITestCase):

    @urlpatch
    def test_register_public(self, registry):

        r1 = registry.register(method='GET', path='/user', content='{"login": "eggs"}')
        r2 = registry.register(method='GET', path='/package/eggs/foo', status=404)
        r3 = registry.register(method='POST', path='/package/eggs/foo', status=200, content='{"login": "eggs"}')

        main(['--show-traceback', 'register', self.data_dir('foo-0.1-0.tar.bz2')], False)

        r1.assertCalled()
        r2.assertCalled()
        r3.assertCalled()

        data = json.loads(r3.req.body)
        self.assertTrue(data['public'])

    @urlpatch
    def test_register_private(self, registry):

        r1 = registry.register(method='GET', path='/user', content='{"login": "eggs"}')
        r2 = registry.register(method='GET', path='/package/eggs/foo', status=404)
        r3 = registry.register(method='POST', path='/package/eggs/foo', status=200, content='{"login": "eggs"}')

        main(['--show-traceback', 'register', '--private', self.data_dir('foo-0.1-0.tar.bz2')], False)

        r1.assertCalled()
        r2.assertCalled()
        r3.assertCalled()

        data = json.loads(r3.req.body)
        self.assertFalse(data['public'])



if __name__ == '__main__':
    unittest.main()
