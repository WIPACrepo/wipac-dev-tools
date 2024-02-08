"""Test the basic stuff about the package."""

import wipac_dev_tools


def test_available() -> None:
    """Test the wanted modules/sub-modules are available."""

    # look at __all__
    all_of_em = {
        "from_environment",
        "from_environment_as_dataclass",
        "SetupShop",
        "logging_tools",
        "strtobool",
        "argparse_tools",
        "data_safety_tools",
    }
    assert set(wipac_dev_tools.__all__) == all_of_em

    # look at dir() -- includes the non-explicitly exported
    availables = set(dir(wipac_dev_tools))
    availables = {a for a in availables if not a.startswith("__")}

    assert availables == all_of_em | {
        "version_info",
        "enviro_tools",
        "setup_tools",
        "semver_parser_tools",
    }
