"""Simple tools used with argparse."""

import argparse
from pathlib import Path
from typing import Optional, TypeVar

T = TypeVar("T")


def validate_arg(val: T, test: bool, exc: Exception) -> T:
    """Validation `val` by checking `test` and raise `exc` if that is falsy.

    If the passed exception is not an instance of `ArgumentTypeError`,
    then an `ArgumentTypeError` instance is raised, like so:
        `ArgumentTypeError(f"{repr(exc)} [{val}]")`
    """
    if test:
        return val

    # The argument to type can be any callable that accepts a single string.
    # If the function raises ArgumentTypeError, TypeError, or ValueError,
    # the exception is caught and a nicely formatted error message is displayed.
    # No other exception types are handled.
    if not isinstance(exc, argparse.ArgumentTypeError):
        raise argparse.ArgumentTypeError(f"{repr(exc)} [{val}]")

    raise exc


def create_dir(val: str) -> Optional[Path]:
    """Create the given directory, if needed.

    Create parent directories, if needed.
    """
    if not val:
        return None
    path = Path(val)
    path.mkdir(parents=True, exist_ok=True)
    return path
