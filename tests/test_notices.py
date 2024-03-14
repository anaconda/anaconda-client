# -*- coding: utf8 -*-
# pylint: disable=missing-function-docstring

"""Tests for notices command."""
import json
import pathlib
import tempfile
from unittest import mock

import pytest

from binstar_client.errors import BinstarError
from binstar_client.commands.notices import NoticesAction

from tests.fixture import CLITestCase, main
from tests.urlmock import urlpatch


class Test(CLITestCase):
    """
    Tests for notices command

    These test all use a mock HTTP backend
    """

    def setUp(self):
        super()
        self.notices_get_config_patch = mock.patch('binstar_client.commands.notices.get_config')
        self.notices_get_config = self.notices_get_config_patch.start()
        self.notices_get_config.return_value = {}

    def tearDown(self):
        self.notices_get_config_patch.stop()

    @urlpatch
    def test_get_notices(self, registry):
        """
        Ensures notices are fetched and displayed as we expect
        """
        user = 'testuser'
        label = 'main'

        registry.register(method='HEAD', path='/', status=200)
        registry.register(method='GET', path='/user', content=f'{{"login": "{user}"}}')
        notices = {
            'notices': [{
                'id': 1,
                'message': 'test message',
                'level': 'info',
                'created_at': '2024-02-22T14:31:24.715857',
                'expires_at': '2025-02-22T14:31:24.715857',
            }]
        }

        registry.register(
            method='GET', path=f'/channels/{user}/{label}/notices', content=notices
        )

        main(['notices', '--get'])

    @urlpatch
    def test_get_notices_with_label_and_user_option(self, registry):
        """
        Ensures notices are fetched and displayed as we expect when using the --label and
        --user options.
        """
        user = 'testuser'
        group = 'testgroup'
        label = 'dev'

        registry.register(method='HEAD', path='/', status=200)
        registry.register(method='GET', path='/user', content=f'{{"login": "{user}"}}')
        notices = {
            'notices': [{
                'id': 1,
                'message': 'test message',
                'level': 'info',
                'created_at': '2024-02-22T14:31:24.715857',
                'expires_at': '2025-02-22T14:31:24.715857',
            }]
        }

        registry.register(
            method="GET", path=f'/channels/{group}/{label}/notices', content=notices
        )

        main(['notices', '--get', '--user', group, '--label', label])

    @urlpatch
    def test_get_notices_no_user_found(self, registry):
        """
        Ensures notices are fetched and displayed as we expect
        """
        registry.register(method='HEAD', path='/', status=200)
        registry.register(method='GET', path='/user', status=200, content='{}')

        error = 'Unable to determine owner in user; please make sure you are logged in'
        with pytest.raises(BinstarError, match=error):
            main(['notices', '--get'])

    @urlpatch
    def test_set_notices(self, registry):
        """
        Ensures notices are set as we expect
        """
        login = 'testuser'
        label = 'main'

        registry.register(method='HEAD', path='/', status=200)
        registry.register(method='GET', path='/user', content=f'{{"login": "{login}"}}')
        registry.register(method='POST', path=f'/channels/{login}/{label}/notices')

        notices_json = json.dumps({
            'notices': [{
                'id': 1,
                'message': 'test message',
                'level': 'info',
                'created_at': '2024-02-22T14:31:24.715857',
                'updated_at': '2024-02-22T14:31:24.715857',
            }]
        })

        main(['notices', '--create', notices_json])

    @urlpatch
    def test_set_notices_from_file(self, registry):
        """
        Ensures notices are set as we expect when read from a notices JSON file
        """
        login = 'testuser'
        label = 'main'

        registry.register(method='HEAD', path='/', status=200)
        registry.register(method='GET', path='/user', content=f'{{"login": "{login}"}}')
        registry.register(method='POST', path=f'/channels/{login}/{label}/notices')

        notices_json = json.dumps({
            'notices': [{
                'id': 1,
                'message': 'test message',
                'level': 'info',
                'created_at': '2024-02-22T14:31:24.715857',
                'updated_at': '2024-02-22T14:31:24.715857',
            }]
        })

        # make temp notices json file
        temp = pathlib.Path(tempfile.mktemp())

        with temp.open("w") as fp:
            fp.write(notices_json)

        main(['notices', '--create', str(temp)])

        temp.unlink()

    @urlpatch
    def test_set_notices_with_label_and_user_option(self, registry):
        """
        Ensures notices are set as we expect
        """
        login = 'testuser'
        group = 'testgroup'
        label = 'dev'

        registry.register(method='HEAD', path='/', status=200)
        registry.register(method='GET', path='/user', content=f'{{"login": "{login}"}}')
        registry.register(method='POST', path=f'/channels/{group}/{label}/notices')

        notices_json = json.dumps({
            'notices': [{
                'id': 1,
                'message': 'test message',
                'level': 'info',
                'created_at': '2024-02-22T14:31:24.715857',
                'updated_at': '2024-02-22T14:31:24.715857',
            }]
        })

        main(['notices', '--user', group, '--label', label, '--create', notices_json])

    @urlpatch
    def test_set_notices_with_bad_json(self, registry):
        """
        Ensures notices are set as we expect
        """
        login = 'testuser'
        label = 'main'

        registry.register(method='HEAD', path='/', status=200)
        registry.register(method='GET', path='/user', content=f'{{"login": "{login}"}}')
        registry.register(method='POST', path=f'/channels/{login}/{label}/notices')

        notices_json = '{"test": "bad_value}'

        mock_target = 'binstar_client.commands.notices.logger'

        with mock.patch(mock_target) as mock_logger:
            with pytest.raises(SystemExit):
                main(['notices', '--create', notices_json])
            assert mock_logger.error.mock_calls == [
                mock.call('Unable to parse provided JSON; please make sure it is valid JSON')
            ]

    @urlpatch
    def test_remove_notices(self, registry):
        """
        Ensures notices are removed as we expect
        """
        login = 'testuser'
        label = 'main'

        registry.register(method='HEAD', path='/', status=200)
        registry.register(method='GET', path='/user', content=f'{{"login": "{login}"}}')
        registry.register(method='DELETE', path=f'/channels/{login}/{label}/notices')

        main(['notices', '--remove'])

    @urlpatch
    def test_remove_notices_with_label_and_user_option(self, registry):
        """
        Ensures notices are set as we expect
        """
        login = 'testuser'
        group = 'testgroup'
        label = 'dev'

        registry.register(method='HEAD', path='/', status=200)
        registry.register(method='GET', path='/user', content=f'{{"login": "{login}"}}')
        registry.register(method='DELETE', path=f'/channels/{group}/{label}/notices')

        main(['notices', '--user', group, '--label', label, '--remove'])

    def test_notices_action_bad_values(self):
        action = NoticesAction('--notices', 'notices')

        mock_target = 'binstar_client.commands.notices.logger'

        with mock.patch(mock_target) as mock_logger:
            with pytest.raises(SystemExit):
                action(None, None, ['test', 'test_value'])
            assert mock_logger.error.mock_calls == [
                mock.call('Notices argument must be defined as a string')
            ]

    def test_notices_action_error_opening_file(self):
        action = NoticesAction('--notices', 'notices')

        mock_logger_target = 'binstar_client.commands.notices.logger'
        mock_pathlib_target = 'binstar_client.commands.notices.pathlib'

        with mock.patch(mock_logger_target) as mock_logger, \
                mock.patch(mock_pathlib_target) as mock_pathlib:

            error = 'test error'
            mock_pathlib.Path().open.side_effect = OSError(error)

            with pytest.raises(SystemExit):
                action(None, None, ['test', 'test_value'])
            assert mock_logger.error.mock_calls == [
                mock.call(f'Unable to read provided JSON file: {error}')
            ]
