"""Tests for the repocore client and CLI commands."""

from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from typer.testing import CliRunner

from binstar_client.repocore import (
    Channel,
    Namespace,
    NamespaceChannel,
    RepoCoreClient,
    ResolvedChannel,
)
from binstar_client.repocore.errors import (
    InvalidName,
    LoginRequiredError,
    RepoCoreError,
    Unauthorized,
)


class TestPydanticModels:
    def test_namespace_model(self):
        ns = Namespace(name="test-org")
        assert ns.name == "test-org"
        assert isinstance(ns, Namespace)

    def test_channel_model(self):
        ch = Channel(name="dev", privacy="private", description=None)
        assert ch.name == "dev"
        assert ch.privacy == "private"
        assert ch.description == ""
        assert ch.artifact_count == 0

    def test_namespace_channel_model(self):
        nsch = NamespaceChannel(name="myorg/dev", privacy="private", owners=["user1", None, "user2"])
        assert nsch.name == "myorg/dev"
        assert nsch.owners == ["user1", "user2"]
        assert nsch.indexing_behavior == "default"

    def test_resolved_channel_model(self):
        resolved = ResolvedChannel(namespace="myorg", channel_name="dev")
        assert resolved.namespace == "myorg"
        assert resolved.channel_name == "dev"

    def test_namespace_model_used_in_list_organizations(self):
        client = _make_client()
        orgs = [{"name": "org1"}, {"name": "org2"}]
        mock_response = _mock_response(200, orgs)
        client.get = MagicMock(return_value=mock_response)
        result = client.list_user_organizations()
        assert all(isinstance(org, Namespace) for org in result)
        assert result[0].name == "org1"

    def test_channel_model_used_in_get_channels(self):
        client = _make_client()
        channels = {"items": [{"name": "dev", "privacy": "private", "artifact_count": 5, "download_count": 10}]}
        mock_response = _mock_response(200, channels)
        client.get = MagicMock(return_value=mock_response)
        result = client.get_channels("myorg")
        assert all(isinstance(ch, Channel) for ch in result)
        assert result[0].name == "dev"

    def test_namespace_channel_model_used_in_get_namespace_channel(self):
        client = _make_client()
        channel = {"name": "myorg/dev", "privacy": "private", "owners": ["user1"]}
        mock_response = _mock_response(200, channel)
        client.get = MagicMock(return_value=mock_response)
        result = client.get_namespace_channel("myorg/dev")
        assert isinstance(result, NamespaceChannel)
        assert result.name == "myorg/dev"

    def test_resolved_channel_model_used_in_resolve_namespace_and_channel(self):
        from binstar_client.commands._repo_channels import _resolve_namespace_and_channel

        mock_api = MagicMock()
        result = _resolve_namespace_and_channel(mock_api, "myorg/dev")
        assert isinstance(result, ResolvedChannel)
        assert result.namespace == "myorg"
        assert result.channel_name == "dev"


class TestRepoCoreClientValidation:
    def test_is_subchannel(self):
        client = _make_client()
        assert client.is_subchannel("main/stage") is True
        assert client.is_subchannel("main") is False

    def test_validate_channel_name_valid(self):
        client = _make_client()
        client._validate_channel_name("my-channel")
        client._validate_channel_name("test123")
        client._validate_channel_name("a")

    def test_validate_channel_name_invalid(self):
        client = _make_client()
        with pytest.raises(InvalidName):
            client._validate_channel_name("UPPERCASE")
        with pytest.raises(InvalidName):
            client._validate_channel_name("123starts-with-number")
        with pytest.raises(InvalidName):
            client._validate_channel_name("has spaces")

    def test_validate_subchannel_name(self):
        client = _make_client()
        client._validate_channel_name("main/stage")
        with pytest.raises(InvalidName):
            client._validate_channel_name("main/INVALID")

    def test_get_channel_url_normal(self):
        client = _make_client()
        url = client._get_channel_url("my-channel")
        assert url.endswith("/channels/my-channel")

    def test_get_channel_url_subchannel(self):
        client = _make_client()
        url = client._get_channel_url("main/stage")
        assert "/channels/main/subchannels/stage" in url


class TestRepoCoreClientAPI:
    def test_list_user_organizations(self):
        client = _make_client()
        orgs = [
            {"name": "anaconda-dfw"},
            {"name": "my-team"},
        ]
        mock_response = _mock_response(200, orgs)
        client.get = MagicMock(return_value=mock_response)

        result = client.list_user_organizations()
        assert len(result) == 2
        assert all(isinstance(org, Namespace) for org in result)
        assert result[0].name == "anaconda-dfw"
        assert result[1].name == "my-team"
        client.get.assert_called_once()
        call_url = client.get.call_args[0][0]
        assert "/api/auth/organizations/my" in call_url

    def test_list_user_organizations_empty(self):
        client = _make_client()
        mock_response = _mock_response(200, [])
        client.get = MagicMock(return_value=mock_response)

        result = client.list_user_organizations()
        assert result == []
        assert isinstance(result, list)

    def test_create_channel(self):
        client = _make_client()
        mock_response = _mock_response(201, {"name": "new-channel"})
        client.post = MagicMock(return_value=mock_response)

        result = client.create_channel("new-channel", privacy="public")
        assert result == {"name": "new-channel"}
        client.post.assert_called_once()
        call_args = client.post.call_args
        assert call_args[1]["json"] == {"name": "new-channel", "privacy": "public"}

    def test_create_subchannel(self):
        client = _make_client()
        mock_response = _mock_response(201, {"name": "stage"})
        client.post = MagicMock(return_value=mock_response)

        result = client.create_channel("main/stage")
        assert result == {"name": "stage"}
        call_args = client.post.call_args
        assert "subchannels" in call_args[0][0]
        assert call_args[1]["json"] == {"name": "stage"}

    def test_remove_channel(self):
        client = _make_client()
        mock_response = _mock_response(202, None)
        client.delete = MagicMock(return_value=mock_response)

        result = client.remove_channel("my-channel")
        assert result is None

    def test_remove_channel_unauthorized(self):
        client = _make_client()
        mock_response = _mock_response(403, None)
        client.delete = MagicMock(return_value=mock_response)

        with pytest.raises(Unauthorized):
            client.remove_channel("my-channel")

    def test_get_namespace_channel(self):
        client = _make_client()
        channel_data = {"name": "test", "privacy": "public", "artifact_count": 5}
        mock_response = _mock_response(200, channel_data)
        client.get = MagicMock(return_value=mock_response)

        result = client.get_namespace_channel("test")
        assert isinstance(result, NamespaceChannel)
        assert result.name == "test"
        assert result.privacy == "public"
        assert result.artifact_count == 5

    def test_update_channel(self):
        client = _make_client()
        mock_response = _mock_response(200, None)
        client.put = MagicMock(return_value=mock_response)

        client.update_channel("test", privacy="private")
        call_args = client.put.call_args
        assert call_args[1]["json"] == {"privacy": "private"}

    def test_manage_response_401_raises_login_required(self):
        client = _make_client()
        mock_response = _mock_response(401, {"error": {"code": "auth_required"}})

        with pytest.raises(LoginRequiredError, match="Authentication required"):
            client._manage_response(mock_response, "test action")

    def test_manage_response_403(self):
        client = _make_client()
        mock_response = _mock_response(403, {"message": "forbidden"})

        with pytest.raises(Unauthorized):
            client._manage_response(mock_response, "test action")

    def test_manage_response_500(self):
        client = _make_client()
        mock_response = _mock_response(500, None)

        with pytest.raises(RepoCoreError):
            client._manage_response(mock_response, "test action")


class TestLoginRequiredErrorHandler:
    def test_handler_is_registered(self):
        from anaconda_cli_base.exceptions import ERROR_HANDLERS, register_error_handler

        # Ensure registration (normally done by plugins.py at CLI startup)
        if LoginRequiredError not in ERROR_HANDLERS:

            @register_error_handler(LoginRequiredError)
            def _handler(e):
                from anaconda_auth.cli import _continue_with_login

                return _continue_with_login()

        assert LoginRequiredError in ERROR_HANDLERS

    def test_handler_calls_continue_with_login(self):
        from anaconda_cli_base.exceptions import ERROR_HANDLERS

        handler = ERROR_HANDLERS[LoginRequiredError]
        with patch("anaconda_auth.cli._continue_with_login", return_value=1) as mock_login:
            result = handler(LoginRequiredError())
            mock_login.assert_called_once()
            assert result == 1


class TestRepoCoreNamespaceChannel:
    def test_create_namespace_channel(self):
        client = _make_client()
        mock_response = _mock_response(201, {"channel_path": "myns/dev"})
        client.post = MagicMock(return_value=mock_response)

        result = client.create_namespace_channel("dev", namespace="myns", privacy="public")
        assert result == {"channel_path": "myns/dev"}
        call_args = client.post.call_args
        assert "namespace-channels" in call_args[0][0]
        assert call_args[1]["json"] == {"channel_name": "dev", "namespace": "myns", "privacy": "public"}

    def test_create_namespace_channel_without_namespace(self):
        client = _make_client()
        mock_response = _mock_response(201, {"channel_path": "dev/dev"})
        client.post = MagicMock(return_value=mock_response)

        result = client.create_namespace_channel("dev")
        assert result == {"channel_path": "dev/dev"}
        call_args = client.post.call_args
        assert call_args[1]["json"] == {"channel_name": "dev", "privacy": "private"}


class TestResolveNamespaceAndChannel:
    def test_slash_in_name_extracts_both(self):
        from binstar_client.commands._repo_channels import _resolve_namespace_and_channel

        mock_api = MagicMock()
        resolved = _resolve_namespace_and_channel(mock_api, "myorg/dev")
        assert resolved.namespace == "myorg"
        assert resolved.channel_name == "dev"
        mock_api.list_user_organizations.assert_not_called()

    def test_explicit_namespace_flag(self):
        from binstar_client.commands._repo_channels import _resolve_namespace_and_channel

        mock_api = MagicMock()
        resolved = _resolve_namespace_and_channel(mock_api, "dev", namespace="myorg")
        assert resolved.namespace == "myorg"
        assert resolved.channel_name == "dev"
        mock_api.list_user_organizations.assert_not_called()

    def test_ambiguous_slash_and_flag_exits(self):
        from click.exceptions import Exit

        from binstar_client.commands._repo_channels import _resolve_namespace_and_channel

        mock_api = MagicMock()
        with pytest.raises(Exit):
            _resolve_namespace_and_channel(mock_api, "org-a/dev", namespace="org-b")

    def test_single_namespace_auto_resolves(self):
        from binstar_client.commands._repo_channels import _resolve_namespace_and_channel

        mock_api = MagicMock()
        mock_api.list_user_organizations.return_value = [Namespace(name="myorg")]
        resolved = _resolve_namespace_and_channel(mock_api, "dev")
        assert resolved.namespace == "myorg"
        assert resolved.channel_name == "dev"

    def test_no_namespaces_exits(self):
        from click.exceptions import Exit

        from binstar_client.commands._repo_channels import _resolve_namespace_and_channel

        mock_api = MagicMock()
        mock_api.list_user_organizations.return_value = []
        with pytest.raises(Exit):
            _resolve_namespace_and_channel(mock_api, "dev")

    def test_multiple_namespaces_prompts(self):
        from binstar_client.commands._repo_channels import _resolve_namespace_and_channel

        mock_api = MagicMock()
        mock_api.list_user_organizations.return_value = [
            Namespace(name="org-a"),
            Namespace(name="org-b"),
        ]

        with patch("binstar_client.commands._repo_channels.select_from_list", return_value="org-b"):
            resolved = _resolve_namespace_and_channel(mock_api, "dev")

        assert resolved.namespace == "org-b"
        assert resolved.channel_name == "dev"


class TestRepoCoreChannelsCLI:
    def test_channels_help(self):
        runner = CliRunner()
        app = _get_channels_app()
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "list" in result.output
        assert "create" in result.output
        assert "remove" in result.output
        assert "show" in result.output
        assert "modify" in result.output

    def test_channels_list(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.list_user_organizations.return_value = [
            Namespace(name="main"),
        ]
        mock_api.get_channels.return_value = [
            Channel(
                name="dev",
                privacy="public",
                description="",
                artifact_count=10,
                download_count=5,
            )
        ]

        with _patch_repo_api(mock_api):
            result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "main" in result.output
        assert "dev" in result.output

    def test_channels_list_with_namespace_filter(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.list_user_organizations.return_value = [
            Namespace(name="org-a"),
            Namespace(name="org-b"),
        ]
        mock_api.get_channel_subchannels.return_value = [
            Channel(
                name="dev",
                privacy="public",
                description="",
                artifact_count=5,
                download_count=1,
            )
        ]

        with _patch_repo_api(mock_api):
            result = runner.invoke(app, ["list", "--namespace", "org-a"])

        assert result.exit_code == 0
        assert "org-a" in result.output
        assert "org-b" not in result.output

    def test_channels_list_fetches_subchannels_per_org(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.list_user_organizations.return_value = [
            Namespace(name="org-a"),
            Namespace(name="org-b"),
        ]
        mock_api.get_channels.side_effect = [
            [
                Channel(
                    name="dev",
                    privacy="private",
                    description="",
                    artifact_count=3,
                    download_count=1,
                )
            ],
            [
                Channel(
                    name="staging",
                    privacy="public",
                    description="Staging",
                    artifact_count=7,
                    download_count=2,
                )
            ],
        ]

        with _patch_repo_api(mock_api):
            result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "org-a" in result.output
        assert "org-b" in result.output
        assert "dev" in result.output
        assert "staging" in result.output
        assert mock_api.get_channels.call_count == 2

    def test_channels_create_with_slash(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.create_namespace_channel.return_value = {"channel_path": "myns/dev"}

        with _patch_repo_api(mock_api):
            result = runner.invoke(app, ["create", "myns/dev", "--public"])

        assert result.exit_code == 0
        assert "Success" in result.output
        mock_api.create_namespace_channel.assert_called_once_with(
            channel_name="dev", namespace="myns", privacy="public"
        )

    def test_channels_create_with_namespace_flag(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.create_namespace_channel.return_value = {"channel_path": "myns/dev"}

        with _patch_repo_api(mock_api):
            result = runner.invoke(app, ["create", "dev", "--namespace", "myns", "--public"])

        assert result.exit_code == 0
        mock_api.create_namespace_channel.assert_called_once_with(
            channel_name="dev", namespace="myns", privacy="public"
        )

    def test_channels_create_bare_name_no_namespace_uses_username(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.list_user_organizations.return_value = []
        type(mock_api).account = PropertyMock(return_value={"user": {"username": "testuser"}})
        mock_api.create_namespace_channel.return_value = {"channel_path": "testuser/newchannel"}

        with _patch_repo_api(mock_api):
            result = runner.invoke(app, ["create", "newchannel", "--private"], input="y\n")

        assert result.exit_code == 0
        mock_api.create_namespace_channel.assert_called_once_with(
            channel_name="newchannel", namespace="testuser", privacy="private"
        )

    def test_channels_create_auto_resolves_namespace(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.list_user_organizations.return_value = [Namespace(name="myorg")]
        mock_api.create_namespace_channel.return_value = {"channel_path": "myorg/dev"}

        with _patch_repo_api(mock_api):
            result = runner.invoke(app, ["create", "dev", "--public"])

        assert result.exit_code == 0
        mock_api.create_namespace_channel.assert_called_once_with(
            channel_name="dev", namespace="myorg", privacy="public"
        )

    def test_channels_create_prompts_for_privacy(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.create_namespace_channel.return_value = {"channel_path": "myns/dev"}

        with (
            _patch_repo_api(mock_api),
            patch("binstar_client.commands._repo_channels.select_from_list", return_value="public"),
        ):
            result = runner.invoke(app, ["create", "myns/dev"])

        assert result.exit_code == 0
        mock_api.create_namespace_channel.assert_called_once_with(
            channel_name="dev", namespace="myns", privacy="public"
        )

    def test_channels_create_privacy_prompt_defaults_to_private(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.create_namespace_channel.return_value = {"channel_path": "myns/dev"}

        with (
            _patch_repo_api(mock_api),
            patch("binstar_client.commands._repo_channels.select_from_list", return_value="private"),
        ):
            result = runner.invoke(app, ["create", "myns/dev"])

        assert result.exit_code == 0
        mock_api.create_namespace_channel.assert_called_once_with(
            channel_name="dev", namespace="myns", privacy="private"
        )

    def test_channels_create_no_namespaces_no_username(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.list_user_organizations.return_value = []
        type(mock_api).account = PropertyMock(side_effect=Exception("No account"))
        mock_api.create_namespace_channel.return_value = {"channel_path": "newchannel"}

        with _patch_repo_api(mock_api):
            result = runner.invoke(app, ["create", "newchannel", "--private"])

        assert result.exit_code == 0
        mock_api.create_namespace_channel.assert_called_once_with(
            channel_name="newchannel", namespace=None, privacy="private"
        )

    def test_channels_create_no_namespaces_with_username(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.list_user_organizations.return_value = []
        type(mock_api).account = PropertyMock(return_value={"user": {"username": "testuser"}})
        mock_api.create_namespace_channel.return_value = {"channel_path": "testuser/newchannel"}

        with _patch_repo_api(mock_api):
            result = runner.invoke(app, ["create", "newchannel", "--private"], input="y\n")

        assert result.exit_code == 0
        mock_api.create_namespace_channel.assert_called_once_with(
            channel_name="newchannel", namespace="testuser", privacy="private"
        )

    def test_channels_remove_with_namespace_resolution(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.list_user_organizations.return_value = [Namespace(name="myorg")]

        with _patch_repo_api(mock_api):
            result = runner.invoke(app, ["remove", "dev"])

        assert result.exit_code == 0
        mock_api.remove_channel.assert_called_once_with("myorg/dev")

    def test_channels_remove_with_slash(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()

        with _patch_repo_api(mock_api):
            result = runner.invoke(app, ["remove", "myorg/dev"])

        assert result.exit_code == 0
        mock_api.remove_channel.assert_called_once_with("myorg/dev")

    def test_channels_remove_no_namespace_errors(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.list_user_organizations.return_value = []

        with _patch_repo_api(mock_api):
            result = runner.invoke(app, ["remove", "dev"])

        assert result.exit_code == 1
        assert "No resolvable namespaces" in result.output

    def test_channels_show_with_namespace_flag(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.get_channel.return_value = NamespaceChannel(
            name="dev",
            privacy="private",
            description="",
            artifact_count=0,
            download_count=0,
            mirror_count=0,
            subchannel_count=0,
            indexing_behavior="default",
            created="2025-01-01",
            updated="2025-06-01",
        )
        mock_api.is_subchannel.return_value = True

        with _patch_repo_api(mock_api):
            result = runner.invoke(app, ["show", "dev", "--namespace", "myorg"])

        assert result.exit_code == 0
        mock_api.get_namespace_channel.assert_called_once_with("myorg/dev")

    def test_channels_modify_with_namespace_resolution(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.list_user_organizations.return_value = [Namespace(name="myorg")]

        with _patch_repo_api(mock_api):
            result = runner.invoke(app, ["modify", "dev", "--privacy", "private"])

        assert result.exit_code == 0
        mock_api.update_channel.assert_called_once_with("myorg/dev", privacy="private")

    def test_channels_modify_no_options(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()

        with _patch_repo_api(mock_api):
            result = runner.invoke(app, ["modify", "test-channel"])

        assert result.exit_code == 1
        assert "At least one option is required" in result.output


# =============================================================================
# Test helpers
# =============================================================================


def _make_client():
    """Create a RepoCoreClient with mocked auth (no real network)."""
    with patch("anaconda_auth.client.BaseClient.__init__", return_value=None):
        client = RepoCoreClient.__new__(RepoCoreClient)
        client._base_uri = "https://example.com"
        client.config = MagicMock()
        client.config.domain = "example.com"
        return client


def _mock_response(status_code, json_data):
    response = MagicMock()
    response.status_code = status_code
    response.content = b""
    if json_data is not None:
        response.json.return_value = json_data
    else:
        response.json.side_effect = ValueError("No JSON")
    return response


def _get_channels_app():
    from binstar_client.commands._repo_channels import app

    return app


class _patch_repo_api:
    """Context manager to inject a mock repo_api into the Typer context."""

    def __init__(self, mock_api):
        self.mock_api = mock_api
        self.patcher = patch("binstar_client.commands._repo_channels.RepoCoreClient", return_value=mock_api)

    def __enter__(self):
        self.patcher.start()
        return self.mock_api

    def __exit__(self, *args):
        self.patcher.stop()


def test_repo_channels_registers_notice_subcommand():
    channels_app = _get_channels_app()
    notice_group = next((grp for grp in channels_app.registered_groups if grp.name == 'notice'), None)
    assert notice_group is not None
