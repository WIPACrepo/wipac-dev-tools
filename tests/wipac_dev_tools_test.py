"""Test the basic stuff about the package."""

import wipac_dev_tools


def test_available() -> None:
    """Test the wanted modules/sub-modules are available."""
    availables = set(dir(wipac_dev_tools))
    availables = {a for a in availables if not a.startswith("__")}

    assert availables == {
        "from_environment",
        "from_environment_as_dataclass",
        "SetupShop",
        "logging_tools",
        "strtobool",
        "argparse_tools",
    }