"""Common tools to supplement/assist the standard logging package."""

import logging
from typing import List, Optional, Union


def set_level(
    level: str,
    first_party_loggers: Optional[List[Union[str, logging.Logger]]] = None,
    third_party_level: str = "WARNING",
    use_coloredlogs: bool = False,
) -> None:
    """Set the level of the root logger, first-party loggers, and third-party loggers.

    Passing `use_coloredlogs=True` will import and use the `coloredlogs`
    package. This will set the logger format and use colored text.
    """
    if not first_party_loggers:
        first_party_loggers = []

    # root
    if use_coloredlogs:
        import coloredlogs  # type: ignore[import]  # pylint: disable=import-outside-toplevel

        coloredlogs.install(level=level)  # root
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
