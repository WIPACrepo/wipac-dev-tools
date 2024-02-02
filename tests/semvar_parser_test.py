"""semvar_parser_test.py."""


import logging

from wipac_dev_tools import semvar_parser_tools

LOGGER = logging.getLogger(__name__)


def test_000() -> None:
    """Test with semvar ranges."""
    assert semvar_parser_tools.list_all_majmin_versions(
        major=3,
        semvar_range=">=3.5.1, <3.9",
        # max_minor=99,
    ) == [(3, 6), (3, 7), (3, 8)]

    assert semvar_parser_tools.list_all_majmin_versions(
        major=3,
        semvar_range=">=3.5.1",
        max_minor=8,
    ) == [(3, 6), (3, 7), (3, 8)]

    assert semvar_parser_tools.list_all_majmin_versions(
        major=3,
        semvar_range=">=3,<3.6,!=3.3",
        # max_minor=99,
    ) == [(3, 0), (3, 1), (3, 2), (3, 4), (3, 5)]

    assert not semvar_parser_tools.list_all_majmin_versions(
        major=2,
        semvar_range=">=3.5.1",
        # max_minor=99,
    )
