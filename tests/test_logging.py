"""Test logging tools."""

import random
import uuid
from itertools import chain
from typing import Any

import pytest
from wipac_dev_tools import logging_tools


def _new_logger_name() -> str:
    return "log" + (uuid.uuid4().hex)[:8]


def crazycase(string: str) -> str:
    """Get the string where each char is either UPPER or lower case with a 50%
    chance."""
    return "".join(
        c.upper() if i % 2 == random.randint(0, 1) else c.lower()
        for i, c in enumerate(string)
    )


LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

# horse of a different color, err...
LEVEL_OF_A_DIFFERENT_CAPITALIZATION = list(
    chain(*[[lvl.upper(), lvl.lower(), crazycase(lvl)] for lvl in LEVELS])
)


@pytest.mark.parametrize("log_level", LEVELS)
@pytest.mark.parametrize("set_level", LEVEL_OF_A_DIFFERENT_CAPITALIZATION)
def test_00(
    set_level: logging_tools.LoggerLevel,
    log_level: logging_tools.LoggerLevel,
    caplog: Any,
) -> None:
    """Test `set_level()` with multiple level cases (upper, lower,
    crazycase)."""
    print(set_level)
    logger_name = _new_logger_name()
    logging_tools.set_level(
        set_level,
        first_party_loggers=logger_name,
        third_party_level="WARNING",
        use_coloredlogs=False,
    )

    message = f"this is a test! ({(uuid.uuid4().hex)[:4]})"

    logfn = logging_tools.get_logger_fn(logger_name, log_level)
    logfn(message)

    found_log_record = False
    for record in caplog.records:
        if record.name == "root":
            continue  # this is other logging stuff
        assert message in record.getMessage()
        assert record.levelname == log_level.upper()
        assert record.msg == message
        assert record.name == logger_name
        found_log_record = True

    if LEVELS.index(set_level) <= LEVELS.index(log_level):
        assert found_log_record
    else:
        assert not found_log_record
