# -*- coding: utf8 -*-
"""Tests for channel notice commands."""

import io
import json
import logging
import unittest.mock
from contextlib import contextmanager

import freezegun
from rich.console import Console

from binstar_client.errors import UserError
from tests.fixture import CLITestCase, main
from tests.urlmock import urlpatch


NOTICE_UUID = '550e8400-e29b-41d4-a716-446655440000'

NOTICE_ITEM = {
    'notice_id': NOTICE_UUID,
    'owner_id': '507f1f77bcf86cd799439011',
    'message': 'hello from api',
    'level': 'info',
    'status': 'draft',
    'created_at': '2026-06-01T12:00:00+00:00',
    'updated_at': '2026-06-01T12:00:00+00:00',
    'expires_at': '2026-09-16T12:00:00+00:00',
}

ACTIVE_NOTICE = {
    'id': NOTICE_UUID,
    'message': 'hello from api',
    'level': 'info',
    'created_at': '2026-06-01T12:00:00+00:00',
    'expires_at': '2026-09-16T12:00:00+00:00',
}


@contextmanager
def _patch_notice_console_print():
    """Route Rich console output into the test logging stream."""
    import binstar_client.commands._channel_notices as notice_cmd

    def _print(*args, **kwargs):
        buf = io.StringIO()
        Console(file=buf, width=200, force_terminal=False).print(*args, **kwargs)
        logging.getLogger('binstar').info(buf.getvalue().rstrip('\n'))

    with unittest.mock.patch.object(notice_cmd.console, 'print', side_effect=_print):
        notice_cmd.console.height = None
        yield


class TestNotices(CLITestCase):
    @urlpatch
    def test_list_notices(self, urls):
        list_req = urls.register(
            method='GET',
            content={'total_count': 1, 'items': [NOTICE_ITEM]},
        )

        with _patch_notice_console_print():
            main(['--show-traceback', 'channel', 'notice', 'list', 'myteam'])

        urls.assertAllCalled()
        self.assertIn('owner=myteam', list_req.req.url)
        self.assertIn('myteam Notices', self.stream.getvalue())
        self.assertIn(NOTICE_UUID, self.stream.getvalue())

    @urlpatch
    def test_get_notice(self, urls):
        urls.register(method='GET', path=f'/myteam/notices/{NOTICE_UUID}', content=NOTICE_ITEM)

        with _patch_notice_console_print():
            main(['--show-traceback', 'channel', 'notice', 'get', 'myteam', NOTICE_UUID])

        urls.assertAllCalled()
        self.assertIn('hello from api', self.stream.getvalue())

    @urlpatch
    def test_get_invalid_notice_id(self, urls):
        with self.assertRaises(UserError) as ctx:
            main(['--show-traceback', 'channel', 'notice', 'get', 'myteam', 'bad-id'])

        self.assertIn('notice_id must be a valid UUID', str(ctx.exception))

    @urlpatch
    def test_create_notice(self, urls):
        create = urls.register(
            method='POST',
            path='/myteam/notices',
            status=201,
            content={**NOTICE_ITEM, 'status': 'draft'},
        )

        with _patch_notice_console_print():
            main(
                [
                    '--show-traceback',
                    'channel',
                    'notice',
                    'create',
                    'myteam',
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
        self.assertNotIn('notice_id', body)
        self.assertEqual(body['level'], 'info')
        self.assertIn(f"Notice '{NOTICE_UUID}' created successfully", self.stream.getvalue())
        self.assertIn('anaconda channel notice list myteam', self.stream.getvalue())
        self.assertIn(f'anaconda channel notice publish myteam {NOTICE_UUID}', self.stream.getvalue())

    @urlpatch
    @freezegun.freeze_time('2026-06-01T12:00:00Z')
    def test_create_notice_defaults_and_expires_after(self, urls):
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
                '--message',
                'hello from api',
                '--expires-after',
                '30',
            ]
        )

        urls.assertAllCalled()
        body = json.loads(create.req.body)
        self.assertNotIn('notice_id', body)
        self.assertEqual(body['level'], 'info')
        self.assertEqual(body['expires_at'], '2026-07-01T12:00:00Z')

    @urlpatch
    def test_create_notice_expires_options_conflict(self, urls):
        with self.assertRaises(UserError) as ctx:
            main(
                [
                    '--show-traceback',
                    'channel',
                    'notice',
                    'create',
                    'myteam',
                    '--message',
                    'hello from api',
                    '--expires-at',
                    '2026-09-16T12:00:00+00:00',
                    '--expires-after',
                    '7',
                ]
            )

        self.assertIn('Use only one of --expires-at or --expires-after', str(ctx.exception))

    @urlpatch
    @freezegun.freeze_time('2026-06-01T12:00:00Z')
    def test_create_notice_rejects_past_expires_at(self, urls):
        with self.assertRaises(UserError) as ctx:
            main(
                [
                    '--show-traceback',
                    'channel',
                    'notice',
                    'create',
                    'myteam',
                    '--message',
                    'hello from api',
                    '--expires-at',
                    '2026-05-01T12:00:00Z',
                ]
            )

        self.assertIn('expires_at must be in the future', str(ctx.exception))

    @urlpatch
    @unittest.mock.patch('binstar_client.commands._channel_notices.bool_input', return_value=False)
    @unittest.mock.patch('binstar_client.commands._channel_notices._is_interactive', return_value=True)
    @unittest.mock.patch('binstar_client.commands._channel_notices.input')
    def test_create_notice_interactive(self, urls, input_mock, _is_interactive_mock, _bool_input_mock):
        input_mock.side_effect = [
            'interactive message',
            'warning',
            '2026-09-16T12:00:00+00:00',
        ]
        create = urls.register(
            method='POST',
            path='/myteam/notices',
            status=201,
            content={**NOTICE_ITEM, 'status': 'draft'},
        )

        with _patch_notice_console_print():
            main(['--show-traceback', 'channel', 'notice', 'create', 'myteam'])

        urls.assertAllCalled()
        body = json.loads(create.req.body)
        self.assertNotIn('notice_id', body)
        self.assertEqual(body['level'], 'warning')
        self.assertIn(f"Notice '{NOTICE_UUID}' created successfully", self.stream.getvalue())

    @urlpatch
    def test_publish_notice(self, urls):
        urls.register(
            method='POST',
            path=f'/myteam/notices/{NOTICE_UUID}/publish',
            content={'notice_id': NOTICE_UUID, 'status': 'published', 'previous_status': 'draft'},
        )

        with _patch_notice_console_print():
            main(['--show-traceback', 'channel', 'notice', 'publish', 'myteam', NOTICE_UUID])

        urls.assertAllCalled()
        self.assertIn(f"Notice '{NOTICE_UUID}' published successfully", self.stream.getvalue())
        self.assertIn('notice published myteam', self.stream.getvalue())

    @urlpatch
    @unittest.mock.patch('binstar_client.commands._channel_notices.bool_input', return_value=True)
    def test_delete_notice(self, urls, _bool_input_mock):
        urls.register(method='DELETE', path=f'/myteam/notices/{NOTICE_UUID}', status=204, content=b'')

        with _patch_notice_console_print():
            main(['--show-traceback', 'channel', 'notice', 'delete', 'myteam', NOTICE_UUID])

        urls.assertAllCalled()
        self.assertIn(f"Notice '{NOTICE_UUID}' deleted successfully", self.stream.getvalue())

    @urlpatch
    def test_delete_notice_force(self, urls):
        urls.register(method='DELETE', path=f'/myteam/notices/{NOTICE_UUID}', status=204, content=b'')

        with _patch_notice_console_print():
            main(['--show-traceback', 'channel', 'notice', 'delete', 'myteam', NOTICE_UUID, '--force'])

        urls.assertAllCalled()
        self.assertIn(f"Notice '{NOTICE_UUID}' deleted successfully", self.stream.getvalue())

    @urlpatch
    @unittest.mock.patch('binstar_client.commands._channel_notices.bool_input', return_value=False)
    def test_delete_notice_cancelled(self, urls, _bool_input_mock):
        urls.register(method='DELETE', path=f'/myteam/notices/{NOTICE_UUID}', status=204, content=b'')

        with _patch_notice_console_print():
            main(['--show-traceback', 'channel', 'notice', 'delete', 'myteam', NOTICE_UUID])

        self.assertIn(f"Not deleting notice '{NOTICE_UUID}'", self.stream.getvalue())

    @urlpatch
    def test_archive_notice(self, urls):
        urls.register(
            method='POST',
            path=f'/myteam/notices/{NOTICE_UUID}/archive',
            content={'notice_id': NOTICE_UUID, 'status': 'archived', 'previous_status': 'published'},
        )

        with _patch_notice_console_print():
            main(['--show-traceback', 'channel', 'notice', 'archive', 'myteam', NOTICE_UUID])

        urls.assertAllCalled()
        self.assertIn(f"Notice '{NOTICE_UUID}' archived successfully", self.stream.getvalue())

    @urlpatch
    def test_published_notices(self, urls):
        published = urls.register(
            method='GET',
            content={'notices': [ACTIVE_NOTICE]},
        )

        with _patch_notice_console_print():
            main(['--show-traceback', 'channel', 'notice', 'published', 'myteam'])

        urls.assertAllCalled()
        self.assertIn('/notices/active', published.req.url)
        self.assertIn('owner=myteam', published.req.url)
        self.assertNotIn('Authorization', published.req.headers)
        self.assertIn('myteam Notices', self.stream.getvalue())
        self.assertIn(NOTICE_UUID, self.stream.getvalue())

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

    @urlpatch
    def test_create_notice_rejects_empty_message(self, urls):
        with self.assertRaises(UserError) as ctx:
            main(
                [
                    '--show-traceback',
                    'channel',
                    'notice',
                    'create',
                    'myteam',
                    '--message',
                    '   ',
                    '--expires-after',
                    '7',
                ]
            )

        self.assertIn('message is required', str(ctx.exception))

    @urlpatch
    def test_create_notice_rejects_message_over_max_length(self, urls):
        with self.assertRaises(UserError) as ctx:
            main(
                [
                    '--show-traceback',
                    'channel',
                    'notice',
                    'create',
                    'myteam',
                    '--message',
                    'x' * 257,
                    '--expires-after',
                    '7',
                ]
            )

        self.assertIn('message must be at most 256 characters', str(ctx.exception))

    @urlpatch
    @unittest.mock.patch('binstar_client.commands._channel_notices.bool_input', return_value=False)
    @unittest.mock.patch('binstar_client.commands._channel_notices._is_interactive', return_value=True)
    @unittest.mock.patch('binstar_client.commands._channel_notices.input')
    @freezegun.freeze_time('2026-06-01T12:00:00Z')
    def test_create_notice_interactive_days(self, urls, input_mock, _is_interactive_mock, _bool_mock):
        input_mock.side_effect = ['hello', 'info', '30']
        create = urls.register(
            method='POST',
            path='/myteam/notices',
            status=201,
            content={**NOTICE_ITEM, 'status': 'draft'},
        )

        with _patch_notice_console_print():
            main(['--show-traceback', 'channel', 'notice', 'create', 'myteam'])

        body = json.loads(create.req.body)
        self.assertEqual(body['expires_at'], '2026-07-01T12:00:00Z')

    @urlpatch
    @unittest.mock.patch('binstar_client.commands._channel_notices.bool_input', side_effect=[True, False])
    @unittest.mock.patch('binstar_client.commands._channel_notices._is_interactive', return_value=True)
    @unittest.mock.patch('binstar_client.commands._channel_notices.input')
    @freezegun.freeze_time('2026-06-01T12:00:00Z')
    def test_create_notice_interactive_blank_then_accept_default(
        self, urls, input_mock, _is_interactive_mock, _bool_mock
    ):
        input_mock.side_effect = ['hello', 'info', '', '', '']
        create = urls.register(
            method='POST',
            path='/myteam/notices',
            status=201,
            content={**NOTICE_ITEM, 'status': 'draft'},
        )

        with _patch_notice_console_print():
            main(['--show-traceback', 'channel', 'notice', 'create', 'myteam'])

        body = json.loads(create.req.body)
        self.assertEqual(body['expires_at'], '2026-07-01T12:00:00Z')

    @urlpatch
    @unittest.mock.patch('binstar_client.commands._channel_notices.bool_input', side_effect=[False, False])
    @unittest.mock.patch('binstar_client.commands._channel_notices._is_interactive', return_value=True)
    @unittest.mock.patch('binstar_client.commands._channel_notices.input')
    @freezegun.freeze_time('2026-06-01T12:00:00Z')
    def test_create_notice_interactive_blank_then_decline_default(
        self, urls, input_mock, _is_interactive_mock, _bool_mock
    ):
        input_mock.side_effect = ['hello', 'info', '', '', '', '14']
        create = urls.register(
            method='POST',
            path='/myteam/notices',
            status=201,
            content={**NOTICE_ITEM, 'status': 'draft'},
        )

        with _patch_notice_console_print():
            main(['--show-traceback', 'channel', 'notice', 'create', 'myteam'])

        body = json.loads(create.req.body)
        self.assertEqual(body['expires_at'], '2026-06-15T12:00:00Z')

    @urlpatch
    @unittest.mock.patch('binstar_client.commands._channel_notices.bool_input', return_value=True)
    @unittest.mock.patch('binstar_client.commands._channel_notices._is_interactive', return_value=True)
    @unittest.mock.patch('binstar_client.commands._channel_notices.input')
    def test_create_notice_interactive_publish_yes(
        self, urls, input_mock, _is_interactive_mock, _bool_mock
    ):
        input_mock.side_effect = ['hello', 'info', '2026-09-16T12:00:00+00:00']
        urls.register(
            method='POST',
            path='/myteam/notices',
            status=201,
            content={**NOTICE_ITEM, 'status': 'draft'},
        )
        urls.register(
            method='POST',
            path=f'/myteam/notices/{NOTICE_UUID}/publish',
            content={'notice_id': NOTICE_UUID, 'status': 'published'},
        )

        with _patch_notice_console_print():
            main(['--show-traceback', 'channel', 'notice', 'create', 'myteam'])

        self.assertIn(f"Notice '{NOTICE_UUID}' published successfully", self.stream.getvalue())

    @urlpatch
    @unittest.mock.patch('binstar_client.commands._channel_notices._is_interactive', return_value=True)
    @unittest.mock.patch('binstar_client.commands._channel_notices.input')
    def test_update_interactive_keeps_expiry_when_blank(self, urls, input_mock, _is_interactive_mock):
        input_mock.side_effect = ['updated message', '', '']
        update = urls.register(
            method='PATCH',
            path=f'/myteam/notices/{NOTICE_UUID}',
            content={**NOTICE_ITEM, 'message': 'updated message'},
        )

        main(['--show-traceback', 'channel', 'notice', 'update', 'myteam', NOTICE_UUID])

        body = json.loads(update.req.body)
        self.assertEqual(body['message'], 'updated message')
        self.assertNotIn('expires_at', body)

    @urlpatch
    @unittest.mock.patch('binstar_client.commands._channel_notices._is_interactive', return_value=True)
    @unittest.mock.patch('binstar_client.commands._channel_notices.input')
    @freezegun.freeze_time('2026-06-01T12:00:00Z')
    def test_update_interactive_days(self, urls, input_mock, _is_interactive_mock):
        input_mock.side_effect = ['', '', '14']
        update = urls.register(
            method='PATCH',
            path=f'/myteam/notices/{NOTICE_UUID}',
            content={**NOTICE_ITEM, 'expires_at': '2026-06-15T12:00:00Z'},
        )

        main(['--show-traceback', 'channel', 'notice', 'update', 'myteam', NOTICE_UUID])

        body = json.loads(update.req.body)
        self.assertEqual(body['expires_at'], '2026-06-15T12:00:00Z')
