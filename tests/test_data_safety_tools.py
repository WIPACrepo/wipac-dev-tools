"""Tests for data_safety_tools.py."""


from wipac_dev_tools import data_safety_tools


def test_00() -> None:
    """Test with usual values."""
    senstives = ["my_token", "AUTHOR", "secretive_number", "YouShallNotPass"]

    unimportant_value = "12345"

    for name in ["foo", "bar", "baz"] + senstives:
        print(name)
        actual = data_safety_tools.obfuscate_value_if_sensitive(name, unimportant_value)
        print(actual)
        if name in senstives:
            assert actual == "***"
        else:
            assert actual == unimportant_value
