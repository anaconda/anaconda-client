"""Pydantic models for repocore API responses."""

from typing import FrozenSet, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


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
    channel_count: int = 0
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


class ChannelCreationResponse(BaseModel):
    """Response from creating a namespace channel."""

    channel_path: str
    status_code: int

    @property
    def created(self) -> bool:
        return self.status_code == 201


class ResolvedChannel(BaseModel):
    """Resolved namespace and channel name.

    ``target`` indicates which system the upload should go to:
      * "repo" -> anaconda.com (repocore): use ``namespace``/``channel_name``.
      * "org"  -> anaconda.org: ``owner`` is the user/organization; labels are
        applied by the caller. ``namespace`` is not used for org targets.

    ``accepted_package_types`` is the set of ``--package-type`` values this target
    accepts (as raw strings, e.g. ``"conda"``, ``"sdist"``). anaconda.com and
    anaconda.org have overlapping-but-different type sets — neither is a superset —
    so the resolver stamps the correct set here and callers validate against it
    generically instead of hard-coding per-target enum rules. An empty set means
    "not populated / do not validate here".
    """

    namespace: Optional[str]
    channel_name: str
    target: str = "repo"
    owner: Optional[str] = None
    accepted_package_types: FrozenSet[str] = frozenset()

    @model_validator(mode="after")
    def _require_dotorg_owner(self) -> "ResolvedChannel":
        """A dotorg (``target="org"``) target must carry an owner to upload to."""
        if self.target == "org" and not self.owner:
            raise ValueError('ResolvedChannel with target="org" must have an owner')
        return self

    def accepts_package_type(self, package_type: Optional[str]) -> bool:
        """Return whether ``package_type`` is acceptable for this target.

        ``None`` (autodetect) is always acceptable; validation of a detected type
        happens later at the point of upload. An unpopulated set accepts anything.
        """
        if package_type is None or not self.accepted_package_types:
            return True
        return package_type in self.accepted_package_types
