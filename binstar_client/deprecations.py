"""Re-usable helpers for deprecating functionality."""

from binstar_client import __version__
from anaconda_cli_base.deprecations import DeprecationHandler


DEPRECATION_MESSAGE_NOTEBOOKS_PROJECTS_ENVIRONMENTS_REMOVED = " ".join(
    [
        "The Projects, Notebooks, and Environments features have been removed.",
        "See our release notes (https://docs.anaconda.com/anacondaorg/release-notes/)",
        "for more information.",
        "If you have any questions, please contact usercare@anaconda.com.",
    ]
)

# Store verrsions for which things are deprecated. This gives us a very
# easy way to find all references, for removal.
# TODO(mattkram): Change to 1.15.0 before merge
DEPRECATE_IN_1_15_0 = "1.14.0"
REMOVE_IN_2_0_0 = "2.0.0"


# Define a deprecation handler specific to anaconda-client/binstar_client
deprecated = DeprecationHandler(__version__)
