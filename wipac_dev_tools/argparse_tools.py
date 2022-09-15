"""Simple tools used with argparse."""

from pathlib import Path
from typing import Optional, TypeVar

T = TypeVar("T")


def validate_arg(val: T, test: bool, exc: Exception) -> T:
    """Validation `val` by checking `test` and raise `exc` if that is falsy."""
    if test:
        return val
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
