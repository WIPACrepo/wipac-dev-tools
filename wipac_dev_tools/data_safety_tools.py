"""Tools for handling sensitive data."""

_OBFUSCATE_SUBSTRINGS_UPPER = ["TOKEN", "AUTH", "PASS", "SECRET"]


def obfuscate_value_if_sensitive(name: str, value: str) -> str:
    """Return "***" if the included `value` is sensitive (by its `name`)."""
    if any(s in name.upper() for s in _OBFUSCATE_SUBSTRINGS_UPPER):
        return "***"
    else:
        return value
