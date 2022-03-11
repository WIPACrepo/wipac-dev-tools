"""Init."""

from .enviro_tools import from_environment  # noqa
from .setup_tools import SetupShop  # noqa

__all__ = ["from_environment", "SetupShop"]

# version is a human-readable version number.
__version__ = "1.1.2"

# version_info is a four-tuple for programmatic comparison. The first
# three numbers are the components of the version number. The fourth
# is zero for an official release, positive for a development branch,
# or negative for a release candidate or beta (after the base version
# number has been incremented)
version_info = (
    int(__version__.split(".")[0]),
    int(__version__.split(".")[1]),
    int(__version__.split(".")[2]),
    0,
)
