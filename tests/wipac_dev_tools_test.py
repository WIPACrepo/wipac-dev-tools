"""Test the basic stuff about the package."""

import wipac_dev_tools


def test_available() -> None:
    """Test the wanted modules/sub-modules are available."""
    assert set(dir(wipac_dev_tools)) == {
        "from_environment",
        "from_environment_as_dataclass",
        "SetupShop",
        "logging_tools",
        "strtobool",
        "argparse_tools",
    }
