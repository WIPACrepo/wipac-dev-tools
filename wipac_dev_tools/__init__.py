"""Init."""

from . import argparse_tools, data_safety_tools, logging_tools
from .enviro_tools import from_environment, from_environment_as_dataclass  # noqa
from .setup_tools import SetupShop  # noqa
from .strtobool import strtobool

__all__ = [
    "from_environment",
    "from_environment_as_dataclass",
    "SetupShop",
    "logging_tools",
    "strtobool",
    "argparse_tools",
    "data_safety_tools",
]

# version is a human-readable version number.
__version__ = "1.13.0"


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
