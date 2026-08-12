"""Tests for the repocore client and CLI commands."""

from unittest.mock import MagicMock, PropertyMock, patch

import pytest
import typer
from typer.testing import CliRunner

from binstar_client.repocore import (
    Channel,
    ChannelCreationResponse,
    ChannelUpdateResponse,
    Namespace,
    RepoCoreClient,
    ResolvedChannel,
)
from binstar_client.repocore.errors import (
    InvalidName,
    RepoCoreError,
    Unauthorized,
)


def _namespace_channels(*names):
    """Build a ``list_my_channels`` return value from top-level channel names.

    The resolver derives namespaces from the caller's own + shared top-level
    channels; a single unpaged page is enough for tests.
    """
    return ([Channel(name=n, privacy="private") for n in names], len(names), None)


def _readable_channels(*channels):
    """Build a ``list_my_channels`` return value from ``(name, parent)`` pairs.

    A ``parent`` of ``None`` is a top-level channel (a namespace); a non-None
    parent makes it a subchannel under that namespace.

    Matches ``list_my_channels``'s ``(items, total_count, error)`` signature;
    the trailing ``None`` is the error slot (no error).
    """
    items = [Channel(name=name, privacy="private", parent=parent) for name, parent in channels]
    return (items, len(items), None)


def _channels_with_access(*channels):
    """Build a ``list_my_channels`` return value from ``(name, parent, access)`` triples.

    Like :func:`_readable_channels` but stamps each channel's ``access`` level
    (``"viewer"``/``"collaborator"``/``"owner"``/``None``) so resolver tests can
    exercise the writable filter. The trailing ``None`` is the error slot.
    """
    items = [Channel(name=name, privacy="private", parent=parent, access=access) for name, parent, access in channels]
    return (items, len(items), None)


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
        nsch = Channel(name="myorg/dev", privacy="private", owners=["user1", None, "user2"])
        assert nsch.name == "myorg/dev"
        assert nsch.owners == ["user1", "user2"]
        assert nsch.indexing_behavior == "default"

    def test_resolved_channel_model(self):
        resolved = ResolvedChannel(namespace="myorg", channel_name="dev")
        assert resolved.namespace == "myorg"
        assert resolved.channel_name == "dev"

    def test_accepts_package_type(self):
        resolved = ResolvedChannel(
            namespace="myorg", channel_name="dev", accepted_package_types=frozenset({"conda", "pypi"})
        )
        assert resolved.accepts_package_type("conda")
        assert not resolved.accepts_package_type("ipynb")
        # None (autodetect) is always acceptable; validation happens at upload.
        assert resolved.accepts_package_type(None)

    def test_accepts_package_type_empty_set_accepts_anything(self):
        # An unpopulated set means "do not validate here".
        resolved = ResolvedChannel(namespace="myorg", channel_name="dev")
        assert resolved.accepts_package_type("anything")

    def test_org_target_requires_owner(self):
        # A dotorg target with no owner has nothing to upload to; reject it.
        with pytest.raises(ValueError):
            ResolvedChannel(namespace=None, channel_name="someowner", target="org")

    def test_org_target_with_owner_is_valid(self):
        resolved = ResolvedChannel(namespace=None, channel_name="someowner", target="org", owner="someowner")
        assert resolved.owner == "someowner"

    def test_repo_target_needs_no_owner(self):
        resolved = ResolvedChannel(namespace="myorg", channel_name="dev", target="repo")
        assert resolved.owner is None

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
        result, error = client.get_channels("myorg")
        assert error is None
        assert all(isinstance(ch, Channel) for ch in result)
        assert result[0].name == "dev"

    def test_namespace_channel_model_used_in_get_namespace_channel(self):
        client = _make_client()
        channel = {"name": "myorg/dev", "privacy": "private", "owners": ["user1"]}
        mock_response = _mock_response(200, channel)
        client.get = MagicMock(return_value=mock_response)
        result, error = client.get_namespace_channel("myorg/dev")
        assert error is None
        assert isinstance(result, Channel)
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

    def test_list_all_channels(self):
        client = _make_client()
        payload = {
            "total_count": 2,
            "items": [
                {"name": "myorg", "privacy": "public"},
                {"name": "dev", "privacy": "private", "parent": "myorg", "artifact_count": 3},
            ],
        }
        mock_response = _mock_response(200, payload)
        client.get = MagicMock(return_value=mock_response)

        items, total, error = client.list_all_channels()

        assert error is None
        assert total == 2
        assert all(isinstance(ch, Channel) for ch in items)
        # The flat listing hits /channels with include_subchannels so shared
        # channels (subchannels under namespaces the user doesn't own) come back.
        call_url = client.get.call_args[0][0]
        assert call_url.endswith("/api/repo/channels")
        assert client.get.call_args[1]["params"]["include_subchannels"] is True
        # A subchannel's namespace is its parent; path reconstructs namespace/channel.
        assert items[0].namespace is None
        assert items[0].path == "myorg"
        assert items[1].namespace == "myorg"
        assert items[1].path == "myorg/dev"

        # An error response yields an empty page rather than raising.
        client.get = MagicMock(return_value=_mock_response(403, None))
        items, total, error = client.list_all_channels()
        assert (items, total) == ([], 0)
        assert isinstance(error, Unauthorized)

    def test_list_my_channels(self):
        client = _make_client()
        payload = {
            "total_count": 2,
            "items": [
                {"name": "myorg", "privacy": "public"},
                {
                    "name": "dev",
                    "privacy": "private",
                    "parent": "myorg",
                    "artifact_count": 3,
                    "access": "collaborator",
                },
            ],
        }
        client.get = MagicMock(return_value=_mock_response(200, payload))

        items, total, error = client.list_my_channels()

        assert error is None
        assert total == 2
        assert all(isinstance(ch, Channel) for ch in items)
        # Hits /account/channels (own + shared only), with subchannels included.
        call_url = client.get.call_args[0][0]
        assert call_url.endswith("/api/repo/account/channels")
        assert client.get.call_args[1]["params"]["include_subchannels"] is True
        assert items[1].path == "myorg/dev"
        # /account/channels surfaces the caller's access level on each channel.
        assert items[1].access == "collaborator"
        assert items[0].access is None

        # An error response yields an empty page rather than raising.
        client.get = MagicMock(return_value=_mock_response(403, None))
        items, total, error = client.list_my_channels()
        assert (items, total) == ([], 0)
        assert isinstance(error, Unauthorized)

    def test_create_channel(self):
        client = _make_client()
        mock_response = _mock_response(201, {"name": "new-channel"})
        client.post = MagicMock(return_value=mock_response)

        result, error = client.create_channel("new-channel", privacy="public")
        assert error is None
        assert result == {"name": "new-channel"}
        client.post.assert_called_once()
        call_args = client.post.call_args
        assert call_args[1]["json"] == {"name": "new-channel", "privacy": "public"}

    def test_create_subchannel(self):
        client = _make_client()
        mock_response = _mock_response(201, {"name": "stage"})
        client.post = MagicMock(return_value=mock_response)

        result, error = client.create_channel("main/stage")
        assert error is None
        assert result == {"name": "stage"}
        call_args = client.post.call_args
        assert "subchannels" in call_args[0][0]
        assert call_args[1]["json"] == {"name": "stage"}

    def test_remove_channel(self):
        client = _make_client()
        mock_response = _mock_response(202, None)
        client.delete = MagicMock(return_value=mock_response)

        result, error = client.remove_channel("my-channel")
        assert error is None
        assert result is None

    def test_remove_channel_unauthorized(self):
        client = _make_client()
        mock_response = _mock_response(403, None)
        client.delete = MagicMock(return_value=mock_response)

        result, error = client.remove_channel("my-channel")
        assert error is not None
        assert isinstance(error, Unauthorized)

    def test_get_namespace_channel(self):
        client = _make_client()
        channel_data = {"name": "test", "privacy": "public", "artifact_count": 5}
        mock_response = _mock_response(200, channel_data)
        client.get = MagicMock(return_value=mock_response)

        result, error = client.get_namespace_channel("test")
        assert error is None
        assert isinstance(result, Channel)
        assert result.name == "test"
        assert result.privacy == "public"
        assert result.artifact_count == 5

        # An error response carries no channel to build, so no model is attempted.
        client.get = MagicMock(return_value=_mock_response(403, None))
        result, error = client.get_namespace_channel("test")
        assert result is None
        assert isinstance(error, Unauthorized)

    def test_update_channel(self):
        client = _make_client()
        # 200 + {"changed": true} => the server applied a change.
        client.put = MagicMock(return_value=_mock_response(200, {"changed": True}))

        result, error = client.update_channel("test", privacy="private")
        call_args = client.put.call_args
        assert call_args[1]["json"] == {"privacy": "private"}
        assert error is None
        assert result.changed is True

    def test_update_channel_no_op_returns_unchanged(self):
        client = _make_client()
        # 200 + {"changed": false} => the channel already held the submitted value.
        client.put = MagicMock(return_value=_mock_response(200, {"changed": False}))

        result, error = client.update_channel("test", privacy="private")
        assert error is None
        assert result.changed is False

    def test_manage_response_401_raises_unauthorized(self):
        client = _make_client()
        mock_response = _mock_response(401, {"error": {"code": "auth_required", "message": "Invalid token"}})

        result, error = client._manage_response(mock_response, "test action")
        assert result == {"error": {"code": "auth_required", "message": "Invalid token"}}
        assert isinstance(error, Unauthorized)
        assert "Invalid token" in str(error)

    def test_manage_response_403(self):
        client = _make_client()
        mock_response = _mock_response(403, {"message": "forbidden"})

        result, error = client._manage_response(mock_response, "test action")
        assert result == {"message": "forbidden"}
        assert isinstance(error, Unauthorized)

    def test_manage_response_500(self):
        client = _make_client()
        mock_response = _mock_response(500, None)

        result, error = client._manage_response(mock_response, "test action")
        assert result is None
        assert isinstance(error, RepoCoreError)


class TestRepoCoreNamespaceChannel:
    def test_create_namespace_channel(self):
        client = _make_client()
        mock_response = _mock_response(201, {"channel_path": "myns/dev"})
        client.post = MagicMock(return_value=mock_response)

        result, error = client.create_namespace_channel("dev", namespace="myns", privacy="public")
        assert error is None
        assert result.channel_path == "myns/dev"
        assert result.status_code == 201
        assert result.created is True
        call_args = client.post.call_args
        assert "namespace-channels" in call_args[0][0]
        assert call_args[1]["json"] == {"channel_name": "dev", "namespace": "myns", "privacy": "public"}

    def test_create_namespace_channel_without_namespace(self):
        client = _make_client()
        mock_response = _mock_response(201, {"channel_path": "dev/dev"})
        client.post = MagicMock(return_value=mock_response)

        result, error = client.create_namespace_channel("dev")
        assert error is None
        assert result.channel_path == "dev/dev"
        assert result.status_code == 201
        assert result.created is True
        call_args = client.post.call_args
        assert call_args[1]["json"] == {"channel_name": "dev", "privacy": "private"}

    def test_create_namespace_channel_already_exists(self):
        client = _make_client()
        mock_response = _mock_response(200, {"channel_path": "myns/dev"})
        client.post = MagicMock(return_value=mock_response)

        result, error = client.create_namespace_channel("dev", namespace="myns")
        assert error is None
        assert result.channel_path == "myns/dev"
        assert result.status_code == 200
        assert result.created is False

        # An error response has no channel_path to build, so no model is attempted.
        client.post = MagicMock(return_value=_mock_response(403, None))
        result, error = client.create_namespace_channel("dev", namespace="myns")
        assert result is None
        assert isinstance(error, Unauthorized)

    def test_share_channel_role_mapping(self):
        client = _make_client()
        mock_response = _mock_response(200, {})
        client.post = MagicMock(return_value=mock_response)

        client.share_channel("myns", "dev", "testuser", action="share", grant="read")
        call_args = client.post.call_args
        assert call_args[1]["json"] == {"action": "share", "user": "testuser", "grant": "read"}
        assert "grant" in call_args[1]["json"]

        client.share_channel("myns", "dev", "testuser", action="share", grant="write")
        call_args = client.post.call_args
        assert call_args[1]["json"] == {"action": "share", "user": "testuser", "grant": "write"}
        assert "grant" in call_args[1]["json"]

    def test_share_channel_unshare_no_grant(self):
        client = _make_client()
        mock_response = _mock_response(200, {})
        client.post = MagicMock(return_value=mock_response)

        client.share_channel("myns", "dev", "testuser", action="unshare", grant="read")
        call_args = client.post.call_args
        assert call_args[1]["json"] == {"action": "unshare", "user": "testuser"}
        assert "grant" not in call_args[1]["json"]


class TestRepoCoreArtifacts:
    def test_list_artifacts(self):
        client = _make_client()
        payload = {
            "total_count": 2,
            "items": [
                {"name": "numpy", "family": "conda", "file_count": 3, "available_versions": ["1.0", "2.0"]},
                {"name": "flask", "family": "python", "download_count": 7},
            ],
        }
        client.get = MagicMock(return_value=_mock_response(200, payload))

        items, total = client.list_artifacts("myns/dev", query="num")

        assert total == 2
        assert [a.name for a in items] == ["numpy", "flask"]
        call_url = client.get.call_args[0][0]
        # Subchannel arg routes through /subchannels/ and appends /artifacts.
        assert call_url.endswith("/channels/myns/subchannels/dev/artifacts")
        assert client.get.call_args[1]["params"]["q"] == "num"

    def test_list_artifact_files(self):
        client = _make_client()
        payload = {
            "total_count": 1,
            "items": [{"ckey": "linux-64/numpy-2.2.5-py313.conda", "name": "numpy", "family": "conda", "size": 100}],
        }
        client.get = MagicMock(return_value=_mock_response(200, payload))

        items, total = client.list_artifact_files("myns/dev", "conda", "numpy")

        assert total == 1
        assert items[0].filename == "numpy-2.2.5-py313.conda"
        call_url = client.get.call_args[0][0]
        assert call_url.endswith("/channels/myns/subchannels/dev/artifacts/conda/numpy/files")

    def test_delete_artifact_file_uses_bulk_with_ckey(self):
        client = _make_client()
        client.put = MagicMock(return_value=_mock_response(202, None))

        client.delete_artifact_file("myns/dev", "conda", "numpy", "linux-64/numpy-2.2.5-py313.conda")

        call_url = client.put.call_args[0][0]
        assert call_url.endswith("/artifacts/bulk")
        body = client.put.call_args[1]["json"]
        assert body["action"] == "delete"
        assert body["items"] == [{"name": "numpy", "family": "conda", "ckey": "linux-64/numpy-2.2.5-py313.conda"}]

    def test_delete_artifact_file_unauthorized(self):
        client = _make_client()
        client.put = MagicMock(return_value=_mock_response(403, None))

        with pytest.raises(Unauthorized):
            client.delete_artifact_file("myns/dev", "conda", "numpy", "linux-64/numpy.conda")


class TestResolveNamespaceAndChannel:
    def test_slash_in_name_extracts_both(self):
        from binstar_client.commands._repo_channels import _resolve_namespace_and_channel

        mock_api = MagicMock()
        resolved = _resolve_namespace_and_channel(mock_api, "myorg/dev")
        assert resolved.namespace == "myorg"
        assert resolved.channel_name == "dev"
        mock_api.list_my_channels.assert_not_called()

    def test_explicit_namespace_flag(self):
        from binstar_client.commands._repo_channels import _resolve_namespace_and_channel

        mock_api = MagicMock()
        resolved = _resolve_namespace_and_channel(mock_api, "dev", namespace="myorg")
        assert resolved.namespace == "myorg"
        assert resolved.channel_name == "dev"
        mock_api.list_my_channels.assert_not_called()

    def test_ambiguous_slash_and_flag_exits(self):
        from binstar_client.commands._repo_channels import _resolve_namespace_and_channel
        import typer

        mock_api = MagicMock()
        with pytest.raises(typer.Exit):
            _resolve_namespace_and_channel(mock_api, "org-a/dev", namespace="org-b")

    def test_single_namespace_auto_resolves(self):
        from binstar_client.commands._repo_channels import _resolve_namespace_and_channel

        mock_api = MagicMock()
        mock_api.list_my_channels.return_value = _namespace_channels("myorg")
        resolved = _resolve_namespace_and_channel(mock_api, "dev")
        assert resolved.namespace == "myorg"
        assert resolved.channel_name == "dev"

    def test_no_namespaces_exits(self):
        from binstar_client.commands._repo_channels import _resolve_namespace_and_channel
        import typer

        mock_api = MagicMock()
        mock_api.list_my_channels.return_value = _namespace_channels()
        with pytest.raises(typer.Exit):
            _resolve_namespace_and_channel(mock_api, "dev")

    def test_multiple_namespaces_prompts(self):
        from binstar_client.commands._repo_channels import _resolve_namespace_and_channel

        mock_api = MagicMock()
        mock_api.list_my_channels.return_value = _namespace_channels("org-a", "org-b")

        with patch("binstar_client.repocore.resolve.select_from_list", return_value="org-b"):
            resolved = _resolve_namespace_and_channel(mock_api, "dev")

        assert resolved.namespace == "org-b"
        assert resolved.channel_name == "dev"

    def test_namespaces_sourced_from_readable_channels(self):
        """Namespaces come from GET /channels (own + shared), not org memberships."""
        from binstar_client.commands._repo_channels import _resolve_namespace_and_channel

        mock_api = MagicMock()
        # A channel shared from an org the user is not a member of is still offered.
        mock_api.list_my_channels.return_value = _namespace_channels("shared-org")

        resolved = _resolve_namespace_and_channel(mock_api, "dev")

        assert resolved.namespace == "shared-org"
        assert resolved.channel_name == "dev"
        # Resolution uses the readable-channels listing (which includes subchannels
        # so an existing channel by that name can be matched directly), and never
        # the org-membership endpoint.
        assert mock_api.list_my_channels.call_args.kwargs["include_subchannels"] is True
        mock_api.list_user_organizations.assert_not_called()

    def test_namespaces_paged_and_deduped(self):
        """Namespace resolution pages GET /channels and drops duplicate namespaces."""
        from binstar_client.commands._repo_channels import _resolve_namespace_and_channel

        mock_api = MagicMock()
        page1 = ([Channel(name=f"ns{i}", privacy="private") for i in range(100)], 150, None)
        # Second page repeats ns0 (dedup) and adds ns100 (the sole *new* namespace).
        page2 = ([Channel(name="ns0", privacy="private"), Channel(name="ns100", privacy="private")], 150, None)
        mock_api.list_my_channels.side_effect = [page1, page2]

        with patch("binstar_client.repocore.resolve.select_from_list", return_value="ns100") as sel:
            resolved = _resolve_namespace_and_channel(mock_api, "dev")

        assert resolved.namespace == "ns100"
        # Two pages fetched; the picker saw 101 distinct namespaces (ns0..ns100, no dup).
        assert mock_api.list_my_channels.call_count == 2
        assert len(sel.call_args[0][1]) == 101

    def test_existing_subchannel_resolves_directly(self):
        """A bare name matching exactly one readable subchannel resolves with no prompt.

        Even when several namespaces exist, ``imhungry`` living only under ``dude``
        is unambiguous → ``dude/imhungry`` directly.
        """
        from binstar_client.commands._repo_channels import _resolve_namespace_and_channel

        mock_api = MagicMock()
        mock_api.list_my_channels.return_value = _readable_channels(
            ("dude", None),
            ("fluffybunnies", None),
            ("imhungry", "dude"),
        )

        with patch("binstar_client.repocore.resolve.select_from_list") as sel:
            resolved = _resolve_namespace_and_channel(mock_api, "imhungry")

        assert resolved.namespace == "dude"
        assert resolved.channel_name == "imhungry"
        sel.assert_not_called()

    def test_ambiguous_subchannel_prompts_full_paths(self):
        """The same channel name under multiple namespaces prompts among full paths."""
        from binstar_client.commands._repo_channels import _resolve_namespace_and_channel

        mock_api = MagicMock()
        mock_api.list_my_channels.return_value = _readable_channels(
            ("dude", None),
            ("fluffybunnies", None),
            ("imhungry", "dude"),
            ("imhungry", "fluffybunnies"),
        )

        with patch(
            "binstar_client.repocore.resolve.select_from_list",
            return_value="fluffybunnies/imhungry",
        ) as sel:
            resolved = _resolve_namespace_and_channel(mock_api, "imhungry")

        assert resolved.namespace == "fluffybunnies"
        assert resolved.channel_name == "imhungry"
        # The picker is offered the full paths, not the bare namespaces.
        assert set(sel.call_args[0][1]) == {"dude/imhungry", "fluffybunnies/imhungry"}

    def test_unknown_name_falls_back_to_namespace_picker(self):
        """A name matching no existing subchannel resolves a namespace (create path)."""
        from binstar_client.commands._repo_channels import _resolve_namespace_and_channel

        mock_api = MagicMock()
        mock_api.list_my_channels.return_value = _readable_channels(
            ("dude", None),
            ("fluffybunnies", None),
            ("imhungry", "dude"),
        )

        with patch(
            "binstar_client.repocore.resolve.select_from_list",
            return_value="fluffybunnies",
        ) as sel:
            resolved = _resolve_namespace_and_channel(mock_api, "brandnew")

        assert resolved.namespace == "fluffybunnies"
        assert resolved.channel_name == "brandnew"
        # No existing channel matched, so the picker offers namespaces to create under.
        assert set(sel.call_args[0][1]) == {"dude", "fluffybunnies"}

    def test_viewer_access_channel_is_not_resolved(self):
        """A read-only ("viewer") shared channel is filtered out of resolution.

        ``imhungry`` exists only as a viewer channel, so the bare name does not
        match a writable subchannel and instead falls through to namespace
        resolution (which offers only the writable namespace ``dude``).
        """
        from binstar_client.commands._repo_channels import _resolve_namespace_and_channel

        mock_api = MagicMock()
        mock_api.list_my_channels.return_value = _channels_with_access(
            ("dude", None, "owner"),
            ("imhungry", "fluffybunnies", "viewer"),
        )

        resolved = _resolve_namespace_and_channel(mock_api, "imhungry")

        # Not resolved to the viewer subchannel; a single writable namespace
        # remains, so "imhungry" resolves as a new channel under "dude".
        assert resolved.namespace == "dude"
        assert resolved.channel_name == "imhungry"

    def test_writable_access_channels_are_resolved(self):
        """Collaborator and owner channels stay resolvable as upload targets."""
        from binstar_client.commands._repo_channels import _resolve_namespace_and_channel

        mock_api = MagicMock()
        mock_api.list_my_channels.return_value = _channels_with_access(
            ("dude", None, "owner"),
            ("imhungry", "dude", "collaborator"),
        )

        with patch("binstar_client.repocore.resolve.select_from_list") as sel:
            resolved = _resolve_namespace_and_channel(mock_api, "imhungry")

        assert resolved.namespace == "dude"
        assert resolved.channel_name == "imhungry"
        sel.assert_not_called()

    def test_viewer_namespace_excluded_from_picker(self):
        """A namespace the caller only views is not offered when creating a channel."""
        from binstar_client.commands._repo_channels import _resolve_namespace_and_channel

        mock_api = MagicMock()
        mock_api.list_my_channels.return_value = _channels_with_access(
            ("owned-ns", None, "owner"),
            ("viewer-ns", None, "viewer"),
        )

        # Only one writable namespace remains, so a brand-new name resolves under
        # it with no prompt — the viewer-only namespace is not a candidate.
        resolved = _resolve_namespace_and_channel(mock_api, "brandnew")

        assert resolved.namespace == "owned-ns"
        assert resolved.channel_name == "brandnew"

    def test_missing_access_is_kept(self):
        """When the server omits ``access`` (SpiceDB off), channels are not filtered."""
        from binstar_client.commands._repo_channels import _resolve_namespace_and_channel

        mock_api = MagicMock()
        mock_api.list_my_channels.return_value = _channels_with_access(
            ("dude", None, None),
            ("imhungry", "dude", None),
        )

        with patch("binstar_client.repocore.resolve.select_from_list") as sel:
            resolved = _resolve_namespace_and_channel(mock_api, "imhungry")

        assert resolved.namespace == "dude"
        assert resolved.channel_name == "imhungry"
        sel.assert_not_called()

    def test_no_namespaces_with_username_confirmed(self):
        from binstar_client.commands._repo_channels import _resolve_no_namespace

        mock_api = MagicMock()
        mock_api.account.get.return_value = {"username": "testuser"}

        with patch("binstar_client.repocore.resolve.typer.confirm", return_value=True):
            resolved = _resolve_no_namespace(mock_api, "dev")

        assert resolved.namespace == "testuser"
        assert resolved.channel_name == "dev"

    def test_no_namespaces_with_username_declined(self):
        from binstar_client.commands._repo_channels import _resolve_no_namespace
        import typer

        mock_api = MagicMock()
        mock_api.account.get.return_value = {"username": "testuser"}

        with patch("binstar_client.repocore.resolve.typer.confirm", return_value=False):
            with pytest.raises(typer.Exit):
                _resolve_no_namespace(mock_api, "dev")

    def test_no_namespaces_no_username(self):
        from binstar_client.commands._repo_channels import _resolve_no_namespace

        mock_api = MagicMock()
        mock_api.account.get.return_value = {}

        resolved = _resolve_no_namespace(mock_api, "dev")

        assert resolved.namespace is None
        assert resolved.channel_name == "dev"

    def test_no_namespaces_api_exception(self):
        from binstar_client.commands._repo_channels import _resolve_no_namespace

        mock_api = MagicMock()
        mock_api.account.get.side_effect = Exception("API Error")

        resolved = _resolve_no_namespace(mock_api, "dev")

        assert resolved.namespace is None
        assert resolved.channel_name == "dev"

    def test_no_namespaces_require_false(self):
        from binstar_client.commands._repo_channels import _resolve_namespace_and_channel

        mock_api = MagicMock()
        mock_api.list_my_channels.return_value = _namespace_channels()
        mock_api.account.get.return_value = {}

        resolved = _resolve_namespace_and_channel(mock_api, "dev", require_namespace=False)

        assert resolved.namespace is None
        assert resolved.channel_name == "dev"


class TestClassifyAndResolve:
    def test_qualified_name_is_repo(self):
        from binstar_client.repocore.resolve import classify_and_resolve

        mock_api = MagicMock()
        resolved = classify_and_resolve(mock_api, "myns/dev", owner_probe=lambda n: True)
        assert resolved.target == "repo"
        assert resolved.namespace == "myns"
        assert resolved.channel_name == "dev"
        # A qualified name is unambiguous: no owner probe needed.

    def test_bare_org_only_routes_to_org(self):
        from binstar_client.repocore.resolve import classify_and_resolve

        mock_api = MagicMock()
        mock_api.list_my_channels.return_value = _namespace_channels("other")
        resolved = classify_and_resolve(mock_api, "user1", owner_probe=lambda n: n == "user1")
        assert resolved.target == "org"
        assert resolved.owner == "user1"

    def test_repo_target_carries_repo_package_types(self):
        from binstar_client.repocore.resolve import REPO_PACKAGE_TYPES, classify_and_resolve

        mock_api = MagicMock()
        resolved = classify_and_resolve(mock_api, "myns/dev", owner_probe=lambda n: False)
        assert resolved.accepted_package_types == REPO_PACKAGE_TYPES
        # "sdist" is a repocore-only type; org-only types are not accepted.
        assert resolved.accepts_package_type("sdist")
        assert not resolved.accepts_package_type("ipynb")

    def test_org_target_carries_org_package_types(self):
        from binstar_client.repocore.resolve import ORG_PACKAGE_TYPES, classify_and_resolve

        mock_api = MagicMock()
        resolved = classify_and_resolve(mock_api, "user1", owner_probe=lambda n: n == "user1")
        assert resolved.accepted_package_types == ORG_PACKAGE_TYPES
        # "ipynb" is an anaconda.org type; the repocore-only "sdist" is not accepted.
        assert resolved.accepts_package_type("ipynb")
        assert not resolved.accepts_package_type("sdist")

    def test_bare_repo_only_resolves_channel_under_namespace(self):
        from binstar_client.repocore.resolve import classify_and_resolve

        mock_api = MagicMock()
        mock_api.list_my_channels.return_value = _namespace_channels("myns")
        # Not a dotorg owner -> stays repo; bare name is a channel under the sole namespace.
        resolved = classify_and_resolve(mock_api, "dev", owner_probe=lambda n: False)
        assert resolved.target == "repo"
        assert resolved.namespace == "myns"
        assert resolved.channel_name == "dev"

    def test_bare_ambiguous_prompts_and_can_pick_org(self):
        from binstar_client.repocore.resolve import classify_and_resolve

        mock_api = MagicMock()
        mock_api.list_my_channels.return_value = _namespace_channels("user1")
        with (
            patch("binstar_client.repocore.resolve.sys.stdin.isatty", return_value=True),
            patch("binstar_client.repocore.resolve.select_from_list", return_value="org"),
        ):
            resolved = classify_and_resolve(mock_api, "user1", owner_probe=lambda n: True)
        assert resolved.target == "org"
        assert resolved.owner == "user1"

    def test_bare_ambiguous_pick_repo_resolves_channel(self):
        from binstar_client.repocore.resolve import classify_and_resolve

        mock_api = MagicMock()
        mock_api.list_my_channels.return_value = _namespace_channels("user1")
        with (
            patch("binstar_client.repocore.resolve.sys.stdin.isatty", return_value=True),
            patch("binstar_client.repocore.resolve.select_from_list", return_value="repo"),
        ):
            resolved = classify_and_resolve(mock_api, "user1", owner_probe=lambda n: True)
        # Picking repo means: treat the bare name as a channel; the sole namespace is user1.
        assert resolved.target == "repo"
        assert resolved.namespace == "user1"
        assert resolved.channel_name == "user1"

    def test_bare_org_owner_colliding_with_subchannel_prompts(self):
        """A bare name that is an org owner *and* an existing subchannel collides.

        Even though it is not a top-level namespace, repocore would resolve it to
        that subchannel directly, so the collision prompt must fire.
        """
        from binstar_client.repocore.resolve import classify_and_resolve

        mock_api = MagicMock()
        mock_api.list_my_channels.return_value = _readable_channels(
            ("dude", None),
            ("imhungry", "dude"),
        )
        with (
            patch("binstar_client.repocore.resolve.sys.stdin.isatty", return_value=True),
            patch("binstar_client.repocore.resolve.select_from_list", return_value="repo"),
        ):
            resolved = classify_and_resolve(mock_api, "imhungry", owner_probe=lambda n: True)
        # Picking repo resolves to the existing subchannel unambiguously.
        assert resolved.target == "repo"
        assert resolved.namespace == "dude"
        assert resolved.channel_name == "imhungry"

    def test_bare_ambiguous_non_tty_errors(self):
        from binstar_client.repocore.resolve import classify_and_resolve

        mock_api = MagicMock()
        mock_api.list_my_channels.return_value = _namespace_channels("user1")
        with patch("binstar_client.repocore.resolve.sys.stdin.isatty", return_value=False):
            with pytest.raises(typer.Exit):
                classify_and_resolve(mock_api, "user1", owner_probe=lambda n: True)


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
        assert "upload" in result.output

    def test_channels_list(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        # The default listing pages the caller's own + shared channels.
        mock_api.list_my_channels.return_value = (
            [
                Channel(name="main", privacy="public"),
                Channel(
                    name="dev",
                    privacy="public",
                    parent="main",
                    artifact_count=10,
                    download_count=5,
                    access="owner",
                ),
            ],
            2,
            None,
        )

        with _patch_repo_api(mock_api):
            result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "main" in result.output
        assert "dev" in result.output
        # The Access column surfaces the caller's access level from /account/channels.
        assert "Access" in result.output
        assert "owner" in result.output
        # Default path hits /account/channels, not the broad /channels listing.
        mock_api.list_my_channels.assert_called()
        mock_api.list_all_channels.assert_not_called()

    def test_channels_list_all_uses_broad_listing(self):
        """`--all` pages GET /channels (every readable channel) instead of the
        account listing."""
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.list_all_channels.return_value = (
            [
                Channel(name="main", privacy="public"),
                Channel(name="public-only", privacy="public"),
            ],
            2,
            None,
        )

        with _patch_repo_api(mock_api):
            result = runner.invoke(app, ["list", "--all"])

        assert result.exit_code == 0
        assert "public-only" in result.output
        # --all uses GET /channels, which doesn't report the caller's access level,
        # so the Access column is dropped entirely rather than shown with dashes
        # (a dash would misleadingly read as "no access").
        assert "Access" not in result.output
        mock_api.list_all_channels.assert_called()
        mock_api.list_my_channels.assert_not_called()

    def test_channels_list_with_namespace_filter(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.list_my_channels.return_value = (
            [
                Channel(name="org-a", privacy="public"),
                Channel(name="org-b", privacy="public"),
                Channel(name="dev", privacy="public", parent="org-a"),
                Channel(name="prod", privacy="public", parent="org-b"),
            ],
            4,
            None,
        )

        with _patch_repo_api(mock_api):
            result = runner.invoke(app, ["list", "--namespace", "org-a"])

        assert result.exit_code == 0
        assert "org-a" in result.output
        assert "org-b" not in result.output

    def test_channels_list_includes_shared_channels(self):
        """A channel shared from a namespace the user doesn't own still appears.

        The flat listing returns the shared subchannel (parent=someorg) without a
        top-level channel of its own; its namespace header is synthesized so the
        shared channel is grouped and shown.
        """
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.list_my_channels.return_value = (
            [
                Channel(name="myorg", privacy="public"),
                Channel(name="dev", privacy="private", parent="myorg"),
                # Shared with the user from an org they don't own (no top-level item).
                Channel(name="staging", privacy="public", parent="someorg"),
            ],
            3,
            None,
        )

        with _patch_repo_api(mock_api):
            result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "myorg" in result.output
        assert "dev" in result.output
        assert "someorg" in result.output
        assert "staging" in result.output

    def test_channels_list_source_repo_skips_org(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.list_my_channels.return_value = ([Channel(name="org-a", privacy="public")], 1, None)

        with (
            _patch_repo_api(mock_api),
            patch("binstar_client.commands._repo_channels.get_server_api") as mock_get_server,
        ):
            result = runner.invoke(app, ["list", "--source", "repo"])

        assert result.exit_code == 0
        assert "org-a" in result.output
        # org path must not be touched when source is repo-only
        mock_get_server.assert_not_called()

    def test_channels_list_source_org_shows_owners_not_labels(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()

        aserver = MagicMock()
        aserver.user.return_value = {"login": "user1"}
        aserver.user_orgs.return_value = [{"login": "org1"}]
        aserver.list_channels.return_value = {"main": {"is_locked": False}, "dev": {"is_locked": True}}

        with (
            _patch_repo_api(mock_api),
            patch("binstar_client.commands._repo_channels.get_server_api", return_value=aserver),
        ):
            result = runner.invoke(app, ["list", "--source", "org"])

        assert result.exit_code == 0
        # Owners are listed...
        assert "user1" in result.output
        assert "org1" in result.output
        # ...but labels are not: `channel list` lists channels, not labels.
        assert "main" not in result.output
        assert "dev" not in result.output
        aserver.list_channels.assert_not_called()
        # repocore namespaces must not be fetched for org-only listing
        mock_api.list_my_channels.assert_not_called()
        mock_api.list_all_channels.assert_not_called()

    def test_channels_list_org_failure_isolated(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.list_my_channels.return_value = ([Channel(name="org-a", privacy="public")], 1, None)

        aserver = MagicMock()
        aserver.user.side_effect = Exception("not logged in")

        with (
            _patch_repo_api(mock_api),
            patch("binstar_client.commands._repo_channels.get_server_api", return_value=aserver),
        ):
            result = runner.invoke(app, ["list", "--source", "all"])

        # repo section still renders; org failure is a dim note, not a crash
        assert result.exit_code == 0
        assert "org-a" in result.output
        assert "unavailable" in result.output

    def test_channels_list_all_suppresses_org_auth_failure(self):
        """Logged into repo but not anaconda.org: `list` (default all) is quiet.

        Most users are logged into only one backend; an auth failure on the other
        under `--source all` is expected, so we don't nag with an 'unavailable'
        note when the source the user *is* logged into worked.
        """
        from binstar_client import errors as dotorg_errors

        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.list_my_channels.return_value = ([Channel(name="org-a", privacy="public")], 1, None)

        aserver = MagicMock()
        aserver.user.side_effect = dotorg_errors.Unauthorized("Authentication token is missing.", 401)

        with (
            _patch_repo_api(mock_api),
            patch("binstar_client.commands._repo_channels.get_server_api", return_value=aserver),
        ):
            result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "org-a" in result.output
        # Not-logged-into-dotorg is silent under the default all-sources listing.
        assert "unavailable" not in result.output

    def test_channels_list_all_suppresses_repo_auth_failure(self):
        """Logged into anaconda.org but not repo: `list` (default all) is quiet."""
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.list_my_channels.side_effect = Unauthorized("Please run `anaconda login`.")

        aserver = MagicMock()
        aserver.user.return_value = {"login": "user1"}
        aserver.user_orgs.return_value = [{"login": "org1"}]

        with (
            _patch_repo_api(mock_api),
            patch("binstar_client.commands._repo_channels.get_server_api", return_value=aserver),
        ):
            result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        # org section rendered; repo auth failure suppressed.
        assert "user1" in result.output
        assert "unavailable" not in result.output

    def test_channels_list_all_reports_repo_non_auth_failure(self):
        """A non-auth repo failure (real outage) still surfaces under all-sources."""
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.list_my_channels.side_effect = RepoCoreError("Service Unavailable")

        aserver = MagicMock()
        aserver.user.return_value = {"login": "user1"}
        aserver.user_orgs.return_value = []

        with (
            _patch_repo_api(mock_api),
            patch("binstar_client.commands._repo_channels.get_server_api", return_value=aserver),
        ):
            result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "unavailable" in result.output

    def test_channels_list_invalid_source(self):
        runner = CliRunner()
        app = _get_channels_app()
        with _patch_repo_api(MagicMock()):
            result = runner.invoke(app, ["list", "--source", "bogus"])
        assert result.exit_code == 1
        assert "must be one of" in result.output

    def test_channels_create_with_slash(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.create_namespace_channel.return_value = (
            ChannelCreationResponse(channel_path="myns/dev", status_code=201),
            None,
        )

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
        mock_api.create_namespace_channel.return_value = (
            ChannelCreationResponse(channel_path="myns/dev", status_code=201),
            None,
        )

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
        mock_api.list_my_channels.return_value = _namespace_channels()
        type(mock_api).account = PropertyMock(return_value={"user": {"username": "testuser"}})
        mock_api.create_namespace_channel.return_value = (
            ChannelCreationResponse(channel_path="testuser/newchannel", status_code=201),
            None,
        )

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
        mock_api.list_my_channels.return_value = _namespace_channels("myorg")
        mock_api.create_namespace_channel.return_value = (
            ChannelCreationResponse(channel_path="myorg/dev", status_code=201),
            None,
        )

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
        mock_api.create_namespace_channel.return_value = (
            ChannelCreationResponse(channel_path="myns/dev", status_code=201),
            None,
        )

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
        mock_api.create_namespace_channel.return_value = (
            ChannelCreationResponse(channel_path="myns/dev", status_code=201),
            None,
        )

        with (
            _patch_repo_api(mock_api),
            patch("binstar_client.commands._repo_channels.select_from_list", return_value="private"),
        ):
            result = runner.invoke(app, ["create", "myns/dev"])

        assert result.exit_code == 0
        mock_api.create_namespace_channel.assert_called_once_with(
            channel_name="dev", namespace="myns", privacy="private"
        )

    def test_channels_create_privacy_flags_mutually_exclusive(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()

        with _patch_repo_api(mock_api):
            result = runner.invoke(app, ["create", "myns/dev", "--private", "--public"])

        assert result.exit_code == 1
        assert "mutually exclusive" in result.output
        mock_api.create_namespace_channel.assert_not_called()

    def test_channels_create_no_namespaces_no_username(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.list_my_channels.return_value = _namespace_channels()
        type(mock_api).account = PropertyMock(side_effect=Exception("No account"))
        mock_api.create_namespace_channel.return_value = (
            ChannelCreationResponse(channel_path="newchannel", status_code=201),
            None,
        )

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
        mock_api.list_my_channels.return_value = _namespace_channels()
        type(mock_api).account = PropertyMock(return_value={"user": {"username": "testuser"}})
        mock_api.create_namespace_channel.return_value = (
            ChannelCreationResponse(channel_path="testuser/newchannel", status_code=201),
            None,
        )

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
        mock_api.list_my_channels.return_value = _namespace_channels("myorg")
        mock_api.remove_channel.return_value = (None, None)

        with _patch_repo_api(mock_api):
            result = runner.invoke(app, ["remove", "dev"])

        assert result.exit_code == 0
        mock_api.remove_channel.assert_called_once_with("myorg/dev")

    def test_channels_remove_with_slash(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.remove_channel.return_value = (None, None)

        with _patch_repo_api(mock_api):
            result = runner.invoke(app, ["remove", "myorg/dev"])

        assert result.exit_code == 0
        mock_api.remove_channel.assert_called_once_with("myorg/dev")

    def test_channels_remove_no_namespace_errors(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.list_my_channels.return_value = _namespace_channels()

        with _patch_repo_api(mock_api):
            result = runner.invoke(app, ["remove", "dev"])

        assert result.exit_code == 1
        assert "No resolvable namespaces" in result.output

    def test_channels_show_with_namespace_flag(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.get_namespace_channel.return_value = (
            Channel(
                name="dev",
                privacy="private",
                description="",
                artifact_count=0,
                download_count=0,
                mirror_count=0,
                channel_count=0,
                indexing_behavior="default",
                created="2025-01-01",
                updated="2025-06-01",
            ),
            None,
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
        mock_api.list_my_channels.return_value = _namespace_channels("myorg")
        # changed => the PUT changed the channel.
        mock_api.update_channel.return_value = (ChannelUpdateResponse(changed=True), None)

        with _patch_repo_api(mock_api):
            result = runner.invoke(app, ["modify", "dev", "--privacy", "private"])

        assert result.exit_code == 0
        assert "Success" in result.output
        mock_api.update_channel.assert_called_once_with("myorg/dev", privacy="private")

    def test_channels_modify_privacy_no_change(self):
        """A 200 (idempotent no-op) should warn instead of reporting success."""
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.list_my_channels.return_value = _namespace_channels("myorg")
        # not changed => the channel already held the requested privacy.
        mock_api.update_channel.return_value = (ChannelUpdateResponse(changed=False), None)

        with _patch_repo_api(mock_api):
            result = runner.invoke(app, ["modify", "dev", "--privacy", "public"])

        assert result.exit_code == 0
        assert "No change" in result.output
        assert "already public" in result.output
        assert "Success" not in result.output
        mock_api.update_channel.assert_called_once_with("myorg/dev", privacy="public")

    def test_channels_modify_indexing_no_change(self):
        """A 200 (idempotent no-op) on indexing_behavior should warn, not succeed."""
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.list_my_channels.return_value = _namespace_channels("myorg")
        mock_api.update_channel.return_value = (ChannelUpdateResponse(changed=False), None)

        with _patch_repo_api(mock_api):
            result = runner.invoke(app, ["modify", "dev", "--indexing-behavior", "default"])

        assert result.exit_code == 0
        assert "No change" in result.output
        assert "Success" not in result.output
        mock_api.update_channel.assert_called_once_with("myorg/dev", indexing_behavior="default")

    def test_channels_modify_no_options(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()

        with _patch_repo_api(mock_api):
            result = runner.invoke(app, ["modify", "test-channel"])

        assert result.exit_code == 1
        assert "At least one option is required" in result.output

    def test_upload_single_file_with_explicit_channel(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.upload_file.return_value = ({"status": "uploaded"}, None)
        type(mock_api).account = PropertyMock(return_value={"default_channel": "main"})
        mock_api.list_my_channels.return_value = _namespace_channels()

        with (
            _patch_repo_api(mock_api),
            patch("binstar_client.commands._repo_channels.os.path.exists", return_value=True),
            patch("binstar_client.commands._repo_channels.os.path.getsize", return_value=100),
            patch("binstar_client.repocore.package_utils._detect_package_type", return_value="conda"),
        ):
            result = runner.invoke(app, ["upload", "--channel", "dev", "test-1.0-py39_0.conda"])

        assert result.exit_code == 0
        assert "Success" in result.output
        mock_api.upload_file.assert_called_once_with("test-1.0-py39_0.conda", "dev", "conda")

    def test_upload_single_file_with_default_channel(self):
        """Test that upload now requires explicit channel specification."""
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_response = _mock_response(200, {"status": "uploaded"})
        mock_api.upload_file.return_value = mock_response

        with (
            _patch_repo_api(mock_api),
            patch("binstar_client.commands._repo_channels.os.path.exists", return_value=True),
            patch("binstar_client.repocore.package_utils._detect_package_type", return_value="conda"),
        ):
            result = runner.invoke(app, ["upload", "test-1.0-py39_0.conda"])

        # Should fail because no channel specified
        assert result.exit_code == 1
        assert "No channel specified" in result.output
        mock_api.upload_file.assert_not_called()

    def test_upload_no_default_channel_exits(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        type(mock_api).account = PropertyMock(return_value={})

        with (
            _patch_repo_api(mock_api),
            patch("binstar_client.commands._repo_channels.os.path.exists", return_value=True),
        ):
            result = runner.invoke(app, ["upload", "test-1.0-py39_0.conda"])

        assert result.exit_code == 1
        assert "No channel specified" in result.output

    def test_channel_upload_bare_name_matching_org_owner_routes_to_dotorg(self):
        """Regression: `channel upload -c NAME` where NAME is also an org owner must
        not silently resolve to NAME/NAME. It routes to anaconda.org instead."""
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.list_my_channels.return_value = _namespace_channels("jnguyenwoohoo")

        with (
            _patch_repo_api(mock_api, owner_exists=True),
            patch("binstar_client.commands._repo_channels.os.path.exists", return_value=True),
            patch("binstar_client.repocore.resolve._prompt_repo_or_org", return_value="org"),
            patch("binstar_client.commands._repo_channels._upload_to_dotorg") as mock_dotorg,
        ):
            result = runner.invoke(app, ["upload", "--channel", "jnguyenwoohoo", "pkg-1.0-0.conda"])

        assert result.exit_code == 0
        # Must NOT attempt a repo upload to jnguyenwoohoo/jnguyenwoohoo.
        mock_api.upload_file.assert_not_called()
        mock_dotorg.assert_called_once()
        args, _ = mock_dotorg.call_args
        assert args[1] == "jnguyenwoohoo"  # owner

    def test_channel_upload_mixed_repo_and_org_with_label(self):
        """A single invocation targeting both a repo channel and an org owner with -l:
        the repo channel uploads (label silently ignored) AND the org owner gets the
        file plus the label. The label must not abort the repo upload."""
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.upload_file.return_value = ({"status": "uploaded"}, None)
        type(mock_api).account = PropertyMock(return_value={"default_channel": "main"})
        # "someowner" is not a repo namespace -> no repo/org collision, no prompt.
        mock_api.list_my_channels.return_value = _namespace_channels("myns")

        with (
            _patch_repo_api(mock_api, owner_exists=True),
            patch("binstar_client.commands._repo_channels.os.path.exists", return_value=True),
            patch("binstar_client.commands._repo_channels.os.path.getsize", return_value=100),
            patch("binstar_client.repocore.package_utils._detect_package_type", return_value="conda"),
            patch("binstar_client.commands._repo_channels._upload_to_dotorg") as mock_dotorg,
        ):
            result = runner.invoke(
                app,
                [
                    "upload",
                    "--channel",
                    "myns/prod",  # qualified -> repo
                    "--channel",
                    "someowner",  # bare, owner_exists=True -> org
                    "--label",
                    "dev",
                    "test-1.0-py39_0.conda",
                ],
            )

        assert result.exit_code == 0
        # Repo upload still happens even though a label was supplied.
        mock_api.upload_file.assert_called_once_with("test-1.0-py39_0.conda", "myns/prod", "conda")
        # Org owner receives the file and the label.
        mock_dotorg.assert_called_once()
        args, _ = mock_dotorg.call_args
        assert args[1] == "someowner"  # owner
        assert args[2] == ["dev"]  # labels

    def test_channel_upload_org_route_honors_package_type(self):
        """`channel upload -c <org-owner> -t conda` must forward the explicit
        package type to the anaconda.org Uploader, not silently auto-detect."""
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.list_my_channels.return_value = _namespace_channels("myns")

        with (
            _patch_repo_api(mock_api, owner_exists=True),
            patch("binstar_client.commands._repo_channels.os.path.exists", return_value=True),
            patch("binstar_client.commands.upload.main") as mock_upload_main,
        ):
            result = runner.invoke(
                app,
                ["upload", "--channel", "someowner", "--package-type", "conda", "pkg-1.0-0.conda"],
            )

        assert result.exit_code == 0
        mock_upload_main.assert_called_once()
        forwarded = mock_upload_main.call_args[0][0]
        # Uploader expects the string value, not the repocore enum object.
        assert forwarded.package_type == "conda"
        assert forwarded.user == "someowner"

    def test_channel_upload_org_route_expands_globs_on_windows(self):
        """On Windows the shell does not expand globs, so the org route must
        expand "*.conda" itself (mirroring the repo path) before uploading."""
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.list_my_channels.return_value = _namespace_channels("myns")

        with (
            _patch_repo_api(mock_api, owner_exists=True),
            patch("binstar_client.commands._repo_channels.os.path.exists", return_value=True),
            patch("binstar_client.repocore.package_utils.os.name", "nt"),
            patch(
                "binstar_client.repocore.package_utils.glob",
                return_value=["a-1.0-0.conda", "b-1.0-0.conda"],
            ),
            patch("binstar_client.commands.upload.main") as mock_upload_main,
        ):
            result = runner.invoke(app, ["upload", "--channel", "someowner", "*.conda"])

        assert result.exit_code == 0
        mock_upload_main.assert_called_once()
        forwarded = mock_upload_main.call_args[0][0]
        # The literal "*.conda" must have been expanded to the matching files.
        assert forwarded.files == [["a-1.0-0.conda"], ["b-1.0-0.conda"]]

    def test_upload_multiple_channels(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.upload_file.return_value = ({"status": "uploaded"}, None)
        type(mock_api).account = PropertyMock(return_value={"default_channel": "main"})
        mock_api.list_my_channels.return_value = _namespace_channels()

        with (
            _patch_repo_api(mock_api),
            patch("binstar_client.commands._repo_channels.os.path.exists", return_value=True),
            patch("binstar_client.commands._repo_channels.os.path.getsize", return_value=100),
            patch("binstar_client.repocore.package_utils._detect_package_type", return_value="conda"),
        ):
            result = runner.invoke(app, ["upload", "--channel", "dev", "--channel", "staging", "test-1.0-py39_0.conda"])

        assert result.exit_code == 0
        assert mock_api.upload_file.call_count == 2
        mock_api.upload_file.assert_any_call("test-1.0-py39_0.conda", "dev", "conda")
        mock_api.upload_file.assert_any_call("test-1.0-py39_0.conda", "staging", "conda")

    def test_upload_explicit_package_type(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.upload_file.return_value = ({"status": "uploaded"}, None)
        type(mock_api).account = PropertyMock(return_value={"default_channel": "main"})
        mock_api.list_my_channels.return_value = _namespace_channels()

        with (
            _patch_repo_api(mock_api),
            patch("binstar_client.commands._repo_channels.os.path.exists", return_value=True),
            patch("binstar_client.commands._repo_channels.os.path.getsize", return_value=100),
        ):
            result = runner.invoke(
                app, ["upload", "--channel", "dev", "--package-type", "pypi", "test-1.0-py3-none-any.whl"]
            )

        assert result.exit_code == 0
        mock_api.upload_file.assert_called_once_with("test-1.0-py3-none-any.whl", "dev", "pypi")

    def test_upload_file_not_found(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.list_my_channels.return_value = _namespace_channels("testorg")

        with (
            _patch_repo_api(mock_api),
            patch("binstar_client.commands._repo_channels.os.path.exists", return_value=False),
            patch("binstar_client.commands._repo_channels.os.path.getsize", return_value=100),
        ):
            result = runner.invoke(app, ["upload", "nonexistent-1.0-py39_0.conda", "--channel", "dev"])

        assert result.exit_code == 0
        assert "Warning" in result.output
        assert "not found" in result.output
        mock_api.upload_file.assert_not_called()

    def test_upload_zero_byte_file(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.list_my_channels.return_value = _namespace_channels("testorg")

        with (
            _patch_repo_api(mock_api),
            patch("binstar_client.commands._repo_channels.os.path.exists", return_value=True),
            patch("binstar_client.commands._repo_channels.os.path.getsize", return_value=0),
        ):
            result = runner.invoke(app, ["upload", "empty-1.0-py39_0.conda", "--channel", "dev"])

        assert result.exit_code == 1
        assert "Error" in result.output
        assert "empty (0 bytes)" in result.output
        mock_api.upload_file.assert_not_called()

    def test_upload_auto_detect_fails_exits(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.list_my_channels.return_value = _namespace_channels("testorg")

        with (
            _patch_repo_api(mock_api),
            patch("binstar_client.commands._repo_channels.os.path.exists", return_value=True),
            patch("binstar_client.commands._repo_channels.os.path.getsize", return_value=100),
            patch("binstar_client.repocore.package_utils._detect_package_type", return_value=None),
        ):
            result = runner.invoke(app, ["upload", "unknown.file", "--channel", "dev"])

        assert result.exit_code == 1
        assert "Could not detect package type" in result.output

    def test_upload_unauthorized(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.list_my_channels.return_value = _namespace_channels("testorg")
        mock_api.upload_file.side_effect = Unauthorized()

        with (
            _patch_repo_api(mock_api),
            patch("binstar_client.commands._repo_channels.os.path.exists", return_value=True),
            patch("binstar_client.commands._repo_channels.os.path.getsize", return_value=100),
            patch("binstar_client.repocore.package_utils._detect_package_type", return_value="conda"),
        ):
            result = runner.invoke(app, ["upload", "test-1.0-py39_0.conda", "--channel", "dev"])

        assert result.exit_code == 1
        assert isinstance(result.exception, Unauthorized)
        assert "does not allow you to perform this operation" in str(result.exception)
        assert "anaconda login" in str(result.exception)

    def test_upload_repocore_error(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.list_my_channels.return_value = _namespace_channels("testorg")
        mock_api.upload_file.side_effect = RepoCoreError("Upload failed")

        with (
            _patch_repo_api(mock_api),
            patch("binstar_client.commands._repo_channels.os.path.exists", return_value=True),
            patch("binstar_client.commands._repo_channels.os.path.getsize", return_value=100),
            patch("binstar_client.repocore.package_utils._detect_package_type", return_value="conda"),
        ):
            result = runner.invoke(app, ["upload", "test-1.0-py39_0.conda", "--channel", "dev"])

        assert result.exit_code == 1
        assert isinstance(result.exception, RepoCoreError)
        assert "Upload failed" in str(result.exception)

        mock_api.upload_file.side_effect = RepoCoreError("Subchannel rhett/subchannel not found")

        with (
            _patch_repo_api(mock_api),
            patch("binstar_client.commands._repo_channels.os.path.exists", return_value=True),
            patch("binstar_client.commands._repo_channels.os.path.getsize", return_value=100),
            patch("binstar_client.repocore.package_utils._detect_package_type", return_value="conda"),
        ):
            result = runner.invoke(app, ["upload", "test-1.0-py39_0.conda", "--channel", "dev"])

        assert result.exit_code == 1
        assert isinstance(result.exception, RepoCoreError)
        assert "Channel rhett/subchannel not found" in str(result.exception)

    def test_upload_401_response(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.list_my_channels.return_value = _namespace_channels("testorg")
        mock_api.upload_file.side_effect = Unauthorized()

        with (
            _patch_repo_api(mock_api),
            patch("binstar_client.commands._repo_channels.os.path.exists", return_value=True),
            patch("binstar_client.commands._repo_channels.os.path.getsize", return_value=100),
            patch("binstar_client.repocore.package_utils._detect_package_type", return_value="conda"),
        ):
            result = runner.invoke(app, ["upload", "test-1.0-py39_0.conda", "--channel", "dev"])

        assert result.exit_code == 1
        assert isinstance(result.exception, Unauthorized)
        assert "does not allow you to perform this operation" in str(result.exception)
        assert "anaconda login" in str(result.exception)

    def test_upload_error_response(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.list_my_channels.return_value = _namespace_channels("testorg")
        mock_api.upload_file.side_effect = RepoCoreError("Internal server error")

        with (
            _patch_repo_api(mock_api),
            patch("binstar_client.commands._repo_channels.os.path.exists", return_value=True),
            patch("binstar_client.commands._repo_channels.os.path.getsize", return_value=100),
            patch("binstar_client.repocore.package_utils._detect_package_type", return_value="conda"),
        ):
            result = runner.invoke(app, ["upload", "test-1.0-py39_0.conda", "--channel", "dev"])

        assert result.exit_code == 1
        assert isinstance(result.exception, RepoCoreError)
        assert "Internal server error" in str(result.exception)

    def test_upload_requires_channel_specified(self):
        """Test that upload requires --channel to be specified."""
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()

        with (
            _patch_repo_api(mock_api),
            patch("binstar_client.commands._repo_channels.os.path.getsize", return_value=100),
        ):
            result = runner.invoke(app, ["upload", "test-1.0-py39_0.conda"])

        assert result.exit_code == 1
        assert "No channel specified" in result.output

    def test_upload_404_with_deprecated_flag_shows_label_hint(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.list_my_channels.return_value = _namespace_channels("testorg")
        mock_api.upload_file.side_effect = RepoCoreError("Channel 'myorg/dev' not found")

        with (
            _patch_repo_api(mock_api),
            patch("binstar_client.commands._repo_channels.os.path.exists", return_value=True),
            patch("binstar_client.commands._repo_channels.os.path.getsize", return_value=100),
            patch("binstar_client.repocore.package_utils._detect_package_type", return_value="conda"),
        ):
            # Simulate the deprecated channel flag by calling from the old upload command
            result = runner.invoke(app, ["upload", "test-1.0-py39_0.conda", "-c", "myorg/dev"])

        assert result.exit_code == 1
        assert isinstance(result.exception, RepoCoreError)
        assert "not found" in str(result.exception).lower()

    def test_share_unshare_option(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.list_my_channels.return_value = _namespace_channels("myorg")
        mock_api.share_channel.return_value = (None, None)

        with _patch_repo_api(mock_api):
            result = runner.invoke(app, ["share", "testuser", "--channel", "myorg/dev", "--unshare"])

        assert result.exit_code == 0
        mock_api.share_channel.assert_called_once_with("myorg", "dev", "testuser", action="unshare", grant="read")

    def test_share_access_defaults_to_viewer(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.list_my_channels.return_value = _namespace_channels("myorg")
        mock_api.share_channel.return_value = (None, None)

        with _patch_repo_api(mock_api):
            result = runner.invoke(app, ["share", "testuser", "--channel", "myorg/dev"])

        assert result.exit_code == 0
        mock_api.share_channel.assert_called_once_with("myorg", "dev", "testuser", action="share", grant="read")

    def test_share_role_is_hidden_alias_for_access(self):
        # --role was the original released flag; it still maps to --access.
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.list_my_channels.return_value = _namespace_channels("myorg")
        mock_api.share_channel.return_value = (None, None)

        with _patch_repo_api(mock_api):
            result = runner.invoke(app, ["share", "testuser", "--channel", "myorg/dev", "--role", "collaborator"])

        assert result.exit_code == 0
        mock_api.share_channel.assert_called_once_with("myorg", "dev", "testuser", action="share", grant="write")

    def test_share_access_wins_over_role(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.list_my_channels.return_value = _namespace_channels("myorg")
        mock_api.share_channel.return_value = (None, None)

        with _patch_repo_api(mock_api):
            result = runner.invoke(
                app,
                ["share", "testuser", "--channel", "myorg/dev", "--access", "viewer", "--role", "collaborator"],
            )

        assert result.exit_code == 0
        mock_api.share_channel.assert_called_once_with("myorg", "dev", "testuser", action="share", grant="read")

    def test_share_single_channel_success(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.list_my_channels.return_value = _namespace_channels("myorg")
        mock_api.share_channel.return_value = (None, None)

        with _patch_repo_api(mock_api):
            result = runner.invoke(app, ["share", "testuser", "--channel", "myorg/dev", "--access", "viewer"])

        assert result.exit_code == 0
        assert "Success" in result.output
        assert "myorg/dev" in result.output
        assert "testuser" in result.output
        mock_api.share_channel.assert_called_once()

    def test_share_multi_channel_success(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.list_my_channels.return_value = _namespace_channels("myorg")
        mock_api.share_channel.return_value = (None, None)

        with _patch_repo_api(mock_api):
            result = runner.invoke(
                app, ["share", "testuser", "--channel", "myorg/dev", "--channel", "myorg/staging", "--access", "viewer"]
            )

        assert result.exit_code == 0
        assert mock_api.share_channel.call_count == 2
        mock_api.share_channel.assert_any_call("myorg", "dev", "testuser", action="share", grant="read")
        mock_api.share_channel.assert_any_call("myorg", "staging", "testuser", action="share", grant="read")

    def test_share_channel_not_namespace_format_prompts_for_namespace_single(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.list_my_channels.return_value = _namespace_channels("org-a", "org-b")
        mock_api.share_channel.return_value = (None, None)

        with (
            _patch_repo_api(mock_api),
            patch("binstar_client.repocore.resolve.select_from_list", return_value="org-a"),
        ):
            result = runner.invoke(app, ["share", "testuser", "--channel", "dev", "--access", "viewer"])

        assert result.exit_code == 0
        mock_api.share_channel.assert_called_once_with("org-a", "dev", "testuser", action="share", grant="read")

    def test_share_channel_not_namespace_format_prompts_for_namespace_multi(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.list_my_channels.return_value = _namespace_channels("org-a", "org-b")
        mock_api.share_channel.return_value = (None, None)

        with (
            _patch_repo_api(mock_api),
            patch(
                "binstar_client.repocore.resolve.select_from_list",
                side_effect=["org-a", "org-b"],
            ),
        ):
            result = runner.invoke(
                app, ["share", "testuser", "--channel", "dev", "--channel", "staging", "--access", "viewer"]
            )

        assert result.exit_code == 0
        assert mock_api.share_channel.call_count == 2
        mock_api.share_channel.assert_any_call("org-a", "dev", "testuser", action="share", grant="read")
        mock_api.share_channel.assert_any_call("org-b", "staging", "testuser", action="share", grant="read")

    def test_share_namespace_option_provides_namespace(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.share_channel.return_value = (None, None)

        with _patch_repo_api(mock_api):
            result = runner.invoke(
                app,
                [
                    "share",
                    "testuser",
                    "--channel",
                    "dev",
                    "--channel",
                    "staging",
                    "--namespace",
                    "myorg",
                    "--access",
                    "viewer",
                ],
            )

        assert result.exit_code == 0
        assert mock_api.share_channel.call_count == 2
        mock_api.share_channel.assert_any_call("myorg", "dev", "testuser", action="share", grant="read")
        mock_api.share_channel.assert_any_call("myorg", "staging", "testuser", action="share", grant="read")
        mock_api.list_my_channels.assert_not_called()

    def test_share_namespace_with_slash_format_throws_ambiguous(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()

        with _patch_repo_api(mock_api):
            result = runner.invoke(
                app, ["share", "testuser", "--channel", "org-a/dev", "--namespace", "org-b", "--access", "viewer"]
            )

        assert result.exit_code == 1
        assert "Ambiguous" in result.output
        mock_api.share_channel.assert_not_called()


class TestRepoCoreShowListingAndRemove:
    def _artifact(self, **kw):
        from binstar_client.repocore import Artifact

        return Artifact(**kw)

    def _file(self, **kw):
        from binstar_client.repocore import ArtifactFile

        return ArtifactFile(**kw)

    def test_show_metadata_only_skips_listing(self):
        """Bare `show` prints channel metadata and does no package paging."""
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.get_namespace_channel.return_value = (Channel(name="dev", privacy="private"), None)

        with _patch_repo_api(mock_api):
            result = runner.invoke(app, ["show", "myns/dev"])

        assert result.exit_code == 0, result.output
        mock_api.get_namespace_channel.assert_called_once_with("myns/dev")
        mock_api.list_artifacts.assert_not_called()

    def test_show_routes_to_dotorg_for_owner(self):
        """A bare name matching an anaconda.org owner delegates to the legacy show."""
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()

        with (
            # owner_exists=True makes the owner probe report an anaconda.org owner,
            # so classify_and_resolve routes the bare name to target="org".
            _patch_repo_api(mock_api, owner_exists=True),
            patch("binstar_client.commands.show.main") as mock_show_main,
        ):
            result = runner.invoke(app, ["show", "someowner"])

        assert result.exit_code == 0, result.output
        # Delegated to dotorg, not the repocore channel metadata call.
        mock_api.get_namespace_channel.assert_not_called()
        mock_show_main.assert_called_once()
        spec = mock_show_main.call_args[0][0].spec
        assert spec.user == "someowner"

    def test_show_dotorg_configures_binstar_console_logging(self):
        """Delegating to legacy show must configure the binstar logger for console.

        legacy ``show.main`` prints its listing via ``logging`` at INFO. Under the
        ``channel`` Typer app nothing configures that logger, so without the fix
        the INFO records are dropped and the command prints nothing. Assert that,
        by the time show.main runs, the ``binstar`` logger is emitting at INFO
        with a console (StreamHandler) attached so its output is not swallowed.
        """
        import logging

        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()

        binstar_logger = logging.getLogger("binstar")
        # Start from the unconfigured state the bug depends on.
        original_handlers = binstar_logger.handlers[:]
        original_level = binstar_logger.level
        for handler in original_handlers:
            binstar_logger.removeHandler(handler)
        binstar_logger.setLevel(logging.NOTSET)

        seen = {}

        def _fake_show_main(args):
            show_logger = logging.getLogger("binstar.show")
            seen["effective_level"] = show_logger.getEffectiveLevel()
            seen["has_stream_handler"] = any(isinstance(h, logging.StreamHandler) for h in binstar_logger.handlers)

        try:
            with (
                _patch_repo_api(mock_api, owner_exists=True),
                patch("binstar_client.commands.show.main", side_effect=_fake_show_main),
            ):
                result = runner.invoke(app, ["show", "someowner"])
        finally:
            for handler in binstar_logger.handlers[:]:
                binstar_logger.removeHandler(handler)
            for handler in original_handlers:
                binstar_logger.addHandler(handler)
            binstar_logger.setLevel(original_level)

        assert result.exit_code == 0, result.output
        # INFO records from show.main will not be dropped, and go to a console.
        assert seen["effective_level"] <= logging.INFO
        assert seen["has_stream_handler"] is True

    def test_show_packages_summary(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.get_namespace_channel.return_value = (Channel(name="dev", privacy="private"), None)
        mock_api.list_artifacts.return_value = (
            [self._artifact(name="numpy", family="conda", file_count=3, available_versions=["1.0", "2.0"])],
            1,
        )

        with _patch_repo_api(mock_api):
            result = runner.invoke(app, ["show", "myns/dev", "--packages"])

        assert result.exit_code == 0, result.output
        assert "numpy" in result.output
        mock_api.list_artifacts.assert_called_with("myns/dev", offset=0, limit=100)

    def test_show_files_shows_filenames(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.get_namespace_channel.return_value = (Channel(name="dev", privacy="private"), None)
        mock_api.list_artifacts.return_value = ([self._artifact(name="numpy", family="conda")], 1)
        mock_api.list_artifact_files.return_value = (
            [self._file(ckey="linux-64/numpy-2.2.5-py313.conda", name="numpy", family="conda", size=1048576)],
            1,
        )

        with _patch_repo_api(mock_api):
            result = runner.invoke(app, ["show", "myns/dev", "--files"])

        assert result.exit_code == 0, result.output
        assert "numpy-2.2.5-py313.conda" in result.output

    def test_show_packages_and_files_are_mutually_exclusive(self):
        """Passing both -p and --files is a user error, not a silent files-wins."""
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()

        with _patch_repo_api(mock_api):
            result = runner.invoke(app, ["show", "myns/dev", "-p", "--files"])

        assert result.exit_code == 1
        assert "mutually exclusive" in result.output
        # Rejected before any channel/listing work.
        mock_api.get_namespace_channel.assert_not_called()
        mock_api.list_artifacts.assert_not_called()

    def test_show_empty_channel_listing(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.get_namespace_channel.return_value = (Channel(name="dev", privacy="private"), None)
        mock_api.list_artifacts.return_value = ([], 0)

        with _patch_repo_api(mock_api):
            result = runner.invoke(app, ["show", "myns/dev", "--packages"])

        assert result.exit_code == 0, result.output
        assert "No packages found" in result.output

    def test_remove_package_success(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.list_artifacts.return_value = ([self._artifact(name="numpy", family="conda")], 1)
        mock_api.list_artifact_files.return_value = (
            [self._file(ckey="linux-64/numpy-2.2.5-py313.conda", name="numpy", family="conda")],
            1,
        )

        with _patch_repo_api(mock_api):
            result = runner.invoke(app, ["remove-package", "numpy-2.2.5-py313.conda", "-c", "myns/dev", "--force"])

        assert result.exit_code == 0, result.output
        mock_api.delete_artifact_file.assert_called_once_with(
            "myns/dev", "conda", "numpy", "linux-64/numpy-2.2.5-py313.conda"
        )
        assert "Success" in result.output

    def test_remove_package_prompts_without_force(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.list_artifacts.return_value = ([self._artifact(name="numpy", family="conda")], 1)
        mock_api.list_artifact_files.return_value = (
            [self._file(ckey="linux-64/numpy-2.2.5-py313.conda", name="numpy", family="conda")],
            1,
        )

        with _patch_repo_api(mock_api):
            # Answer "n" to the confirmation prompt.
            result = runner.invoke(app, ["remove-package", "numpy-2.2.5-py313.conda", "-c", "myns/dev"], input="n\n")

        assert result.exit_code == 0
        mock_api.delete_artifact_file.assert_not_called()

    def test_remove_package_not_found(self):
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.list_artifacts.return_value = ([self._artifact(name="numpy", family="conda")], 1)
        mock_api.list_artifact_files.return_value = (
            [self._file(ckey="linux-64/numpy-2.2.5-py313.conda", name="numpy", family="conda")],
            1,
        )

        with _patch_repo_api(mock_api):
            result = runner.invoke(app, ["remove-package", "does-not-exist.conda", "-c", "myns/dev", "--force"])

        assert result.exit_code == 1
        assert "No file named" in result.output
        mock_api.delete_artifact_file.assert_not_called()

    def test_remove_package_requires_channel(self):
        runner = CliRunner()
        app = _get_channels_app()
        with _patch_repo_api(MagicMock()):
            result = runner.invoke(app, ["remove-package", "foo.conda", "--force"])
        assert result.exit_code == 1
        assert "No channel specified" in result.output

    def test_remove_package_routes_to_dotorg_for_owner(self):
        """A -c value matching an anaconda.org owner proxies to the legacy remove path."""
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()

        with (
            # owner_exists=True makes the owner probe report an anaconda.org owner,
            # so classify_and_resolve routes the bare name to target="org".
            _patch_repo_api(mock_api, owner_exists=True),
            patch("binstar_client.commands.remove.main") as mock_remove_main,
        ):
            result = runner.invoke(
                app,
                ["remove-package", "mypkg/1.0/mypkg-1.0.tar.bz2", "-c", "someowner", "--force"],
            )

        assert result.exit_code == 0, result.output
        # Delegated to dotorg, not the repocore file delete.
        mock_api.delete_artifact_file.assert_not_called()
        mock_remove_main.assert_called_once()
        args = mock_remove_main.call_args[0][0]
        assert args.force is True
        # The owner is prepended to form the full owner/package/version/filename spec.
        spec = args.specs[0]
        assert spec.user == "someowner"
        assert spec.package == "mypkg"
        assert spec.version == "1.0"
        assert spec.basename == "mypkg-1.0.tar.bz2"

    def test_remove_package_owner_prepended_once(self):
        """If the target already starts with the owner, it is not doubled."""
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()

        with (
            _patch_repo_api(mock_api, owner_exists=True),
            patch("binstar_client.commands.remove.main") as mock_remove_main,
        ):
            result = runner.invoke(
                app,
                ["remove-package", "someowner/mypkg/1.0/mypkg-1.0.tar.bz2", "-c", "someowner", "--force"],
            )

        assert result.exit_code == 0, result.output
        spec = mock_remove_main.call_args[0][0].specs[0]
        assert spec.user == "someowner"
        assert spec.package == "mypkg"
        assert spec.version == "1.0"
        assert spec.basename == "mypkg-1.0.tar.bz2"

    def test_show_pages_through_all_artifacts(self):
        """show --packages keeps requesting pages until the reported total is reached."""
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.get_namespace_channel.return_value = (Channel(name="dev", privacy="private"), None)
        # Two full pages of 100 then a short final page; total is 250.
        page1 = ([self._artifact(name=f"pkg{i}", family="conda") for i in range(100)], 250)
        page2 = ([self._artifact(name=f"pkg{i}", family="conda") for i in range(100, 200)], 250)
        page3 = ([self._artifact(name=f"pkg{i}", family="conda") for i in range(200, 250)], 250)
        mock_api.list_artifacts.side_effect = [page1, page2, page3]

        with _patch_repo_api(mock_api):
            result = runner.invoke(app, ["show", "myns/dev", "--packages"])

        assert result.exit_code == 0, result.output
        assert mock_api.list_artifacts.call_count == 3
        offsets = [call.kwargs["offset"] for call in mock_api.list_artifacts.call_args_list]
        assert offsets == [0, 100, 200]

    def test_show_stops_on_short_page_despite_overreported_total(self):
        """A total larger than the data still terminates once a short page arrives."""
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.get_namespace_channel.return_value = (Channel(name="dev", privacy="private"), None)
        # Server over-reports total=999 but only returns a short first page.
        mock_api.list_artifacts.return_value = ([self._artifact(name="numpy", family="conda")], 999)

        with _patch_repo_api(mock_api):
            result = runner.invoke(app, ["show", "myns/dev", "--packages"])

        assert result.exit_code == 0, result.output
        # Short page (1 < _PAGE_SIZE) ends paging; no infinite loop.
        assert mock_api.list_artifacts.call_count == 1

    def test_remove_package_ambiguous_match(self):
        """A filename resolving to more than one file aborts without deleting."""
        runner = CliRunner()
        app = _get_channels_app()
        mock_api = MagicMock()
        mock_api.list_artifacts.return_value = (
            [self._artifact(name="numpy", family="conda"), self._artifact(name="numpy2", family="conda")],
            2,
        )
        # Same bare filename appears under two different packages/subdirs.
        mock_api.list_artifact_files.side_effect = [
            ([self._file(ckey="linux-64/dup.conda", name="numpy", family="conda")], 1),
            ([self._file(ckey="win-64/dup.conda", name="numpy2", family="conda")], 1),
        ]

        with _patch_repo_api(mock_api):
            result = runner.invoke(app, ["remove-package", "dup.conda", "-c", "myns/dev", "--force"])

        assert result.exit_code == 1
        assert "matches more than one file" in result.output
        mock_api.delete_artifact_file.assert_not_called()


class TestPackageUtils:
    def test_windows_glob_on_windows(self):
        from binstar_client.repocore.package_utils import windows_glob

        with patch("binstar_client.repocore.package_utils.os.name", "nt"):
            with patch(
                "binstar_client.repocore.package_utils.glob",
                return_value=["pkg1-1.0-py39_0.conda", "pkg2-2.0-py39_0.conda"],
            ):
                result = windows_glob("*.conda")
                assert result == ["pkg1-1.0-py39_0.conda", "pkg2-2.0-py39_0.conda"]

    def test_windows_glob_on_posix(self):
        from binstar_client.repocore.package_utils import windows_glob

        with patch("binstar_client.repocore.package_utils.os.name", "posix"):
            result = windows_glob("*.conda")
            assert result == ["*.conda"]

    def test_determine_package_type_explicit(self):
        from binstar_client.repocore.package_utils import PackageType, determine_package_type

        result = determine_package_type("test-1.0-py39_0.conda", PackageType.conda)
        assert result == "conda"

    def test_determine_package_type_auto_detect(self):
        from binstar_client.repocore.package_utils import determine_package_type

        with patch("binstar_client.repocore.package_utils._detect_package_type", return_value="pypi"):
            result = determine_package_type("test.whl")
            assert result == "pypi"

    def test_detect_package_type_conda(self):
        from binstar_client.repocore.package_utils import _detect_package_type
        import tempfile
        import tarfile
        import json
        import os

        with tempfile.NamedTemporaryFile(suffix=".tar.bz2", delete=False) as tmp:
            tmp_name = tmp.name
            with tarfile.open(tmp.name, "w:bz2") as tar:
                info_data = json.dumps({"name": "test", "version": "1.0"})
                info = tarfile.TarInfo(name="info/index.json")
                info.size = len(info_data)
                tar.addfile(info, __import__('io').BytesIO(info_data.encode()))

        try:
            result = _detect_package_type(tmp_name)
            assert result == "conda"
        finally:
            os.unlink(tmp_name)

    def test_detect_package_type_pypi_wheel(self):
        from binstar_client.repocore.package_utils import _detect_package_type

        result = _detect_package_type("test-1.0-py3-none-any.whl")
        assert result == "pypi"

    def test_detect_package_type_ipynb(self):
        from binstar_client.repocore.package_utils import _detect_package_type

        result = _detect_package_type("notebook.ipynb")
        assert result == "ipynb"

    def test_detect_package_type_environment(self):
        from binstar_client.repocore.package_utils import _detect_package_type

        result = _detect_package_type("environment.yml")
        assert result == "env"
        result = _detect_package_type("environment.yaml")
        assert result == "env"

    def test_detect_package_type_unknown(self):
        from binstar_client.repocore.package_utils import _detect_package_type

        result = _detect_package_type("unknown.xyz")
        assert result is None

    def test_package_type_enum(self):
        from binstar_client.repocore.package_utils import PackageType

        assert PackageType.conda.value == "conda"
        assert PackageType.pypi.value == "pypi"
        assert PackageType.sdist.value == "sdist"


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
    """Context manager to inject a mock repo_api into the Typer context.

    Also stubs the anaconda.org owner probe used during channel classification.
    By default the probe reports "no such owner" so bare channel names route to
    the repo path; pass ``owner_exists=True`` to simulate an anaconda.org owner.
    """

    def __init__(self, mock_api, owner_exists=False):
        self.mock_api = mock_api
        self.patcher = patch("binstar_client.commands._repo_channels.RepoCoreClient", return_value=mock_api)

        aserver = MagicMock()
        if owner_exists:
            aserver.user.return_value = {"login": "someowner"}
        else:
            from binstar_client import errors

            aserver.user.side_effect = errors.NotFound("no such user")
        self.owner_patcher = patch("binstar_client.commands._repo_channels.get_server_api", return_value=aserver)

    def __enter__(self):
        self.patcher.start()
        self.owner_patcher.start()
        return self.mock_api

    def __exit__(self, *args):
        self.owner_patcher.stop()
        self.patcher.stop()


def test_repo_channels_registers_notice_subcommand():
    channels_app = _get_channels_app()
    notice_group = next((grp for grp in channels_app.registered_groups if grp.name == 'notice'), None)
    assert notice_group is not None
