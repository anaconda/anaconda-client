import hashlib

from anaconda_cli_base.telemetry import count as _base_count

from .telemetry_models import (
    TelemetryEvent,
    ChannelCreatedEvent,
    ChannelCreatedExistsEvent,
    ChannelAccessedEvent,
    ChannelLimitReachedEvent,
    ChannelRemovedEvent,
    ChannelModifiedEvent,
    UpgradePromptImpressedEvent,
    UpgradePromptConvertedEvent,
    UpgradePromptDismissedEvent,
    PackageUploadedEvent,
    MemberInvitedEvent,
    MemberRemovedEvent,
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
        self.user_id = None
        self.user_email = None
        self.organization_ids = []
        self.account_tiers = []

        try:
            account = client.account
        except Exception:
            return

        try:
            user = account.get("user", {})
            self.user_id = user.get("id")
        except Exception:
            pass  # nosec B110

        try:
            user = account.get("user", {})
            user_email = user.get("email")
            if user_email:
                self.user_email = hashlib.sha256(user_email.encode()).hexdigest()
        except Exception:
            pass  # nosec B110

        try:
            subscriptions = account.get("subscriptions", [])
            self.organization_ids = [sub.get("org_id") or "" for sub in subscriptions]
        except Exception:
            pass  # nosec B110

        try:
            subscriptions = account.get("subscriptions", [])
            self.account_tiers = [sub.get("product_code") or "" for sub in subscriptions]
        except Exception:
            pass  # nosec B110

    def to_dict(self) -> dict:
        """Export user attributes as a dictionary for telemetry.

        Returns:
            Dictionary with user_id, user_email, organization.ids, and account.tier
        """
        return {
            "user_id": self.user_id,
            "user_email": self.user_email,
            "organization.ids": self.organization_ids,
            "account.tier": self.account_tiers,
        }


def _check_error(event: TelemetryEvent, error: bool) -> None:
    """Append .error suffix to event name if error flag is set and event is errorable."""
    if error and event.errorable and not event.event_name.endswith('.error'):
        event.event_name += '.error'


def _check_account_attrs(api) -> Attributes:
    """Check and cache account attributes on the api object."""
    if not hasattr(api, 'account_attributes'):
        api.account_attributes = Attributes(api)
    return api.account_attributes


def _count(event: TelemetryEvent, api, app_name: str | None, error: bool = False) -> None:
    """Helper to track telemetry events with user attributes."""
    try:
        _check_error(event, error)
        user_attrs = _check_account_attrs(api)
        all_attributes = {**user_attrs.to_dict(), **event.attribute_dump()}
        if app_name is None:
            app_name = ""
        _base_count(event.event_name, app_name, attributes=all_attributes)
    except Exception:
        pass  # nosec B110


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
