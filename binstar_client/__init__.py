import logging

from binstar_client._version import __version__
from binstar_client.client import NullAuth, HTTPBearerAuth
from binstar_client.client import Binstar as Binstar
from binstar_client.deprecations import (
    DEPRECATE_IN_1_15_0,
    REMOVE_IN_2_0_0,
    deprecated,
)
from binstar_client.errors import (
    BinstarError,
    Unauthorized,
    Conflict,
    NotFound,
    UserError,
    ServerError,
    ShowHelp,
    NoMetadataError,
    DestinationPathExists,
    PillowNotInstalled,
)
from binstar_client.mixins.channels import ChannelsMixin
from binstar_client.mixins.organizations import OrgMixin
from binstar_client.mixins.package import PackageMixin
from binstar_client.utils import compute_hash, jencode
from binstar_client.utils.http_codes import STATUS_CODES
from binstar_client.utils.multipart_uploader import multipart_files_upload


logger = logging.getLogger('binstar')

# Deprecated re-imports from binstar_client.mixins
deprecated.constant(
    deprecate_in=DEPRECATE_IN_1_15_0,
    remove_in=REMOVE_IN_2_0_0,
    constant="ChannelsMixin",
    value=ChannelsMixin,
    addendum="Use `binstar_client.mixins.channels.ChannelsMixin` instead",
)

deprecated.constant(
    deprecate_in=DEPRECATE_IN_1_15_0,
    remove_in=REMOVE_IN_2_0_0,
    constant="OrgMixin",
    value=OrgMixin,
    addendum="Use `binstar_client.mixins.organizations.OrgMixin` instead",
)

deprecated.constant(
    deprecate_in=DEPRECATE_IN_1_15_0,
    remove_in=REMOVE_IN_2_0_0,
    constant="PackageMixin",
    value=PackageMixin,
    addendum="Use `binstar_client.mixins.package.PackageMixin` instead",
)

# Deprecated re-imports from binstar_client.utils
deprecated.constant(
    deprecate_in=DEPRECATE_IN_1_15_0,
    remove_in=REMOVE_IN_2_0_0,
    constant="compute_hash",
    value=compute_hash,
    addendum="Use `binstar_client.utils.compute_hash` instead",
)
deprecated.constant(
    deprecate_in=DEPRECATE_IN_1_15_0,
    remove_in=REMOVE_IN_2_0_0,
    constant="jencode",
    value=jencode,
    addendum="Use `binstar_client.utils.jencode` instead",
)
deprecated.constant(
    deprecate_in=DEPRECATE_IN_1_15_0,
    remove_in=REMOVE_IN_2_0_0,
    constant="multipart_files_upload",
    value=multipart_files_upload,
    addendum="Use `binstar_client.utils.multipart_files_upload` instead",
)
deprecated.constant(
    deprecate_in=DEPRECATE_IN_1_15_0,
    remove_in=REMOVE_IN_2_0_0,
    constant="STATUS_CODES",
    value=STATUS_CODES,
    addendum="Use `binstar_client.utils.http_codes.STATUS_CODES` instead",
)

# Deprecated re-imports from binstar_client.client
deprecated.constant(
    deprecate_in=DEPRECATE_IN_1_15_0,
    remove_in=REMOVE_IN_2_0_0,
    constant="NullAuth",
    value=NullAuth,
    addendum="Use `binstar_client.client.NullAuth` instead",
)

deprecated.constant(
    deprecate_in=DEPRECATE_IN_1_15_0,
    remove_in=REMOVE_IN_2_0_0,
    constant="HTTPBearerAuth",
    value=HTTPBearerAuth,
    addendum="Use `binstar_client.client.HTTPBearerAuth` instead",
)

# Deprecated re-imports from binstar_client.errors
from binstar_client import errors  # noqa: E402

for name in [
    "BinstarError",
    "Unauthorized",
    "Conflict",
    "NotFound",
    "UserError",
    "ServerError",
    "ShowHelp",
    "NoMetadataError",
    "DestinationPathExists",
    "PillowNotInstalled",
]:
    deprecated.constant(
        deprecate_in=DEPRECATE_IN_1_15_0,
        remove_in=REMOVE_IN_2_0_0,
        constant=name,
        value=getattr(errors, name),
        addendum=f"Use `binstar_client.errors.{name}` instead",
    )
del errors

# Prevent export of these into the global symbols
del DEPRECATE_IN_1_15_0, REMOVE_IN_2_0_0, deprecated
