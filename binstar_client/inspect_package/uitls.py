# The contents of this module have all been moved to binstar_client.inspect_package.utils
from binstar_client.deprecations import DEPRECATE_IN_1_15_0, REMOVE_IN_2_0_0, deprecated

from . import utils

__all__ = []

for name in [
    "extract_first",
    "tarfile_match_and_extract",
    "zipfile_match_and_extract",
    "safe",
    "get_key",
    "pop_key",
]:
    deprecated.constant(
        deprecate_in=DEPRECATE_IN_1_15_0,
        remove_in=REMOVE_IN_2_0_0,
        constant=name,
        value=getattr(utils, name),
        addendum=f"Use `binstar_client.inspect_package.utils.{name}` instead",
    )

del DEPRECATE_IN_1_15_0, REMOVE_IN_2_0_0, deprecated
