from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class TelemetryEvent(BaseModel):
    """Base class for all telemetry events."""
    event_name: str
    errorable: bool = Field(default=False, description="Whether this event can be an error event")
    attributes: Dict[str, Any] = Field(default_factory=dict)

    def attribute_dump(self) -> Dict[str, Any]:
        """Export event attributes excluding event_name and errorable."""
        return {k: v for k, v in self.model_dump().items() if k not in ['event_name', 'errorable']}


class ChannelCreatedEvent(TelemetryEvent):
    """Channel creation event."""
    event_name: str = "channel.created"
    errorable: bool = True
    channel_path: str
    privacy: str


class ChannelCreatedExistsEvent(TelemetryEvent):
    """Channel creation event when channel already exists."""
    event_name: str = "channel.created_exists"
    errorable: bool = False
    channel_path: str
    privacy: str


class ChannelAccessedEvent(TelemetryEvent):
    """Channel access event."""
    event_name: str = "channel.accessed"
    errorable: bool = True
    channel_path: str


class ChannelLimitReachedEvent(TelemetryEvent):
    """Channel limit reached event."""
    event_name: str = "channel.limit_reached"
    errorable: bool = False
    channel_path: str


class ChannelRemovedEvent(TelemetryEvent):
    """Channel removal event."""
    event_name: str = "channel.removed"
    errorable: bool = True
    channel_path: str


class UpgradePromptImpressedEvent(TelemetryEvent):
    """Upgrade prompt impression event."""
    event_name: str = "upgrade_prompt.impressed"
    errorable: bool = False


class UpgradePromptConvertedEvent(TelemetryEvent):
    """Upgrade prompt conversion event."""
    event_name: str = "upgrade_prompt.converted"
    errorable: bool = False


class UpgradePromptDismissedEvent(TelemetryEvent):
    """Upgrade prompt dismissal event."""
    event_name: str = "upgrade_prompt.dismissed"
    errorable: bool = False


class PackageUploadedEvent(TelemetryEvent):
    """Package upload event."""
    event_name: str = "package.uploaded"
    errorable: bool = True
    channel: str
    package_type: str
    package_name: str


class MemberInvitedEvent(TelemetryEvent):
    """Channel sharing (member invited) event."""
    event_name: str = "member.invited"
    errorable: bool = True
    channel_path: str
    user: str
    role: str


class MemberRemovedEvent(TelemetryEvent):
    """Channel unsharing (member removed) event."""
    event_name: str = "member.removed"
    errorable: bool = True
    channel_path: str
    user: str
