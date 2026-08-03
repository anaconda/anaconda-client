import hashlib
from typing import Any, Dict, Optional

from anaconda_cli_base.telemetry import count as _base_count


def _count(event_name: str, api, app_name: str, attributes: Dict[str, Any]) -> None:
    """Helper to track telemetry events with user attributes."""
    user_attrs = Attributes(api)
    all_attributes = {**user_attrs.to_dict(), **attributes}
    _base_count(event_name, app_name, attributes=all_attributes)


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
    def created(api, app_name: str, channel_path: str, privacy: str, error: bool = False, extra_attrs: Optional[Dict[str, Any]] = None) -> None:
        """Track channel creation event."""
        event_name = 'channel.created.error' if error else 'channel.created'
        attributes = {
            "channel_path": channel_path,
            "privacy": privacy,
        }
        if extra_attrs:
            attributes.update(extra_attrs)
        _count(event_name, api, app_name, attributes)

    @staticmethod
    def accessed(api, app_name: str, channel_path: str, error: bool = False, extra_attrs: Optional[Dict[str, Any]] = None) -> None:
        """Track channel access event."""
        event_name = 'channel.accessed.error' if error else 'channel.accessed'
        attributes = {"channel_path": channel_path}
        if extra_attrs:
            attributes.update(extra_attrs)
        _count(event_name, api, app_name, attributes)

    @staticmethod
    def limit(api, app_name: str, channel_path: str, extra_attrs: Optional[Dict[str, Any]] = None) -> None:
        """Track channel limit reached event."""
        attributes = {"channel_path": channel_path}
        if extra_attrs:
            attributes.update(extra_attrs)
        _count('channel.limit_reached', api, app_name, attributes)

    @staticmethod
    def removed(api, app_name: str, channel_path: str, error: bool = False, extra_attrs: Optional[Dict[str, Any]] = None) -> None:
        """Track channel removal event."""
        event_name = 'channel.removed.error' if error else 'channel.removed'
        attributes = {"channel_path": channel_path}
        if extra_attrs:
            attributes.update(extra_attrs)
        _count(event_name, api, app_name, attributes)


class UpgradeEvents:
    """Channel events"""

    @staticmethod
    def impressed(api, app_name: str, extra_attrs: Optional[Dict[str, Any]] = None) -> None:
        """Track upgrade prompt impression event."""
        attributes = extra_attrs or {}
        _count('upgrade_prompt.impressed', api, app_name, attributes)

    @staticmethod
    def converted(api, app_name: str, extra_attrs: Optional[Dict[str, Any]] = None) -> None:
        """Track upgrade prompt conversion event."""
        attributes = extra_attrs or {}
        _count('upgrade_prompt.converted', api, app_name, attributes)

    @staticmethod
    def dismissed(api, app_name: str, extra_attrs: Optional[Dict[str, Any]] = None) -> None:
        """Track upgrade prompt dismissal event."""
        attributes = extra_attrs or {}
        _count('upgrade_prompt.dismissed', api, app_name, attributes)


class UploadEvents:
    """Package upload events"""

    @staticmethod
    def uploaded(api, app_name: str, channel: str, package_type: str, package_name: str, error: bool = False, extra_attrs: Optional[Dict[str, Any]] = None) -> None:
        """Track package upload event."""
        event_name = 'package.uploaded.error' if error else 'package.uploaded'
        attributes = {
            "channel": channel,
            "package_type": package_type,
            "package_name": package_name,
        }
        if extra_attrs:
            attributes.update(extra_attrs)
        _count(event_name, api, app_name, attributes)


class ShareEvents:
    """Channel sharing events"""

    @staticmethod
    def share(api, app_name: str, channel_path: str, shared_with_user: str, grant: str, role: str, error: bool = False, extra_attrs: Optional[Dict[str, Any]] = None) -> None:
        """Track channel sharing event."""
        event_name = 'member.invited.error' if error else 'member.invited'
        attributes = {
            "channel_path": channel_path,
            "shared_with_user": shared_with_user,
            "grant": grant,
            "role": role,
        }
        if extra_attrs:
            attributes.update(extra_attrs)
        _count(event_name, api, app_name, attributes)