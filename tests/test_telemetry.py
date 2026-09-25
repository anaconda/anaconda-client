"""Tests for telemetry models and functions."""

from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from binstar_client.repocore.models import ActiveSubscription, Namespace
from binstar_client.repocore.telemetry import (
    Attributes,
    ChannelEvents,
    UpgradeEvents,
    UploadEvents,
    _extract_namespace,
)
from binstar_client.repocore.telemetry_models import (
    ChannelAccessedEvent,
    ChannelCreatedEvent,
    ChannelCreatedExistsEvent,
    ChannelLimitReachedEvent,
    ChannelModifiedEvent,
    ChannelRemovedEvent,
    MemberInvitedEvent,
    MemberRemovedEvent,
    PackageUploadedEvent,
    TelemetryEvent,
    UpgradePromptConvertedEvent,
    UpgradePromptDismissedEvent,
    UpgradePromptImpressedEvent,
)


class TestPydanticTelemetryModels:
    def test_channel_created_event_model(self):
        event = ChannelCreatedEvent(channel_path="myorg/dev", privacy="private")
        assert event.event_name == "channel.created"
        assert event.errorable is True
        assert event.channel_path == "myorg/dev"
        assert event.privacy == "private"
        assert isinstance(event, TelemetryEvent)

    def test_channel_created_exists_event_model(self):
        event = ChannelCreatedExistsEvent(channel_path="myorg/dev", privacy="public")
        assert event.event_name == "channel.created_exists"
        assert event.errorable is False

    def test_channel_accessed_event_model(self):
        event = ChannelAccessedEvent(channel_path="myorg/prod", action="list")
        assert event.event_name == "channel.accessed"
        assert event.channel_path == "myorg/prod"
        assert event.action == "list"

    def test_channel_limit_reached_event_model(self):
        event = ChannelLimitReachedEvent(channel_path="myorg/dev", action="create", limit=5)
        assert event.event_name == "channel.limit_reached"
        assert event.channel_path == "myorg/dev"
        assert event.action == "create"
        assert event.limit == 5

    def test_channel_removed_event_model(self):
        event = ChannelRemovedEvent(channel_path="myorg/staging")
        assert event.event_name == "channel.removed"

    def test_channel_modified_event_model(self):
        event = ChannelModifiedEvent(channel_path="myorg/dev", privacy="private", indexing_behavior="frozen")
        assert event.event_name == "channel.modified"
        assert event.channel_path == "myorg/dev"
        assert event.privacy == "private"
        assert event.indexing_behavior == "frozen"

    def test_upgrade_events_models(self):
        impressed = UpgradePromptImpressedEvent()
        converted = UpgradePromptConvertedEvent()
        dismissed = UpgradePromptDismissedEvent()
        assert impressed.event_name == "upgrade_prompt.impressed"
        assert converted.event_name == "upgrade_prompt.converted"
        assert dismissed.event_name == "upgrade_prompt.dismissed"

    def test_package_uploaded_event_model(self):
        event = PackageUploadedEvent(channel="myorg/dev", package_type="conda", package_name="test-pkg")
        assert event.event_name == "package.uploaded"
        assert event.channel == "myorg/dev"
        assert event.package_type == "conda"
        assert event.package_name == "test-pkg"

    def test_member_invited_event_model(self):
        event = MemberInvitedEvent(channel_path="myorg/dev", user="testuser", role="viewer")
        assert event.event_name == "member.invited"
        assert event.channel_path == "myorg/dev"
        assert event.user == "testuser"
        assert event.role == "viewer"

    def test_member_removed_event_model(self):
        event = MemberRemovedEvent(channel_path="myorg/dev", user="testuser")
        assert event.event_name == "member.removed"
        assert event.channel_path == "myorg/dev"


class TestAttributes:
    def test_attributes_with_valid_account(self):
        mock_client = MagicMock()
        mock_client.account = {
            "user": {"id": "user123", "email": "test@example.com"},
            "subscriptions": [{"org_id": "org1", "product_code": "pro"}, {"org_id": "org2", "product_code": "team"}],
        }

        attrs = Attributes(mock_client)
        assert attrs.user_id == "user123"
        assert attrs.user_email is not None
        assert len(attrs.user_email) == 64
        # organization.id and account.tier are derived from the channel
        # namespace, not from the account's full subscription list
        assert attrs.organization_id is None
        assert attrs.account_tier is None

    def test_attributes_with_exception(self):
        mock_client = MagicMock()
        type(mock_client).account = PropertyMock(side_effect=Exception("API Error"))

        attrs = Attributes(mock_client)
        assert attrs.user_id is None
        assert attrs.user_email is None
        assert attrs.organization_id is None
        assert attrs.account_tier is None

    def test_set_organization_from_namespace(self):
        mock_client = MagicMock()
        mock_client.account = {"user": {"id": "user123", "email": "test@example.com"}}
        mock_client.get_organization.return_value = Namespace(
            name="myorg",
            id="org1",
            active_subscription=ActiveSubscription(product_code="pro"),
        )

        attrs = Attributes(mock_client)
        attrs.set_organization_from_namespace(mock_client, "myorg")

        mock_client.get_organization.assert_called_once_with("myorg")
        assert attrs.organization_id == "org1"
        assert attrs.account_tier == "pro"

    def test_set_organization_from_namespace_no_subscription(self):
        mock_client = MagicMock()
        mock_client.account = {"user": {"id": "user123", "email": "test@example.com"}}
        mock_client.get_organization.return_value = Namespace(name="myorg", id="org1")

        attrs = Attributes(mock_client)
        attrs.set_organization_from_namespace(mock_client, "myorg")

        assert attrs.organization_id == "org1"
        assert attrs.account_tier is None

    def test_set_organization_from_namespace_no_namespace(self):
        mock_client = MagicMock()
        mock_client.account = {"user": {"id": "user123", "email": "test@example.com"}}

        attrs = Attributes(mock_client)
        attrs.set_organization_from_namespace(mock_client, None)

        mock_client.get_organization.assert_not_called()
        assert attrs.organization_id is None
        assert attrs.account_tier is None

    def test_set_organization_from_namespace_org_not_found(self):
        mock_client = MagicMock()
        mock_client.account = {"user": {"id": "user123", "email": "test@example.com"}}
        mock_client.get_organization.return_value = None

        attrs = Attributes(mock_client)
        attrs.set_organization_from_namespace(mock_client, "myorg")

        assert attrs.organization_id is None
        assert attrs.account_tier is None

    def test_set_organization_from_namespace_request_error(self):
        mock_client = MagicMock()
        mock_client.account = {"user": {"id": "user123", "email": "test@example.com"}}
        mock_client.get_organization.side_effect = Exception("API Error")

        attrs = Attributes(mock_client)
        attrs.set_organization_from_namespace(mock_client, "myorg")

        assert attrs.organization_id is None
        assert attrs.account_tier is None

    def test_attributes_to_dict(self):
        mock_client = MagicMock()
        mock_client.account = {
            "user": {"id": "user123", "email": "test@example.com"},
        }
        mock_client.get_organization.return_value = Namespace(
            name="myorg",
            id="org1",
            active_subscription=ActiveSubscription(product_code="pro"),
        )

        attrs = Attributes(mock_client)
        attrs.set_organization_from_namespace(mock_client, "myorg")
        result = attrs.to_dict()

        assert result["user_id"] == "user123"
        assert result["user_email"] is not None
        # organization.id and account.tier are simple strings, not lists
        assert result["organization.id"] == "org1"
        assert result["account.tier"] == "pro"
        assert "organization.ids" not in result
        assert "account.tiers" not in result


class TestExtractNamespace:
    def test_from_channel_path(self):
        event = ChannelAccessedEvent(channel_path="myorg/dev", action="show")
        assert _extract_namespace(event) == "myorg"

    def test_from_channel_field(self):
        event = PackageUploadedEvent(channel="myorg/dev", package_type="conda", package_name="pkg")
        assert _extract_namespace(event) == "myorg"

    def test_bare_channel_name_has_no_namespace(self):
        event = ChannelAccessedEvent(channel_path="dev", action="show")
        assert _extract_namespace(event) is None

    def test_event_without_channel(self):
        event = UpgradePromptImpressedEvent()
        assert _extract_namespace(event) is None
