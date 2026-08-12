"""Pydantic models for repocore API responses."""

from typing import FrozenSet, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


def _handle_none_as_empty_string(v):
    return v if v is not None else ""


class Namespace(BaseModel):
    """Namespace/organization from the auth API."""

    name: str


class Channel(BaseModel):
    """A repocore channel, as returned by any of the channel endpoints.

    The repo API serializes channels with a single shape (``resources.channels``
    ``dump()``); the various endpoints — the flat ``GET /channels`` listing, a
    parent's ``/subchannels``, and a single ``GET /channels/{name}`` — differ only
    in which of those fields they populate. This model carries the superset with
    permissive defaults, so one class parses every channel response.

    A repocore "namespace" is a top-level channel named after the org; a user's
    actual channel is a subchannel beneath it. So a channel's namespace is its
    ``parent`` (when present); ``name`` alone is the bare channel name. ``path``
    reconstructs the ``namespace/channel`` form used for display.
    """

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
    parent: Optional[str] = None
    owners: list[str] = Field(default_factory=list)
    # The caller's access level on the channel (viewer/collaborator/owner). Only
    # populated by GET /account/channels; the flat GET /channels listing omits it.
    access: Optional[str] = None

    _handle_description = field_validator("description", mode="before")(_handle_none_as_empty_string)

    @field_validator("owners", mode="before")
    @classmethod
    def _filter_none_owners(cls, v):
        if v is None:
            return []
        return [o for o in v if o]

    @property
    def namespace(self) -> Optional[str]:
        """The channel's namespace: its parent top-level channel, if any."""
        return self.parent

    @property
    def path(self) -> str:
        """The ``namespace/channel`` display path (or bare name for a top-level channel)."""
        return f"{self.parent}/{self.name}" if self.parent else self.name


class Artifact(BaseModel):
    """A package in a channel, as returned by ``GET .../artifacts``.

    An "artifact" here is a *package* — the server groups files by
    ``family`` + ``name`` (its common name), so one Artifact spans every
    version and file of that package in the channel. Individual files live one
    level down (see :class:`ArtifactFile`).
    """

    name: str
    family: str = ""
    channel: str = ""
    subchannel: str = ""
    download_count: int = 0
    file_count: int = 0
    cve_count: int = 0
    available_versions: list[str] = Field(default_factory=list)
    updated_at: str = ""

    @field_validator("available_versions", mode="before")
    @classmethod
    def _none_versions_as_empty(cls, v):
        return v or []


class ArtifactFile(BaseModel):
    """A single physical file (route) belonging to an artifact/package.

    Identified by ``ckey``, the file's route path (e.g.
    ``linux-64/numpy-2.2.5-py313h51bfb38_3.conda`` or
    ``simple/six/six-1.12.0-py2.py3-none-any.whl``). The filename a user works
    with is the basename of the ckey.
    """

    ckey: str = ""
    name: str = ""
    family: str = ""
    channel: str = ""
    subchannel: str = ""
    size: int = 0

    @property
    def filename(self) -> str:
        """The bare filename — the last path segment of the ckey."""
        return self.ckey.rsplit("/", 1)[-1] if self.ckey else ""


class ChannelCreationResponse(BaseModel):
    """Response from creating a namespace channel."""

    channel_path: str
    status_code: int
    org_id: Optional[str] = None

    @property
    def created(self) -> bool:
        return self.status_code == 201


class ChannelUpdateResponse(BaseModel):
    """Response from updating a channel. ``changed`` is ``false`` when the channel
    already held every submitted value (a no-op)."""

    changed: bool = False


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
