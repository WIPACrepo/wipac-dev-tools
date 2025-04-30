"""Common tools to supplement/assist the standard logging package."""

import argparse
import dataclasses
import logging
from typing import Callable, Dict, List, Optional, TYPE_CHECKING, TypeVar, Union

from typing_extensions import Literal

from .data_safety_tools import obfuscate_value_if_sensitive

# fmt: off
if TYPE_CHECKING:  # _typeshed only exists at runtime
    from _typeshed import DataclassInstance
    DataclassT = TypeVar("DataclassT", bound=DataclassInstance)
else:
    DataclassT = TypeVar("DataclassT")
# fmt: on

T = TypeVar("T")

LogggerObjectOrName = Union[str, logging.Logger]


# ---------------------------------------------------------------------------------------


LoggerLevel = Literal[
    "CRITICAL",
    "ERROR",
    "WARNING",
    "INFO",
    "DEBUG",
    "critical",
    "error",
    "warning",
    "info",
    "debug",
]


# ---------------------------------------------------------------------------------------


def get_logger_fn(
    logger: Union[None, str, logging.Logger], level: LoggerLevel
) -> Callable[[str], None]:
    """Get the logger function from `logger` and `level`."""
    level = level.upper()  # type: ignore[assignment]

    if not logger:
        _logger = logging.getLogger()
    elif isinstance(logger, logging.Logger):
        _logger = logger
    else:
        _logger = logging.getLogger(logger)

    if level not in ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]:
        raise ValueError(f"Invalid logging level: {level}")

    return getattr(_logger, level.lower())  # ..., info, warning, critical, ...


def log_argparse_args(
    args: argparse.Namespace,
    logger: Union[None, str, logging.Logger] = None,
    level: LoggerLevel = "WARNING",
) -> argparse.Namespace:
    """Log the argparse args and their values at the given level.

    Sensitive args (containing specific substrings, case-insensitive)
    have their values obfuscated with '***'

    Return the args (Namespace) unchanged.

    Example:
        2022-05-13 22:37:21 fv-az136-643 my-logs[61] WARNING in_file: in_msg.pkl
        2022-05-13 22:37:21 fv-az136-643 my-logs[61] WARNING out_file: out_msg.pkl
        2022-05-13 22:37:21 fv-az136-643 my-logs[61] WARNING log: DEBUG
        2022-05-13 22:37:21 fv-az136-643 my-logs[61] WARNING log_third_party: WARNING
    """
    logger_fn = get_logger_fn(logger, level)

    for arg, val in vars(args).items():
        logger_fn(f"{arg}: {obfuscate_value_if_sensitive(arg, val)}")

    return args


def log_dataclass(
    dclass: DataclassT,
    logger: LogggerObjectOrName,
    level: LoggerLevel,
    prefix: str = "",
    obfuscate_sensitive_substrings: bool = False,
) -> DataclassT:
    """Log a dataclass instance's fields and members.

    Arguments:
        `obfuscate_sensitive_substrings` -
            Sensitive args (containing specific substrings, case-insensitive)
            have their values obfuscated with '***'
    """
    if not (dataclasses.is_dataclass(dclass) and not isinstance(dclass, type)):
        raise TypeError(f"Expected instantiated dataclass: 'dclass' ({dclass})")

    logger_fn = get_logger_fn(logger, level)

    for field in dataclasses.fields(dclass):
        val = getattr(dclass, field.name)
        if obfuscate_sensitive_substrings:
            val = obfuscate_value_if_sensitive(field.name, val)
        logger_fn(f"{prefix+' 'if prefix else ''}{field.name}: {val}")

    return dclass


def _to_list(pseudo_list: Union[None, T, List[T]]) -> List[T]:
    if not pseudo_list:
        return []
    elif not isinstance(pseudo_list, list):
        return [pseudo_list]
    else:
        return pseudo_list


def _logger_to_name(logger: LogggerObjectOrName) -> str:
    if isinstance(logger, logging.Logger):
        return logger.name
    elif isinstance(logger, str):
        return logger
    else:
        raise TypeError("not Logger object or str")


def _set_and_share(log_name: str, level: LoggerLevel, text: str) -> None:
    logging.getLogger(log_name).setLevel(level)
    logging.getLogger().info(f"{text} Logger: '{log_name}' ({level})")


class WIPACDevToolsFormatter(logging.Formatter):
    """A fairly detailed formatter that is similar to coloredlogs's format."""

    def __init__(self):
        super().__init__(
            "%(asctime)s.%(msecs)03d [%(levelname)8s] %(name)s[%(process)d] %(message)s <%(filename)s:%(lineno)s/%(funcName)s()>",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


def set_level(
    level: LoggerLevel,
    first_party_loggers: Union[
        None, LogggerObjectOrName, List[LogggerObjectOrName]
    ] = None,
    third_party_level: LoggerLevel = "WARNING",
    future_third_parties: Union[None, str, List[str]] = None,
    specialty_loggers: Optional[Dict[LogggerObjectOrName, LoggerLevel]] = None,
    use_coloredlogs: bool = False,
    formatter: Union[WIPACDevToolsFormatter, logging.Formatter, None] = None,
) -> None:
    """Set the level of loggers of various precedence.

    The root logger and first-party logger(s) are set to the same level (`level`).

    Args:
        `level`
            the desired logging level (first-party), case-insensitive
        `first_party_loggers`
            a list (or a single instance) of `logging.Logger` or the loggers' names
        `third_party_level`
            the desired logging level for any other (currently) available loggers, case-insensitive
        `future_third_parties`
            additional third party logger(s) which have not yet been created (at call time)
        `specialty_loggers`
            additional loggers, each paired with a logging level, which are not
            considered first-party nor third-party loggers. **These have the highest precedence**
        `use_coloredlogs`
            *DEPRECATED* -- will use the WIPACDevToolsFormatter formatter
        `formatter`
            a logging.Formatter instance to use for all logging, use `WIPACDevToolsFormatter()`
            for a fairly detailed logger
    """
    if use_coloredlogs:
        logging.getLogger().warning(
            "set_level()'s `use_coloredlogs` is DEPRECATED (use `formatter=WIPACDevToolsFormatter()`). "
            "Proceeding with vanilla 'logging' package with a similar formatter."
        )
        formatter = WIPACDevToolsFormatter()

    return _set_level(
        first_party_level=level.upper(),  # type: ignore
        #
        first_parties=list(
            _logger_to_name(lg)  # type: ignore[arg-type]
            for lg in _to_list(first_party_loggers)
        ),
        #
        third_party_level=third_party_level.upper(),  # type: ignore
        #
        future_third_parties=_to_list(future_third_parties),
        #
        formatter=formatter,
        #
        specialty_loggers=(
            {_logger_to_name(k): v for k, v in specialty_loggers.items()}
            if specialty_loggers
            else {}
        ),
    )


def _set_level(
    first_party_level: LoggerLevel,
    first_parties: List[str],
    third_party_level: LoggerLevel,
    future_third_parties: List[str],
    formatter: Union[WIPACDevToolsFormatter, logging.Formatter, None],
    specialty_loggers: Dict[str, LoggerLevel],
) -> None:
    # set root -> first_party_level
    if formatter:
        hand = logging.StreamHandler()
        hand.setFormatter(formatter)
        logging.getLogger().addHandler(hand)
    logging.getLogger().setLevel(first_party_level)
    logging.getLogger().info(f"Root Logger: '' ({first_party_level})")

    all_known_base_loggers = set(
        lg.split(".", maxsplit=1)[0]
        for lg in first_parties
        + list(logging.root.manager.loggerDict)
        + future_third_parties
        + list(specialty_loggers.keys())
    )

    # base-loggers (including third-parties)
    # Ex: some_logger=A.B.C -> base_logger=A -> set A,
    #       only if A isn't a first_party/specialty_logger.
    #       Note: If A.B is claimed, that's okay; it'll be set later on
    for base_logger in sorted(all_known_base_loggers):
        if base_logger in first_parties + list(specialty_loggers.keys()):
            continue
        _set_and_share(base_logger, third_party_level, "Third-Party")

    # first-party
    for log_name in sorted(set(first_parties)):
        _set_and_share(log_name, first_party_level, "First-Party")

    # specialty loggers
    for log_name, level in sorted(specialty_loggers.items()):
        _set_and_share(log_name, level, "Specialty")
