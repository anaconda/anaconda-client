# -*- coding: utf8 -*-
"""Tests for channel notice commands."""

import json
import unittest.mock

from binstar_client.errors import UserError
from tests.fixture import CLITestCase, main
from tests.urlmock import urlpatch


NOTICE_ITEM = {
    'notice_id': 'api-notice-1',
    'owner_id': '507f1f77bcf86cd799439011',
    'message': 'hello from api',
    'level': 'info',
    'status': 'draft',
    'created_at': '2026-06-01T12:00:00+00:00',
    'updated_at': '2026-06-01T12:00:00+00:00',
    'expires_at': '2026-09-16T12:00:00+00:00',
}

ACTIVE_NOTICE = {
    'id': 'api-notice-1',
    'message': 'hello from api',
    'level': 'info',
    'created_at': '2026-06-01T12:00:00+00:00',
    'expires_at': '2026-09-16T12:00:00+00:00',
}


class TestNotices(CLITestCase):
    @urlpatch
    def test_list_notices(self, urls):
        list_req = urls.register(
            method='GET',
            content={'total_count': 1, 'items': [NOTICE_ITEM]},
        )

        main(['--show-traceback', 'channel', 'notice', 'list', 'myteam'])

        urls.assertAllCalled()
        self.assertIn('owner=myteam', list_req.req.url)
        self.assertIn('api-notice-1', self.stream.getvalue())

    @urlpatch
    def test_get_notice(self, urls):
        urls.register(method='GET', path='/myteam/notices/api-notice-1', content=NOTICE_ITEM)

        main(['--show-traceback', 'channel', 'notice', 'get', 'myteam', 'api-notice-1'])

        urls.assertAllCalled()
        self.assertIn('hello from api', self.stream.getvalue())

    @urlpatch
    def test_create_notice(self, urls):
        create = urls.register(
            method='POST',
            path='/myteam/notices',
            status=201,
            content={**NOTICE_ITEM, 'status': 'draft'},
        )

        main(
            [
                '--show-traceback',
                'channel',
                'notice',
                'create',
                'myteam',
                '--id',
                'api-notice-1',
                '--message',
                'hello from api',
                '--level',
                'info',
                '--expires-at',
                '2026-09-16T12:00:00+00:00',
            ]
        )

        urls.assertAllCalled()
        body = json.loads(create.req.body)
        self.assertEqual(body['notice_id'], 'api-notice-1')
        self.assertEqual(body['level'], 'info')
        self.assertIn("Created notice 'api-notice-1'", self.stream.getvalue())

    @urlpatch
    @unittest.mock.patch('binstar_client.commands._channel_notices._is_interactive', return_value=True)
    @unittest.mock.patch('binstar_client.commands._channel_notices.input')
    def test_create_notice_interactive(self, urls, input_mock, _is_interactive_mock):
        input_mock.side_effect = [
            'interactive-notice',
            'interactive message',
            'warning',
            '2026-09-16T12:00:00+00:00',
        ]
        create = urls.register(
            method='POST',
            path='/myteam/notices',
            status=201,
            content={**NOTICE_ITEM, 'notice_id': 'interactive-notice', 'status': 'draft'},
        )

        main(['--show-traceback', 'channel', 'notice', 'create', 'myteam'])

        urls.assertAllCalled()
        body = json.loads(create.req.body)
        self.assertEqual(body['notice_id'], 'interactive-notice')
        self.assertEqual(body['level'], 'warning')

    @urlpatch
    def test_publish_notice(self, urls):
        urls.register(
            method='POST',
            path='/myteam/notices/api-notice-1/publish',
            content={'notice_id': 'api-notice-1', 'status': 'published', 'previous_status': 'draft'},
        )

        main(['--show-traceback', 'channel', 'notice', 'publish', 'myteam', 'api-notice-1'])

        urls.assertAllCalled()
        self.assertIn('Published notice', self.stream.getvalue())

    @urlpatch
    def test_archive_notice(self, urls):
        urls.register(
            method='POST',
            path='/myteam/notices/api-notice-1/archive',
            content={'notice_id': 'api-notice-1', 'status': 'archived', 'previous_status': 'published'},
        )

        main(['--show-traceback', 'channel', 'notice', 'archive', 'myteam', 'api-notice-1'])

        urls.assertAllCalled()
        self.assertIn('Archived notice', self.stream.getvalue())

    @urlpatch
    def test_delete_notice(self, urls):
        urls.register(method='DELETE', path='/myteam/notices/api-notice-1', status=204, content=b'')

        main(['--show-traceback', 'channel', 'notice', 'delete', 'myteam', 'api-notice-1'])

        urls.assertAllCalled()
        self.assertIn("Deleted notice 'api-notice-1'", self.stream.getvalue())

    @urlpatch
    def test_active_notices(self, urls):
        active = urls.register(
            method='GET',
            content={'notices': [ACTIVE_NOTICE]},
        )

        main(['--show-traceback', 'channel', 'notice', 'active', '--channel', 'myteam'])

        urls.assertAllCalled()
        self.assertIn('/notices/active', active.req.url)
        self.assertIn('owner=myteam', active.req.url)
        self.assertNotIn('Authorization', active.req.headers)
        self.assertIn('api-notice-1', self.stream.getvalue())

    @urlpatch
    def test_validation_error(self, urls):
        urls.register(
            method='POST',
            path='/myteam/notices',
            status=422,
            content={
                'code': 'validation_error',
                'message': 'level must be one of: info, warning, critical',
                'requestId': 'req-123',
            },
        )

        with self.assertRaises(UserError) as ctx:
            main(
                [
                    '--show-traceback',
                    'channel',
                    'notice',
                    'create',
                    'myteam',
                    '--id',
                    'bad',
                    '--message',
                    'msg',
                    '--level',
                    'info',
                    '--expires-at',
                    '2026-09-16T12:00:00+00:00',
                ]
            )

        self.assertIn('validation_error', str(ctx.exception))
        self.assertIn('req-123', str(ctx.exception))

    @urlpatch
    def test_list_with_organization(self, urls):
        list_req = urls.register(
            method='GET',
            content={'total_count': 0, 'items': []},
        )

        main(['--show-traceback', 'channel', 'notice', 'list', '-o', 'myorg'])

        urls.assertAllCalled()
        self.assertIn('owner=myorg', list_req.req.url)
