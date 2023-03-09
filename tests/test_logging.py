"""Test logging tools."""

import dataclasses as dc
import logging
import random
import uuid
from itertools import chain
from typing import Any

import pytest
from wipac_dev_tools import logging_tools

# pylint:disable=missing-class-docstring,disallowed-name,invalid-name


@pytest.fixture()
def logger_name() -> str:
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
@pytest.mark.parametrize("third_party_level", LEVELS)
@pytest.mark.parametrize("set_level", LEVEL_OF_A_DIFFERENT_CAPITALIZATION)
def test_00(
    set_level: logging_tools.LoggerLevel,
    third_party_level: logging_tools.LoggerLevel,
    log_level: logging_tools.LoggerLevel,
    caplog: Any,
    logger_name: str,
) -> None:
    """Test `set_level()` with multiple level cases (upper, lower,
    crazycase)."""
    present_third_party_name = f"third-party-{logger_name}"
    logging.getLogger(present_third_party_name)  # this creates the logger
    #
    future_third_party_name = f"future-third-party-{logger_name}"

    logging_tools.set_level(
        set_level,
        first_party_loggers=logger_name,
        third_party_level=third_party_level,
        use_coloredlogs=False,
        future_third_parties=future_third_party_name,
    )

    message = f"this is a test! ({(uuid.uuid4().hex)[:4]})"

    with caplog.at_level(logging.DEBUG):  # allow capturing everything that is logged
        logfn = logging_tools.get_logger_fn(logger_name, log_level)
        logfn(message)

        present_third_party_msg = (
            f"here's a third party logger ({(uuid.uuid4().hex)[:4]})"
        )
        logging.getLogger(present_third_party_name).info(present_third_party_msg)
        #
        future_third_party_msg = f"FUTURE 3RD PARTY ({(uuid.uuid4().hex)[:4]})"
        logging.getLogger(future_third_party_name).warning(future_third_party_msg)

    found_log_record = False
    found_present_third_party = False
    found_future_third_party = False
    for record in caplog.records:
        if record.name == "root":  # this is other logging stuff
            continue
        elif record.name == present_third_party_name:
            assert record.levelname == "INFO"
            assert record.msg == present_third_party_msg
            found_present_third_party = True
        elif record.name == future_third_party_name:
            assert record.levelname == "WARNING"
            assert record.msg == future_third_party_msg
            found_future_third_party = True
        else:
            assert message in record.getMessage()
            assert record.levelname == log_level.upper()
            assert record.msg == message
            assert record.name == logger_name
            found_log_record = True
        # NOTE - there may be other leftover log messages in the stream

    caplog.clear()

    # first party
    if LEVELS.index(set_level.upper()) <= LEVELS.index(log_level.upper()):
        assert found_log_record
    else:
        assert not found_log_record

    # current third party
    if LEVELS.index(third_party_level.upper()) <= LEVELS.index("INFO"):
        assert found_present_third_party
    else:
        assert not found_present_third_party

    # future third party
    if LEVELS.index(third_party_level.upper()) <= LEVELS.index("WARNING"):
        assert found_future_third_party
    else:
        assert not found_future_third_party


def test_10__log_dataclass(caplog: Any) -> None:
    """Test `set_level()` with multiple level cases (upper, lower."""
    senstives = ["my_token", "AUTHOR", "secretive_number", "YouShallNotPass"]

    @dc.dataclass(frozen=True)
    class Config:
        # sensitives
        my_token: str
        AUTHOR: str
        secretive_number: str
        YouShallNotPass: str
        # others
        foo: str
        BAR: str
        Baz: str

    # give every arg the same value to keep testing logic easy
    value = "1a2b3c4d5e6f"
    dclass = Config(
        my_token=value,
        AUTHOR=value,
        secretive_number=value,
        YouShallNotPass=value,
        foo=value,
        BAR=value,
        Baz=value,
    )
    prefix = "blah"
    level = "INFO"
    logger = "my-logger"

    with caplog.at_level(logging.DEBUG):  # allow capturing everything that is logged
        logging_tools.log_dataclass(
            dclass,
            logger=logger,
            level=level,  # type: ignore[arg-type]
            prefix=prefix,
            obfuscate_sensitive_substrings=True,
        )

    # assert
    checked = []
    for record in caplog.records:
        print(record)
        for field in dc.fields(dclass):
            if field.name in record.msg:
                checked.append(field.name)
                # check basic things
                assert record.name == logger
                assert record.levelname == level
                assert record.msg.startswith(prefix + " ")
                # check obfuscations
                if field.name in senstives:
                    assert "***" in record.msg and value not in record.msg
                else:
                    assert "***" not in record.msg and value in record.msg
    # was everything logged?
    assert sorted(checked) == sorted(f.name for f in dc.fields(dclass))

    caplog.clear()
