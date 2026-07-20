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
    'id': NOTICE_UUID,
    'owner_id': '507f1f77bcf86cd799439011',
    'message': 'hello from api',
    'level': 'info',
    'status': 'draft',
    'created_at': '2026-06-01T12:00:00+00:00',
    'updated_at': '2026-06-01T12:00:00+00:00',
    'expires_at': '2026-09-16T12:00:00+00:00',
}


@contextmanager
def _patch_level_picker(level='info'):
    with unittest.mock.patch(
        'binstar_client.commands._channel_notices.select_from_list',
        return_value=level,
    ):
        yield


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
            path='/myteam/notices?offset=0&limit=20',
            content={'total_count': 1, 'items': [NOTICE_ITEM]},
        )

        with _patch_notice_console_print():
            main(['--show-traceback', 'channel', 'notice', 'list', 'myteam'])

        urls.assertAllCalled()
        self.assertIn('/myteam/notices', list_req.req.url)
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

        self.assertIn('Notice ID must be a valid UUID', str(ctx.exception))

    @urlpatch
    def test_delete_missing_notice_id(self, urls):
        with _patch_notice_console_print():
            with self.assertRaises(UserError) as ctx:
                main(['--show-traceback', 'channel', 'notice', 'delete', 'myteam'])

        self.assertIn("Missing argument 'Notice ID'", str(ctx.exception))
        self.assertIn('anaconda channel notice list myteam', self.stream.getvalue())
        self.assertIn('Note: Find Notice IDs with', self.stream.getvalue())

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
    def test_create_notice_accepts_id_field(self, urls):
        """API returns `id` on create."""
        urls.register(
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

        self.assertIn(f"Notice '{NOTICE_UUID}' created successfully", self.stream.getvalue())

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
        self.assertEqual(body['expires_at'], '2026-07-01T12:00:00+00:00')

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
    @unittest.mock.patch('binstar_client.commands._channel_notices._prompt_input')
    def test_create_notice_interactive(self, urls, input_mock, _is_interactive_mock, _bool_input_mock):
        input_mock.side_effect = [
            'interactive message',
            '2026-09-16T12:00:00+00:00',
        ]
        create = urls.register(
            method='POST',
            path='/myteam/notices',
            status=201,
            content={**NOTICE_ITEM, 'status': 'draft'},
        )

        with _patch_notice_console_print(), _patch_level_picker('warning'):
            main(['--show-traceback', 'channel', 'notice', 'create', 'myteam'])

        urls.assertAllCalled()
        body = json.loads(create.req.body)
        self.assertNotIn('notice_id', body)
        self.assertEqual(body['level'], 'warning')
        self.assertIn(f"Notice '{NOTICE_UUID}' created successfully", self.stream.getvalue())

    @urlpatch
    @unittest.mock.patch('binstar_client.commands._channel_notices.bool_input', return_value=True)
    def test_publish_notice(self, urls, _bool_input_mock):
        urls.register(
            method='POST',
            path=f'/myteam/notices/{NOTICE_UUID}/publish',
            content={'id': NOTICE_UUID, 'status': 'published'},
        )

        with _patch_notice_console_print():
            main(['--show-traceback', 'channel', 'notice', 'publish', 'myteam', NOTICE_UUID])

        urls.assertAllCalled()
        self.assertIn(f"Notice '{NOTICE_UUID}' published successfully", self.stream.getvalue())
        self.assertIn('list myteam --status published', self.stream.getvalue())

    @urlpatch
    def test_publish_notice_force(self, urls):
        urls.register(
            method='POST',
            path=f'/myteam/notices/{NOTICE_UUID}/publish',
            content={'id': NOTICE_UUID, 'status': 'published'},
        )

        with _patch_notice_console_print():
            main(['--show-traceback', 'channel', 'notice', 'publish', 'myteam', NOTICE_UUID, '--force'])

        urls.assertAllCalled()
        self.assertIn(f"Notice '{NOTICE_UUID}' published successfully", self.stream.getvalue())

    @urlpatch
    @unittest.mock.patch('binstar_client.commands._channel_notices.bool_input', return_value=False)
    def test_publish_notice_cancelled(self, urls, _bool_input_mock):
        urls.register(
            method='POST',
            path=f'/myteam/notices/{NOTICE_UUID}/publish',
            content={'id': NOTICE_UUID, 'status': 'published'},
        )

        with _patch_notice_console_print():
            main(['--show-traceback', 'channel', 'notice', 'publish', 'myteam', NOTICE_UUID])

        self.assertIn(f"Not publishing notice '{NOTICE_UUID}'", self.stream.getvalue())

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
    @unittest.mock.patch('binstar_client.commands._channel_notices.bool_input', return_value=True)
    def test_archive_notice(self, urls, _bool_input_mock):
        urls.register(
            method='POST',
            path=f'/myteam/notices/{NOTICE_UUID}/archive',
            content={'id': NOTICE_UUID, 'status': 'archived'},
        )

        with _patch_notice_console_print():
            main(['--show-traceback', 'channel', 'notice', 'archive', 'myteam', NOTICE_UUID])

        urls.assertAllCalled()
        self.assertIn(f"Notice '{NOTICE_UUID}' archived successfully", self.stream.getvalue())

    @urlpatch
    @unittest.mock.patch('binstar_client.commands._channel_notices.bool_input', return_value=True)
    def test_archive_with_namespace_and_notice_id_only(self, urls, _bool_input_mock):
        archive = urls.register(
            method='POST',
            path=f'/myorg/notices/{NOTICE_UUID}/archive',
            content={'id': NOTICE_UUID, 'status': 'archived'},
        )

        with _patch_notice_console_print():
            main(['--show-traceback', 'channel', 'notice', 'archive', '-n', 'myorg', NOTICE_UUID, '--force'])

        urls.assertAllCalled()
        self.assertIn(f'/myorg/notices/{NOTICE_UUID}/archive', archive.req.url)
        self.assertIn(f"Notice '{NOTICE_UUID}' archived successfully", self.stream.getvalue())

    @urlpatch
    @unittest.mock.patch('binstar_client.commands._channel_notices.bool_input', return_value=True)
    def test_publish_with_namespace_and_notice_id_only(self, urls, _bool_input_mock):
        publish = urls.register(
            method='POST',
            path=f'/myorg/notices/{NOTICE_UUID}/publish',
            content={'id': NOTICE_UUID, 'status': 'published'},
        )

        with _patch_notice_console_print():
            main(['--show-traceback', 'channel', 'notice', 'publish', '-n', 'myorg', NOTICE_UUID, '--force'])

        urls.assertAllCalled()
        self.assertIn(f'/myorg/notices/{NOTICE_UUID}/publish', publish.req.url)
        self.assertIn(f"Notice '{NOTICE_UUID}' published successfully", self.stream.getvalue())

    def test_coerce_notice_id_args_with_namespace(self):
        from binstar_client.commands._channel_notices import _coerce_notice_id_args

        channel, notice_id = _coerce_notice_id_args(NOTICE_UUID, None, 'myorg')
        self.assertIsNone(channel)
        self.assertEqual(notice_id, NOTICE_UUID)

    def test_coerce_notice_id_args_without_namespace(self):
        from binstar_client.commands._channel_notices import _coerce_notice_id_args

        channel, notice_id = _coerce_notice_id_args('myorg', NOTICE_UUID, None)
        self.assertEqual(channel, 'myorg')
        self.assertEqual(notice_id, NOTICE_UUID)

    @urlpatch
    def test_archive_notice_force(self, urls):
        urls.register(
            method='POST',
            path=f'/myteam/notices/{NOTICE_UUID}/archive',
            content={'id': NOTICE_UUID, 'status': 'archived'},
        )

        with _patch_notice_console_print():
            main(['--show-traceback', 'channel', 'notice', 'archive', 'myteam', NOTICE_UUID, '--force'])

        urls.assertAllCalled()
        self.assertIn(f"Notice '{NOTICE_UUID}' archived successfully", self.stream.getvalue())

    @urlpatch
    @unittest.mock.patch('binstar_client.commands._channel_notices.bool_input', return_value=False)
    def test_archive_notice_cancelled(self, urls, _bool_input_mock):
        urls.register(
            method='POST',
            path=f'/myteam/notices/{NOTICE_UUID}/archive',
            content={'id': NOTICE_UUID, 'status': 'archived'},
        )

        with _patch_notice_console_print():
            main(['--show-traceback', 'channel', 'notice', 'archive', 'myteam', NOTICE_UUID])

        self.assertIn(f"Not archiving notice '{NOTICE_UUID}'", self.stream.getvalue())

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
    def test_list_with_namespace(self, urls):
        list_req = urls.register(
            method='GET',
            path='/myorg/notices?offset=0&limit=20',
            content={'total_count': 0, 'items': []},
        )

        main(['--show-traceback', 'channel', 'notice', 'list', '-n', 'myorg'])

        urls.assertAllCalled()
        self.assertIn('/myorg/notices', list_req.req.url)

    def test_resolve_notice_owner_rejects_both_channel_and_namespace(self):
        from binstar_client.commands._channel_notices import resolve_notice_owner

        with self.assertRaises(UserError) as ctx:
            resolve_notice_owner('myorg', 'myorg')

        self.assertIn('Cannot specify both channel and --namespace', str(ctx.exception))

    def test_resolve_notice_owner_requires_channel_or_namespace(self):
        from binstar_client.commands._channel_notices import resolve_notice_owner

        with self.assertRaises(UserError) as ctx:
            resolve_notice_owner(None, None)

        self.assertIn('channel or --namespace is required', str(ctx.exception))

    def test_resolve_level_uses_level_picker_when_interactive(self):
        from binstar_client.commands._channel_notices import resolve_level

        with unittest.mock.patch(
            'binstar_client.commands._channel_notices.select_from_list',
            return_value='warning',
        ) as select_mock:
            level = resolve_level(interactive=True)

        self.assertEqual(level, 'warning')
        select_mock.assert_called_once()

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

        self.assertIn('Message is required', str(ctx.exception))

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
                    'x' * 601,
                    '--expires-after',
                    '7',
                ]
            )

        self.assertIn('Message must be at most 600 characters', str(ctx.exception))

    @urlpatch
    @unittest.mock.patch('binstar_client.commands._channel_notices.bool_input', return_value=False)
    @unittest.mock.patch('binstar_client.commands._channel_notices._is_interactive', return_value=True)
    @unittest.mock.patch('binstar_client.commands._channel_notices._prompt_input')
    @freezegun.freeze_time('2026-06-01T12:00:00Z')
    def test_create_notice_interactive_days(self, urls, input_mock, _is_interactive_mock, _bool_mock):
        input_mock.side_effect = ['hello', '30']
        create = urls.register(
            method='POST',
            path='/myteam/notices',
            status=201,
            content={**NOTICE_ITEM, 'status': 'draft'},
        )

        with _patch_notice_console_print(), _patch_level_picker('info'):
            main(['--show-traceback', 'channel', 'notice', 'create', 'myteam'])

        body = json.loads(create.req.body)
        self.assertEqual(body['expires_at'], '2026-07-01T12:00:00+00:00')

    @urlpatch
    @unittest.mock.patch('binstar_client.commands._channel_notices.bool_input', side_effect=[True, False])
    @unittest.mock.patch('binstar_client.commands._channel_notices._is_interactive', return_value=True)
    @unittest.mock.patch('binstar_client.commands._channel_notices._prompt_input')
    @freezegun.freeze_time('2026-06-01T12:00:00Z')
    def test_create_notice_interactive_blank_then_accept_default(
        self, urls, input_mock, _is_interactive_mock, _bool_mock
    ):
        input_mock.side_effect = ['hello', '', '', '']
        create = urls.register(
            method='POST',
            path='/myteam/notices',
            status=201,
            content={**NOTICE_ITEM, 'status': 'draft'},
        )

        with _patch_notice_console_print(), _patch_level_picker('info'):
            main(['--show-traceback', 'channel', 'notice', 'create', 'myteam'])

        body = json.loads(create.req.body)
        self.assertEqual(body['expires_at'], '2026-07-01T12:00:00+00:00')

    @urlpatch
    @unittest.mock.patch('binstar_client.commands._channel_notices.bool_input', side_effect=[False, False])
    @unittest.mock.patch('binstar_client.commands._channel_notices._is_interactive', return_value=True)
    @unittest.mock.patch('binstar_client.commands._channel_notices._prompt_input')
    @freezegun.freeze_time('2026-06-01T12:00:00Z')
    def test_create_notice_interactive_blank_then_decline_default(
        self, urls, input_mock, _is_interactive_mock, _bool_mock
    ):
        input_mock.side_effect = ['hello', '', '', '', '14']
        create = urls.register(
            method='POST',
            path='/myteam/notices',
            status=201,
            content={**NOTICE_ITEM, 'status': 'draft'},
        )

        with _patch_notice_console_print(), _patch_level_picker('info'):
            main(['--show-traceback', 'channel', 'notice', 'create', 'myteam'])

        body = json.loads(create.req.body)
        self.assertEqual(body['expires_at'], '2026-06-15T12:00:00+00:00')

    @urlpatch
    @unittest.mock.patch('binstar_client.commands._channel_notices.bool_input', return_value=True)
    @unittest.mock.patch('binstar_client.commands._channel_notices._is_interactive', return_value=True)
    @unittest.mock.patch('binstar_client.commands._channel_notices._prompt_input')
    def test_create_notice_interactive_publish_yes(self, urls, input_mock, _is_interactive_mock, _bool_mock):
        input_mock.side_effect = ['hello', '2026-09-16T12:00:00+00:00']
        urls.register(
            method='POST',
            path='/myteam/notices',
            status=201,
            content={**NOTICE_ITEM, 'status': 'draft'},
        )
        urls.register(
            method='POST',
            path=f'/myteam/notices/{NOTICE_UUID}/publish',
            content={'id': NOTICE_UUID, 'status': 'published'},
        )

        with _patch_notice_console_print(), _patch_level_picker('info'):
            main(['--show-traceback', 'channel', 'notice', 'create', 'myteam'])

        self.assertIn(f"Notice '{NOTICE_UUID}' published successfully", self.stream.getvalue())

    @urlpatch
    @unittest.mock.patch('binstar_client.commands._channel_notices._is_interactive', return_value=True)
    @unittest.mock.patch('binstar_client.commands._channel_notices._prompt_input')
    def test_update_interactive_keeps_expiry_when_blank(self, urls, input_mock, _is_interactive_mock):
        input_mock.side_effect = ['updated message', '']
        update = urls.register(
            method='PATCH',
            path=f'/myteam/notices/{NOTICE_UUID}',
            content={**NOTICE_ITEM, 'message': 'updated message'},
        )

        with _patch_level_picker('(skip)'):
            main(['--show-traceback', 'channel', 'notice', 'update', 'myteam', NOTICE_UUID])

        body = json.loads(update.req.body)
        self.assertEqual(body['message'], 'updated message')
        self.assertNotIn('expires_at', body)

    @urlpatch
    @unittest.mock.patch('binstar_client.commands._channel_notices._is_interactive', return_value=True)
    @unittest.mock.patch('binstar_client.commands._channel_notices._prompt_input')
    @freezegun.freeze_time('2026-06-01T12:00:00Z')
    def test_update_interactive_days(self, urls, input_mock, _is_interactive_mock):
        input_mock.side_effect = ['', '14']
        update = urls.register(
            method='PATCH',
            path=f'/myteam/notices/{NOTICE_UUID}',
            content={**NOTICE_ITEM, 'expires_at': '2026-06-15T12:00:00Z'},
        )

        with _patch_level_picker('(skip)'):
            main(['--show-traceback', 'channel', 'notice', 'update', 'myteam', NOTICE_UUID])

        body = json.loads(update.req.body)
        self.assertEqual(body['expires_at'], '2026-06-15T12:00:00+00:00')

    @urlpatch
    def test_update_notice_status(self, urls):
        update = urls.register(
            method='PATCH',
            path=f'/myteam/notices/{NOTICE_UUID}',
            content={**NOTICE_ITEM, 'status': 'published'},
        )

        main(
            [
                '--show-traceback',
                'channel',
                'notice',
                'update',
                'myteam',
                NOTICE_UUID,
                '--status',
                'published',
            ]
        )

        urls.assertAllCalled()
        body = json.loads(update.req.body)
        self.assertEqual(body['status'], 'published')

    def test_update_notice_rejects_draft_status(self):
        from binstar_client.commands._channel_notices import validate_update_status

        with self.assertRaises(UserError) as ctx:
            validate_update_status('draft')

        self.assertIn('Cannot set status to draft', str(ctx.exception))

    def test_validate_message_strips_newlines(self):
        from binstar_client.commands._channel_notices import validate_message

        self.assertEqual(validate_message('hello\nworld'), 'hello world')

    def test_validate_message_rejects_ansi_arrow_keys(self):
        from binstar_client.commands._channel_notices import validate_message

        with self.assertRaises(UserError) as ctx:
            validate_message('\x1b[A\x1b[A')

        self.assertIn('Message is required', str(ctx.exception))

    @urlpatch
    def test_list_deleted_notices(self, urls):
        deleted_item = {
            **NOTICE_ITEM,
            'status': 'deleted',
            'id': '8699dc07-c7d7-4988-be88-25ee3a2c3b10',
        }
        list_req = urls.register(
            method='GET',
            path='/myteam/notices?offset=0&limit=20&status=deleted',
            content={'total_count': 1, 'items': [deleted_item]},
        )

        with _patch_notice_console_print():
            main(['--show-traceback', 'channel', 'notice', 'list', 'myteam', '--status', 'deleted'])

        urls.assertAllCalled()
        self.assertIn('status=deleted', list_req.req.url)
        self.assertIn('8699dc07-c7d7-4988-be88-25ee3a2c3b10', self.stream.getvalue())
        self.assertIn('1 notice(s)', self.stream.getvalue())

    @urlpatch
    def test_list_notices_shows_pagination_hint_when_more_pages(self, urls):
        urls.register(
            method='GET',
            path='/myteam/notices?offset=0&limit=20',
            content={'total_count': 25, 'items': [NOTICE_ITEM] * 20},
        )

        with _patch_notice_console_print():
            main(['--show-traceback', 'channel', 'notice', 'list', 'myteam'])

        output = self.stream.getvalue()
        self.assertIn('Showing 1–20 of 25 notices', output)
        self.assertIn('Use --offset 20 for more.', output)

    @urlpatch
    def test_list_notices_renders_ansi_message_safely(self, urls):
        ansi_notice = {
            **NOTICE_ITEM,
            'id': '6268dc4d-1e12-492c-9cdd-10463e998812',
            'message': '\x1b[A\x1b[A',
            'expires_at': '2032-12-12T14:52:29+00:00',
            'status': 'published',
        }
        normal_notice = {
            **NOTICE_ITEM,
            'id': '07625e4d-d844-46fa-845c-d7f91e5e561c',
            'message': 'Updated',
            'status': 'published',
        }
        urls.register(
            method='GET',
            path='/myteam/notices?offset=0&limit=20',
            content={'total_count': 2, 'items': [ansi_notice, normal_notice]},
        )

        with _patch_notice_console_print():
            main(['--show-traceback', 'channel', 'notice', 'list', 'myteam'])

        output = self.stream.getvalue()
        self.assertIn('6268dc4d-1e12-492c-9cdd-10463e998812', output)
        self.assertIn('07625e4d-d844-46fa-845c-d7f91e5e561c', output)
        self.assertIn('2032-12-12T14:52:29+00:00', output)
        self.assertIn('Updated', output)
        self.assertIn('2 notice(s)', output)
