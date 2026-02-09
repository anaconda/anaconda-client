import logging

from ._version import __version__

# For backwards compatibility
from .errors import *
from .mixins.channels import ChannelsMixin
from .mixins.organizations import OrgMixin
from .mixins.package import PackageMixin
from .utils import compute_hash, jencode
from .utils.http_codes import STATUS_CODES
from .utils.multipart_uploader import multipart_files_upload

from binstar_client.client import NullAuth, HTTPBearerAuth
from binstar_client.client import Binstar as Binstar
from binstar_client.deprecations import DEPRECATE_IN_1_15_0, REMOVE_IN_2_0_0, deprecated


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

del DEPRECATE_IN_1_15_0, REMOVE_IN_2_0_0, deprecated
