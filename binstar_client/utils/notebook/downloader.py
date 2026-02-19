from binstar_client.commands.download import Downloader
from binstar_client.deprecations import DEPRECATE_IN_1_15_0, REMOVE_IN_2_0_0, deprecated

deprecated.constant(
    deprecate_in=DEPRECATE_IN_1_15_0,
    remove_in=REMOVE_IN_2_0_0,
    constant="Downloader",
    value=Downloader,
    addendum="Use `binstar_client.commands.dowload.Downloader` instead",
)
