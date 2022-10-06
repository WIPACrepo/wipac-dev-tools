"""Common tools to supplement/assist the standard logging package."""

import argparse
import logging
from typing import Callable, List, TypeVar, Union

from typing_extensions import Literal  # will redirect to Typing for 3.8+

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

    Return the args (Namespace) unchanged.

    Example:
        2022-05-13 22:37:21 fv-az136-643 my-logs[61] WARNING in_file: in_msg.pkl
        2022-05-13 22:37:21 fv-az136-643 my-logs[61] WARNING out_file: out_msg.pkl
        2022-05-13 22:37:21 fv-az136-643 my-logs[61] WARNING log: DEBUG
        2022-05-13 22:37:21 fv-az136-643 my-logs[61] WARNING log_third_party: WARNING
    """
    logger_fn = get_logger_fn(logger, level)

    for arg, val in vars(args).items():
        logger_fn(f"{arg}: {val}")

    return args


T = TypeVar("T")


def log_dataclass(
    dclass: T, logger: Union[str, logging.Logger], level: LoggerLevel
) -> T:
    """Log a dataclass instance's fields and members."""
    import dataclasses  # imports for python 3.7+

    if not (dataclasses.is_dataclass(dclass) and not isinstance(dclass, type)):
        raise TypeError(f"Expected instantiated dataclass: 'dclass' ({dclass})")

    logger_fn = get_logger_fn(logger, level)

    for field in dataclasses.fields(dclass):
        logger_fn(f"(env) {field.name}: {getattr(dclass, field.name)}")

    return dclass


def _to_list(pseudo_list: Union[None, T, List[T]]) -> List[T]:
    if not pseudo_list:
        return []
    elif not isinstance(pseudo_list, list):
        return [pseudo_list]
    else:
        return pseudo_list


def _set_and_share(log_name: str, level: LoggerLevel, text: str) -> None:
    logging.getLogger(log_name).setLevel(level)
    logging.getLogger().info(f"{text} Logger: '{log_name}' ({level})")


def set_level(
    level: LoggerLevel,
    first_party_loggers: Union[
        None, str, logging.Logger, List[Union[str, logging.Logger]]
    ] = None,
    third_party_level: LoggerLevel = "WARNING",
    future_third_parties: Union[None, str, List[str]] = None,
    use_coloredlogs: bool = False,
) -> None:
    """Set the level of the root logger, first-party loggers, and third-party
    loggers.

    The root logger and first-party logger(s) are set to the same level (`level`).

    Args:
        `level`
            the desired logging level (first-party), case-insensitive
        `first_party_loggers`
            a list (or a single instance) of `logging.Logger` or the loggers' names
        `third_party_level`
            the desired logging level for any other (currently) available loggers, case-insensitive
        `future_third_parties`
            additional third party logger(s) which have not yet been created
        `use_coloredlogs`
            if True, will import and use the `coloredlogs` package.
            This will set the logger format and use colored text.
    """
    # convert to names (str) only
    first_parties: List[str] = []

    for lg in _to_list(first_party_loggers):
        if isinstance(lg, logging.Logger):
            first_parties.append(lg.name)
        elif isinstance(lg, str):
            first_parties.append(lg)
        else:
            raise TypeError(
                f"'first_party_loggers' must be either 'None', or "
                f"a list of Logger instances or names: {first_party_loggers}"
            )

    return _set_level(
        level.upper(),  # type: ignore
        first_parties,
        third_party_level.upper(),  # type: ignore
        list(logging.root.manager.loggerDict) + _to_list(future_third_parties),
        use_coloredlogs,
    )


def _set_level(
    first_party_level: LoggerLevel,
    first_parties: List[str],
    third_party_level: LoggerLevel,
    third_parties: List[str],
    use_coloredlogs: bool,
) -> None:
    # root
    if use_coloredlogs:
        try:
            import coloredlogs  # type: ignore[import]  # pylint: disable=import-outside-toplevel

            coloredlogs.install(level=first_party_level)  # root
        except ImportError:
            logging.getLogger().warning(
                "set_level()'s `use_coloredlogs` was set to `True`, "
                "but 'coloredlogs' is not installed. Proceeding with 'logging' package."
            )
            logging.getLogger().setLevel(first_party_level)
    else:
        logging.getLogger().setLevel(first_party_level)
    logging.getLogger().info(f"Root Logger: '' ({first_party_level})")

    # third-party
    # Ex: third_party=A.B.C -> set A, if A isn't a first_party
    # Ex: first_party=X.Y -> set X, if X isn't a first_party
    for base_logger in sorted(
        set(lg.split(".", maxsplit=1)[0] for lg in third_parties + first_parties)
    ):
        if base_logger not in first_parties:
            _set_and_share(base_logger, third_party_level, "Third-Party")

    # first-party
    for log_name in sorted(set(first_parties)):
        _set_and_share(log_name, first_party_level, "First-Party")
