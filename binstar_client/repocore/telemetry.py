import hashlib

from anaconda_cli_base.telemetry import count as _base_count

from .telemetry_models import (
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


class Attributes:
    """Stores user attributes for telemetry events

    Initialized once with client data and provides a method to export as dict
    """

    def __init__(self, client):
        """Initialize user attributes from client.

        Args:
            client: RepoCoreClient or any BaseClient instance with account property
        """

        self.organization_id = None
        self.account_tier = None

        try:
            account = client.account
            user = account.get("user", {})

            self.user_id = user.get("id")
            user_email = user.get("email")

            if user_email:
                self.user_email = hashlib.sha256(user_email.encode()).hexdigest()
            else:
                self.user_email = None
        except Exception:
            self.user_id = None
            self.user_email = None

    def set_organization_from_namespace(self, api, namespace: str | None) -> None:
        """Resolve the organization for the given channel namespace and set
        organization_id and account_tier from it.

        Only the organization matching the namespace is queried, rather than
        collecting every organization and subscription the user belongs to.
        """
        if not namespace:
            return
        try:
            org = api.get_organization(namespace)
        except Exception:
            return
        if org is None:
            return
        self.organization_id = org.id
        if org.active_subscription is not None:
            self.account_tier = org.active_subscription.product_code

    def to_dict(self) -> dict:
        """Export user attributes as a dictionary for telemetry.

        Returns:
            Dictionary with user_id, user_email, organization.id, and account.tier
        """
        return {
            "user_id": self.user_id,
            "user_email": self.user_email,
            "organization.id": self.organization_id,
            "account.tier": self.account_tier,
        }


def _check_error(event: TelemetryEvent, error: bool) -> None:
    """Append .error suffix to event name if error flag is set and event is errorable."""
    if error and event.errorable:
        event.event_name += '.error'


def _check_account_attrs(api) -> Attributes:
    """Check and cache account attributes on the api object."""
    if not hasattr(api, 'account_attributes'):
        api.account_attributes = Attributes(api)
    return api.account_attributes


def _extract_namespace(event: TelemetryEvent) -> str | None:
    """Extract the channel namespace from an event's channel path, if any.

    Channel paths are qualified as ``namespace/channel``; a bare channel name
    has no namespace (user namespace), which resolves to no organization.
    """
    for field_value in (getattr(event, "channel_path", None), getattr(event, "channel", None)):
        if isinstance(field_value, str) and "/" in field_value:
            return field_value.split("/", 1)[0]
    return None


def _count(event: TelemetryEvent, api, app_name: str | None, error: bool = False) -> None:
    """Helper to track telemetry events with user attributes."""
    _check_error(event, error)
    user_attrs = _check_account_attrs(api)
    user_attrs.set_organization_from_namespace(api, _extract_namespace(event))
    all_attributes = {**user_attrs.to_dict(), **event.attribute_dump()}
    if app_name is None:
        app_name = ""
    _base_count(event.event_name, app_name, attributes=all_attributes)


class ChannelEvents:
    """Channel events"""

    @staticmethod
    def created(api, app_name: str | None, error: bool = False, **kwargs) -> None:
        """Track channel creation event."""
        event = ChannelCreatedEvent(**kwargs)
        _count(event, api, app_name, error)

    @staticmethod
    def created_exists(api, app_name: str | None, error: bool = False, **kwargs) -> None:
        """Track channel creation event when channel already exists."""
        event = ChannelCreatedExistsEvent(**kwargs)
        _count(event, api, app_name, error)

    @staticmethod
    def accessed(api, app_name: str | None, error: bool = False, **kwargs) -> None:
        """Track channel access event."""
        event = ChannelAccessedEvent(**kwargs)
        _count(event, api, app_name, error)

    @staticmethod
    def limit(api, app_name: str | None, **kwargs) -> None:
        """Track channel limit reached event."""
        event = ChannelLimitReachedEvent(**kwargs)
        _count(event, api, app_name)

    @staticmethod
    def removed(api, app_name: str | None, error: bool = False, **kwargs) -> None:
        """Track channel removal event."""
        event = ChannelRemovedEvent(**kwargs)
        _count(event, api, app_name, error)

    @staticmethod
    def modified(api, app_name: str | None, error: bool = False, **kwargs) -> None:
        """Track channel modification event."""
        event = ChannelModifiedEvent(**kwargs)
        _count(event, api, app_name, error)

    @staticmethod
    def share(api, app_name: str | None, error: bool = False, **kwargs) -> None:
        """Track channel sharing event."""
        event = MemberInvitedEvent(**kwargs)
        _count(event, api, app_name, error)

    @staticmethod
    def unshare(api, app_name: str | None, error: bool = False, **kwargs) -> None:
        """Track channel unsharing event."""
        event = MemberRemovedEvent(**kwargs)
        _count(event, api, app_name, error)


class UpgradeEvents:
    """Upgrade prompt events"""

    @staticmethod
    def impressed(api, app_name: str | None) -> None:
        """Track upgrade prompt impression event."""
        event = UpgradePromptImpressedEvent()
        _count(event, api, app_name)

    @staticmethod
    def converted(api, app_name: str | None) -> None:
        """Track upgrade prompt conversion event."""
        event = UpgradePromptConvertedEvent()
        _count(event, api, app_name)

    @staticmethod
    def dismissed(api, app_name: str | None) -> None:
        """Track upgrade prompt dismissal event."""
        event = UpgradePromptDismissedEvent()
        _count(event, api, app_name)


class UploadEvents:
    """Package upload events"""

    @staticmethod
    def uploaded(api, app_name: str | None, error: bool = False, **kwargs) -> None:
        """Track package upload event."""
        event = PackageUploadedEvent(**kwargs)
        _count(event, api, app_name, error)
