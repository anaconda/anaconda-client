"""Pydantic models for repocore API responses."""

from typing import Optional

from pydantic import BaseModel, Field, field_validator


def _handle_none_as_empty_string(v):
    return v if v is not None else ""


class Namespace(BaseModel):
    """Namespace/organization from the auth API."""

    name: str


class Channel(BaseModel):
    """Channel within a parent namespace channel."""

    name: str
    privacy: str
    description: str = ""
    artifact_count: int = 0
    download_count: int = 0

    _handle_description = field_validator("description", mode="before")(_handle_none_as_empty_string)


class NamespaceChannel(BaseModel):
    """Parent namespace channel data from the repo API."""

    name: str
    privacy: str
    description: str = ""
    artifact_count: int = 0
    download_count: int = 0
    mirror_count: int = 0
    subchannel_count: int = 0
    indexing_behavior: str = "default"
    created: str = ""
    updated: str = ""
    owners: list[str] = Field(default_factory=list)

    _handle_description = field_validator("description", mode="before")(_handle_none_as_empty_string)

    @field_validator("owners", mode="before")
    @classmethod
    def _filter_none_owners(cls, v):
        if v is None:
            return []
        return [o for o in v if o]


class ResolvedChannel(BaseModel):
    """Resolved namespace and channel name."""

    namespace: Optional[str]
    channel_name: str
