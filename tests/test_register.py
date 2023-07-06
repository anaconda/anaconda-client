# -*- coding: utf8 -*-
# pylint: disable=invalid-name,missing-function-docstring

"""Tests for package registration commands."""

import json
import unittest

from tests.fixture import CLITestCase, main
from tests.urlmock import urlpatch
from tests.utils.utils import data_dir


@unittest.skip('Need to change this to binstar package --create')
class Test(CLITestCase):
    """Tests for package registration commands."""

    @urlpatch
    def test_register_public(self, registry):
        r1 = registry.register(method='GET', path='/user', content='{"login": "eggs"}')
        r2 = registry.register(method='GET', path='/package/eggs/foo', status=404)
        r3 = registry.register(method='POST', path='/package/eggs/foo', status=200, content='{"login": "eggs"}')

        main(['--show-traceback', 'register', data_dir('foo-0.1-0.tar.bz2')])

        r1.assertCalled()
        r2.assertCalled()
        r3.assertCalled()

        data = json.loads(r3.req.body)
        self.assertTrue(data['public'])

    @urlpatch
    def test_register_private(self, registry):  # pylint: disable=missing-function-docstring
        r1 = registry.register(method='GET', path='/user', content='{"login": "eggs"}')
        r2 = registry.register(method='GET', path='/package/eggs/foo', status=404)
        r3 = registry.register(method='POST', path='/package/eggs/foo', status=200, content='{"login": "eggs"}')

        main(['--show-traceback', 'register', '--private', data_dir('foo-0.1-0.tar.bz2')])

        r1.assertCalled()
        r2.assertCalled()
        r3.assertCalled()

        data = json.loads(r3.req.body)
        self.assertFalse(data['public'])
