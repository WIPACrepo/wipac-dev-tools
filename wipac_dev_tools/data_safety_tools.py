"""Tools for handling sensitive data."""

_OBFUSCATE_SUBSTRINGS_UPPER = ["TOKEN", "AUTH", "PASS", "SECRET"]


def is_name_sensitive(name: str) -> bool:
    """Return whether `name` is considered sensitive."""
    return any(s in name.upper() for s in _OBFUSCATE_SUBSTRINGS_UPPER)


def obfuscate_value_if_sensitive(name: str, value: str) -> str:
    """Return "***" if the included `value` is sensitive (by its `name`)."""
    if is_name_sensitive(name):
        return "***"
    else:
        return value
