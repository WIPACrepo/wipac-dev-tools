"""Test strtobool.py."""


from random import choice

import pytest
from wipac_dev_tools import strtobool


def random_case(string: str) -> str:
    """Randomly capitalize string."""
    return "".join(choice((str.upper, str.lower))(c) for c in string)


def test_true() -> None:
    """Test True cases"""
    strings = ["y", "yes", "t", "true", "on", "1"]
    strings.extend([s.upper() for s in strings])
    strings.extend([random_case(s) for s in strings])  # yes, this doubles everything

    for string in strings:
        val = strtobool(string)
        assert isinstance(val, bool)
        assert val


def test_false() -> None:
    """Test False cases."""
    strings = ["n", "no", "f", "false", "off", "0"]
    strings.extend([s.upper() for s in strings])
    strings.extend([random_case(s) for s in strings])  # yes, this doubles everything

    for string in strings:
        val = strtobool(string)
        assert isinstance(val, bool)
        assert not val


def test_value_error() -> None:
    """Test error cases"""
    strings = ["nah", "yup", "", "hmm", "maybe", "offf", "123"]
    strings.extend([s.upper() for s in strings])
    strings.extend([random_case(s) for s in strings])  # yes, this doubles everything

    for string in strings:
        with pytest.raises(ValueError, match=rf"Invalid truth value: {string}"):
            strtobool(string)
