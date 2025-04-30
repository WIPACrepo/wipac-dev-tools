"""semver_parser_test.py."""


import logging

from wipac_dev_tools import semver_parser_tools

LOGGER = logging.getLogger(__name__)


def test_000() -> None:
    """Test with semver ranges."""
    assert semver_parser_tools.list_all_majmin_versions(
        major=3,
        semver_range=">=3.5.1, <3.9",
        # max_minor=99,
    ) == [(3, 6), (3, 7), (3, 8)]

    assert semver_parser_tools.list_all_majmin_versions(
        major=3,
        semver_range=">=3.5.1",
        max_minor=8,
    ) == [(3, 6), (3, 7), (3, 8)]

    assert semver_parser_tools.list_all_majmin_versions(
        major=3,
        semver_range=">=3,<3.6,!=3.3",
        # max_minor=99,
    ) == [(3, 0), (3, 1), (3, 2), (3, 4), (3, 5)]

    assert not semver_parser_tools.list_all_majmin_versions(
        major=2,
        semver_range=">=3.5.1",
        # max_minor=99,
    )
