import unittest
from binstar_client.tests.fixture import CLITestCase
from binstar_client.tests.urlmock import urlpatch
from binstar_client.scripts.cli import main
from binstar_client import errors


class Test(CLITestCase):
    @urlpatch
    def test_show(self, urls):
        urls.register(
            method='GET',
            path='/groups/org',
            content='{"groups": [{"name":"grp", "permission": "read"}]}',
        )

        main(['--show-traceback', 'groups', 'show', 'org'], False)

        urls.assertAllCalled()

    @urlpatch
    def test_show_group(self, urls):
        urls.register(
            method='GET',
            path='/group/org/owners',
            content='{"name": "owners", "permission": "read", "members_count": 1, "repos_count": 1}',
        )

        main(['--show-traceback', 'groups', 'show', 'org/owners'], False)

        urls.assertAllCalled()

    @urlpatch
    def test_create(self, urls):
        urls.register(
            method='POST',
            path='/group/org/new_grp',
            status=204,
        )

        main(['--show-traceback', 'groups', 'add', 'org/new_grp'], False)

        urls.assertAllCalled()

    @urlpatch
    def test_create_missing_group(self, urls):
        with self.assertRaisesRegexp(errors.UserError, 'Group name not given'):
            main(['--show-traceback', 'groups', 'add', 'org'], False)

    @urlpatch
    def test_add_member(self, urls):
        urls.register(
            method='PUT',
            path='/group/org/grp/members/new_member',
            status=204,
        )

        main(['--show-traceback', 'groups', 'add_member', 'org/grp/new_member'], False)

        urls.assertAllCalled()

    @urlpatch
    def test_add_member_missing_member(self, urls):
        with self.assertRaisesRegexp(errors.UserError, 'Member name not given'):
            main(['--show-traceback', 'groups', 'add_member', 'org/grp'], False)

    @urlpatch
    def test_remove_member(self, urls):
        urls.register(
            method='DELETE',
            path='/group/org/grp/members/new_member',
            status=204,
        )

        main(['--show-traceback', 'groups', 'remove_member', 'org/grp/new_member'], False)

        urls.assertAllCalled()

    @urlpatch
    def test_packages(self, urls):
        urls.register(
            method='GET',
            path='/group/org/grp/packages',
            content='[{"name": "pkg", "full_name": "org/pkg", "summary": "An org pkg"}]'
        )

        main(['--show-traceback', 'groups', 'packages', 'org/grp'], False)

        urls.assertAllCalled()

    @urlpatch
    def test_add_package(self, urls):
        urls.register(
            method='PUT',
            path='/group/org/grp/packages/pkg',
            status=204,
        )

        main(['--show-traceback', 'groups', 'add_package', 'org/grp/pkg'], False)

        urls.assertAllCalled()

    @urlpatch
    def test_remove_package(self, urls):
        urls.register(
            method='DELETE',
            path='/group/org/grp/packages/pkg',
            status=204,
        )

        main(['--show-traceback', 'groups', 'remove_package', 'org/grp/pkg'], False)

        urls.assertAllCalled()

if __name__ == "__main__":
    unittest.main()
