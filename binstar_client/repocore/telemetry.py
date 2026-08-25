import hashlib

from anaconda_cli_base.telemetry import log_event

from .telemetry_models import (
    TelemetryEvent,
    ChannelCreatedEvent,
    ChannelCreatedExistsEvent,
    ChannelAccessedEvent,
    ChannelLimitReachedEvent,
    ChannelRemovedEvent,
    ChannelModifiedEvent,
    UpgradePromptImpressedEvent,
    UpgradePromptAcceptedEvent,
    UpgradePromptDismissedEvent,
    PackageUploadedEvent,
    MemberInvitedEvent,
    MemberRemovedEvent,
    CollaboratorLimitReachedEvent,
)


class Attributes:
    """Stores user attributes for telemetry events

    Initialized once with client data and provides a method to export as dict
    """

    def __init__(self, client, namespace: str | None = None):
        """Initialize user attributes from client.

        Args:
            client: RepoCoreClient or any BaseClient instance with account property
            namespace: Optional namespace/org name to set organization context
        """
        self.user_id = None
        self.user_email = None
        self.organization_id = None
        self.account_tier = None

        try:
            account = client.account
        except Exception:
            pass  # nosec B110
        else:
            user = account.get("user", {})
            self.user_id = user.get("id")
            user_email = user.get("email")
            if user_email:
                self.user_email = hashlib.sha256(user_email.encode()).hexdigest()

        if namespace:
            try:
                organizations = client.get_user_organizations()
            except Exception:
                pass  # nosec B110
            else:
                org_lookup = {}
                for org in organizations:
                    org_name = org.get("name")
                    org_id = org.get("id") or ""
                    product_code = (org.get("active_subscription") or {}).get("product_code") or "free_subscription"
                    if org_name:
                        org_lookup[org_name] = (org_id, product_code)

                if namespace in org_lookup:
                    self.organization_id, self.account_tier = org_lookup[namespace]

    def to_dict(self) -> dict:
        """Export user attributes as a dictionary for telemetry.

        Returns:
            Dictionary with user.id, user.email, organization.id, and account.tier
        """
        return {
            "user.id": self.user_id or "",
            "user.email": self.user_email or "",
            "organization.id": self.organization_id or "",
            "account.tier": self.account_tier or "",
        }


def _check_error(event: TelemetryEvent, error: bool) -> None:
    """Append .error suffix to event name if error flag is set and event is errorable."""
    if error and event.errorable and not event.event_name.endswith('.error'):
        event.event_name += '.error'


def _event(event: TelemetryEvent, api, app_name: str | None, namespace: str | None = None, error: bool = False) -> None:
    """Helper to track telemetry events with user attributes."""
    try:
        _check_error(event, error)
        user_attrs = Attributes(api, namespace)
        all_attributes = {**user_attrs.to_dict(), **event.attribute_dump()}
        if app_name is None:
            app_name = ""
        log_event("", event.event_name, app_name, all_attributes)
    except Exception:
        pass  # nosec B110


class ChannelEvents:
    """Channel events"""

    @staticmethod
    def created(api, app_name: str | None, namespace: str | None = None, error: bool = False, **kwargs) -> None:
        """Track channel creation event."""
        event = ChannelCreatedEvent(**kwargs)
        _event(event, api, app_name, namespace, error)

    @staticmethod
    def created_exists(api, app_name: str | None, namespace: str | None = None, error: bool = False, **kwargs) -> None:
        """Track channel creation event when channel already exists."""
        event = ChannelCreatedExistsEvent(**kwargs)
        _event(event, api, app_name, namespace, error)

    @staticmethod
    def accessed(api, app_name: str | None, namespace: str | None = None, error: bool = False, **kwargs) -> None:
        """Track channel access event."""
        event = ChannelAccessedEvent(**kwargs)
        _event(event, api, app_name, namespace, error)

    @staticmethod
    def limit(api, app_name: str | None, namespace: str | None = None, **kwargs) -> None:
        """Track channel limit reached event."""
        event = ChannelLimitReachedEvent(**kwargs)
        _event(event, api, app_name, namespace)

    @staticmethod
    def removed(api, app_name: str | None, namespace: str | None = None, error: bool = False, **kwargs) -> None:
        """Track channel removal event."""
        event = ChannelRemovedEvent(**kwargs)
        _event(event, api, app_name, namespace, error)

    @staticmethod
    def modified(api, app_name: str | None, namespace: str | None = None, error: bool = False, **kwargs) -> None:
        """Track channel modification event."""
        event = ChannelModifiedEvent(**kwargs)
        _event(event, api, app_name, namespace, error)

    @staticmethod
    def share(api, app_name: str | None, namespace: str | None = None, error: bool = False, **kwargs) -> None:
        """Track channel sharing event."""
        event = MemberInvitedEvent(**kwargs)
        _event(event, api, app_name, namespace, error)

    @staticmethod
    def unshare(api, app_name: str | None, namespace: str | None = None, error: bool = False, **kwargs) -> None:
        """Track channel unsharing event."""
        event = MemberRemovedEvent(**kwargs)
        _event(event, api, app_name, namespace, error)

    @staticmethod
    def collaborator_limit(api, app_name: str | None, namespace: str | None = None, **kwargs) -> None:
        """Track collaborator limit reached event."""
        event = CollaboratorLimitReachedEvent(**kwargs)
        _event(event, api, app_name, namespace)


class UpgradeEvents:
    """Upgrade prompt events"""

    @staticmethod
    def impressed(api, app_name: str | None, action: str, namespace: str | None = None) -> None:
        """Track upgrade prompt impression event."""
        event = UpgradePromptImpressedEvent(action=action)
        _event(event, api, app_name, namespace)

    @staticmethod
    def accepted(api, app_name: str | None, action: str, namespace: str | None = None) -> None:
        """Track upgrade prompt acceptance event."""
        event = UpgradePromptAcceptedEvent(action=action)
        _event(event, api, app_name, namespace)

    @staticmethod
    def dismissed(api, app_name: str | None, action: str, namespace: str | None = None) -> None:
        """Track upgrade prompt dismissal event."""
        event = UpgradePromptDismissedEvent(action=action)
        _event(event, api, app_name, namespace)


class UploadEvents:
    """Package upload events"""

    @staticmethod
    def uploaded(api, app_name: str | None, namespace: str | None = None, error: bool = False, **kwargs) -> None:
        """Track package upload event."""
        event = PackageUploadedEvent(**kwargs)
        _event(event, api, app_name, namespace, error)
