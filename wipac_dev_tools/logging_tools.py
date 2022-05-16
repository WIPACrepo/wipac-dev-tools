"""Common tools to supplement/assist the standard logging package."""

import argparse
import logging
from typing import List, Optional, Union

from typing_extensions import Literal  # will redirect to Typing for 3.8+

LoggerLevel = Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]


def log_argparse_args(
    args: argparse.Namespace,
    logger: Optional[Union[str, logging.Logger]] = None,
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
    if not logger:
        _logger = logging.getLogger()
    elif isinstance(logger, logging.Logger):
        _logger = logger
    else:
        _logger = logging.getLogger(logger)

    if level not in ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]:
        raise ValueError(f"Invalid logging level: {level}")
    log = getattr(_logger, level.lower())  # ..., info, warning, critical, ...
    for arg, val in vars(args).items():
        log(f"{arg}: {val}")

    return args


def set_level(
    level: str,
    first_party_loggers: Optional[List[Union[str, logging.Logger]]] = None,
    third_party_level: LoggerLevel = "WARNING",
    use_coloredlogs: bool = False,
) -> None:
    """Set the level of the root logger, first-party loggers, and third-party loggers.

    The root logger and first-party logger(s) are set to the same level
    (`level`). The third-party loggers are non-root and non-first-party
    loggers that are defined at the time of invocation. If a logger is
    created after this function call, then its level defaults to its
    parent (that's the root logger for non-child loggers).

    Passing `use_coloredlogs=True` will import and use the `coloredlogs`
    package. This will set the logger format and use colored text.
    """
    if not first_party_loggers:
        first_party_loggers = []

    # root
    if use_coloredlogs:
        try:
            import coloredlogs  # type: ignore[import]  # pylint: disable=import-outside-toplevel

            coloredlogs.install(level=level)  # root
        except ImportError:
            logging.getLogger("wipac_dev_tools.logging_tools").warning(
                "set_level()'s `use_coloredlogs` was set to `True`, "
                "but coloredlogs is not installed. Proceeding with only logging package."
            )
            logging.getLogger().setLevel(level)
    else:
        logging.getLogger().setLevel(level)

    # first-party
    for log in first_party_loggers:
        if isinstance(log, logging.Logger):
            log.setLevel(level)
        else:  # str
            logging.getLogger(log).setLevel(level)

    # third-party
    for log_name in logging.root.manager.loggerDict:
        if log_name in first_party_loggers:
            continue
        if logging.getLogger(log_name) in first_party_loggers:
            continue
        logging.getLogger(log_name).setLevel(third_party_level)
