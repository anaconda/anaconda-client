import hashlib


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
    """Channel upgrade events"""

    created = 'channel.created'
    accessed = 'channel.accessed'
    limit = 'channel.limit_reached'
    removed = 'channel.removed'


class UpgradeEvents:
    """Channel upgrade events"""

    impressed = 'upgrade_prompt.impressed'
    converted = 'upgrade_prompt.converted'
    dismissed = 'upgrade_prompt.dismissed'


class UploadEvents:
    """Package upload events"""

    uploaded = 'package.uploaded'


class ShareEvents:
    """Channel sharing events"""

    share = 'member.invited'