import hashlib

from anaconda_cli_base.telemetry import count as _base_count

from .telemetry_models import TelemetryEvent


def _count(event: TelemetryEvent, api, app_name: str) -> None:
    """Helper to track telemetry events with user attributes."""
    user_attrs = Attributes(api)
    all_attributes = {**user_attrs.to_dict(), **event.attribute_dump()}
    _base_count(event.event_name, app_name, attributes=all_attributes)


class Attributes:
    """Stores user attributes for telemetry events.

    Initialized once with client data and provides a method to export as dict.
    """

    def __init__(self, client):
        """Initialize user attributes from client.

        Args:
            client: RepoCoreClient or any BaseClient instance with account property
        """
        self.user_id = None
        self.user_email = None
        self.organization_ids = []
        self.account_tiers = []

        try:
            account = client.account
            user = account.get("user", {})

            self.user_id = user.get("id")
            user_email = user.get("email")

            if user_email:
                salt = "anaconda_client_telemetry"
                self.user_email = hashlib.sha256(f"{user_email}{salt}".encode()).hexdigest()

            # Extract org_id and product_code from subscriptions
            subscriptions = account.get("subscriptions", [])
            self.organization_ids = [sub.get("org_id") for sub in subscriptions if sub.get("org_id") is not None]
            self.account_tiers = [sub.get("product_code") for sub in subscriptions if sub.get("product_code")]
        except Exception:
            pass

    def to_dict(self) -> dict:
        """Export user attributes as a dictionary for telemetry.

        Returns:
            Dictionary with user_id, user_email, organization.id, and account.tier
        """
        return {
            "user_id": self.user_id,
            "user_email": self.user_email,
            "organization.id": self.organization_ids,
            "account.tier": self.account_tiers,
        }


class ChannelEvents:
    """Channel events"""

    @staticmethod
    def created(api, app_name: str, channel_path: str, privacy: str, error: bool = False) -> None:
        """Track channel creation event."""
        from .telemetry_models import ChannelCreatedEvent
        event = ChannelCreatedEvent(channel_path=channel_path, privacy=privacy)
        if error:
            event.event_name += '.error'
        _count(event, api, app_name)

    @staticmethod
    def created_exists(api, app_name: str, channel_path: str, privacy: str, error: bool = False) -> None:
        """Track channel creation event when channel already exists."""
        from .telemetry_models import ChannelCreatedExistsEvent
        event = ChannelCreatedExistsEvent(channel_path=channel_path, privacy=privacy)
        if error:
            event.event_name += '.error'
        _count(event, api, app_name)

    @staticmethod
    def accessed(api, app_name: str, channel_path: str, error: bool = False) -> None:
        """Track channel access event."""
        from .telemetry_models import ChannelAccessedEvent
        event = ChannelAccessedEvent(channel_path=channel_path)
        if error:
            event.event_name += '.error'
        _count(event, api, app_name)

    @staticmethod
    def limit(api, app_name: str, channel_path: str) -> None:
        """Track channel limit reached event."""
        from .telemetry_models import ChannelLimitReachedEvent
        event = ChannelLimitReachedEvent(channel_path=channel_path)
        _count(event, api, app_name)

    @staticmethod
    def removed(api, app_name: str, channel_path: str, error: bool = False) -> None:
        """Track channel removal event."""
        from .telemetry_models import ChannelRemovedEvent
        event = ChannelRemovedEvent(channel_path=channel_path)
        if error:
            event.event_name += '.error'
        _count(event, api, app_name)


class UpgradeEvents:
    """Upgrade prompt events"""

    @staticmethod
    def impressed(api, app_name: str) -> None:
        """Track upgrade prompt impression event."""
        from .telemetry_models import UpgradePromptImpressedEvent
        event = UpgradePromptImpressedEvent()
        _count(event, api, app_name)

    @staticmethod
    def converted(api, app_name: str) -> None:
        """Track upgrade prompt conversion event."""
        from .telemetry_models import UpgradePromptConvertedEvent
        event = UpgradePromptConvertedEvent()
        _count(event, api, app_name)

    @staticmethod
    def dismissed(api, app_name: str) -> None:
        """Track upgrade prompt dismissal event."""
        from .telemetry_models import UpgradePromptDismissedEvent
        event = UpgradePromptDismissedEvent()
        _count(event, api, app_name)


class UploadEvents:
    """Package upload events"""

    @staticmethod
    def uploaded(api, app_name: str, channel: str, package_type: str, package_name: str, error: bool = False) -> None:
        """Track package upload event."""
        from .telemetry_models import PackageUploadedEvent
        event = PackageUploadedEvent(channel=channel, package_type=package_type, package_name=package_name)
        if error:
            event.event_name += '.error'
        _count(event, api, app_name)


class ShareEvents:
    """Channel sharing events"""

    @staticmethod
    def share(api, app_name: str, channel_path: str, user: str, role: str, error: bool = False) -> None:
        """Track channel sharing event."""
        from .telemetry_models import MemberInvitedEvent
        event = MemberInvitedEvent(channel_path=channel_path, user=user, role=role)
        if error:
            event.event_name += '.error'
        _count(event, api, app_name)

    @staticmethod
    def unshare(api, app_name: str, channel_path: str, user: str, error: bool = False) -> None:
        """Track channel unsharing event."""
        from .telemetry_models import MemberRemovedEvent
        event = MemberRemovedEvent(channel_path=channel_path, user=user)
        if error:
            event.event_name += '.error'
        _count(event, api, app_name)