from binstar_client import __version__
from binstar_client.deprecations import DEPRECATE_IN_1_15_0, REMOVE_IN_2_0_0, deprecated

deprecated.constant(
    deprecate_in=DEPRECATE_IN_1_15_0,
    remove_in=REMOVE_IN_2_0_0,
    constant="__version__",
    value=__version__,
    addendum="Use `binstar_client.__version__` instead",
)

del DEPRECATE_IN_1_15_0, REMOVE_IN_2_0_0, deprecated
