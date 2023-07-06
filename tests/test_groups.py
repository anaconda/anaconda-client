# -*- coding: utf8 -*-
# pylint: disable=missing-function-docstring

"""Tests for group management commands."""

from binstar_client import errors
from tests.fixture import CLITestCase, main
from tests.urlmock import urlpatch


class Test(CLITestCase):
    """Tests for group management commands."""

    @urlpatch
    def test_show(self, urls):
        urls.register(
            method='GET',
            path='/groups/org',
            content='{"groups": [{"name":"grp", "permission": "read"}]}',
        )

        main(['--show-traceback', 'groups', 'show', 'org'])

        urls.assertAllCalled()

    @urlpatch
    def test_show_group(self, urls):
        urls.register(
            method='GET',
            path='/group/org/owners',
            content='{"name": "owners", "permission": "read", "members_count": 1, "repos_count": 1}',
        )

        main(['--show-traceback', 'groups', 'show', 'org/owners'])

        urls.assertAllCalled()

    @urlpatch
    def test_create(self, urls):
        urls.register(
            method='POST',
            path='/group/org/new_grp',
            status=204,
        )

        main(['--show-traceback', 'groups', 'add', 'org/new_grp'])

        urls.assertAllCalled()

    def test_create_missing_group(self):
        with self.assertRaisesRegex(errors.UserError, 'Group name not given'):
            main(['--show-traceback', 'groups', 'add', 'org'])

    @urlpatch
    def test_add_member(self, urls):
        urls.register(
            method='PUT',
            path='/group/org/grp/members/new_member',
            status=204,
        )

        main(['--show-traceback', 'groups', 'add_member', 'org/grp/new_member'])

        urls.assertAllCalled()

    def test_add_member_missing_member(self):
        with self.assertRaisesRegex(errors.UserError, 'Member name not given'):
            main(['--show-traceback', 'groups', 'add_member', 'org/grp'])

    @urlpatch
    def test_remove_member(self, urls):
        urls.register(
            method='DELETE',
            path='/group/org/grp/members/new_member',
            status=204,
        )

        main(['--show-traceback', 'groups', 'remove_member', 'org/grp/new_member'])

        urls.assertAllCalled()

    @urlpatch
    def test_packages(self, urls):
        urls.register(
            method='GET',
            path='/group/org/grp/packages',
            content='[{"name": "pkg", "full_name": "org/pkg", "summary": "An org pkg"}]'
        )

        main(['--show-traceback', 'groups', 'packages', 'org/grp'])

        urls.assertAllCalled()

    @urlpatch
    def test_add_package(self, urls):
        urls.register(
            method='PUT',
            path='/group/org/grp/packages/pkg',
            status=204,
        )

        main(['--show-traceback', 'groups', 'add_package', 'org/grp/pkg'])

        urls.assertAllCalled()

    @urlpatch
    def test_remove_package(self, urls):
        urls.register(
            method='DELETE',
            path='/group/org/grp/packages/pkg',
            status=204,
        )

        main(['--show-traceback', 'groups', 'remove_package', 'org/grp/pkg'])

        urls.assertAllCalled()
