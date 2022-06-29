"""Test logging tools."""

import logging
import random
import uuid
from itertools import chain
from typing import Any

import pytest
from wipac_dev_tools import logging_tools


def _new_logger_name() -> str:
    return "log" + (uuid.uuid4().hex)[:8]


def crazycase(string: str) -> str:
    """Get the string where each char is either UPPER or lower case with a 50% chance."""
    return "".join(
        c.upper() if i % 2 == random.randint(0, 1) else c.lower()
        for i, c in enumerate(string)
    )


# horse of a different color, err...
level_of_a_different_capitalization = list(
    chain(
        *[
            [lvl.upper(), lvl.lower(), crazycase(lvl)]
            for lvl in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        ]
    )
)


@pytest.mark.parametrize("level", level_of_a_different_capitalization)
def test_00(level: str, capsys: Any) -> None:
    """Test `set_level()` with multiple level cases (upper, lower, crazycase)."""
    print(level)
    logger_name = _new_logger_name()
    logging_tools.set_level(
        level,
        first_party_loggers=logging.getLogger(logger_name),
        third_party_level="WARNING",
        use_coloredlogs=False,
    )

    message = f"this is a test! ({(uuid.uuid4().hex)[:4]})"

    logfn = getattr(logging.getLogger(logger_name), level.lower())
    logfn(message)

    stderr = capsys.readouterr()
    assert message in stderr


# def test_00() -> None:
#     """ """
#     pass


# def test_00() -> None:
#     """ """
#     pass


# def test_00() -> None:
#     """ """
#     pass


# def test_00() -> None:
#     """ """
#     pass


# def test_00() -> None:
#     """ """
#     pass


# def test_00() -> None:
#     """ """
#     pass


# def test_00() -> None:
#     """ """
#     pass


# def test_00() -> None:
#     """ """
#     pass


# def test_00() -> None:
#     """ """
#     pass


# def test_00() -> None:
#     """ """
#     pass


# def test_00() -> None:
#     """ """
#     pass
