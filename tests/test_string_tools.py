"""Unit tests for string_tools."""

import pytest

from wipac_dev_tools.string_tools import regex_named_groups_to_template


# ---------------------------------------------------------------------------
# Core behavior: named groups become {name}
# ---------------------------------------------------------------------------


def test_000_replaces_single_named_group() -> None:
    inp = r"/TransferRequests/(?P<request_id>[^/]+)$"
    out = regex_named_groups_to_template(inp)
    assert out == "/TransferRequests/{request_id}"


def test_001_replaces_multiple_named_groups() -> None:
    inp = r"/users/(?P<user_id>\d+)/posts/(?P<post_id>\d+)$"
    out = regex_named_groups_to_template(inp)
    assert out == r"/users/{user_id}/posts/{post_id}"


def test_002_preserves_non_named_regex_syntax() -> None:
    inp = r"(foo|bar)/(?P<id>\d+)$"
    out = regex_named_groups_to_template(inp)
    assert out == r"(foo|bar)/{id}"


def test_003_returns_input_when_no_named_groups() -> None:
    inp = r"/static/path$"
    out = regex_named_groups_to_template(inp)
    assert out == r"/static/path"


# ---------------------------------------------------------------------------
# Dollar stripping behavior
# ---------------------------------------------------------------------------


def test_010_default_strips_trailing_dollar() -> None:
    inp = r"/x/(?P<id>\d+)$"
    out = regex_named_groups_to_template(inp)
    assert out == r"/x/{id}"


def test_011_can_disable_stripping_trailing_dollar() -> None:
    inp = r"/x/(?P<id>\d+)$"
    out = regex_named_groups_to_template(inp, rstrip_dollar=False)
    assert out == r"/x/{id}$"


def test_012_strips_only_at_end_not_middle() -> None:
    inp = r"foo$(?P<x>\w+)$"
    out = regex_named_groups_to_template(inp)
    assert out == r"foo${x}"


def test_013_rstrip_removes_all_trailing_dollars() -> None:
    inp = r"/x/(?P<id>\d+)$$$"
    out = regex_named_groups_to_template(inp)
    assert out == r"/x/{id}"


# ---------------------------------------------------------------------------
# Escapes and nested content inside the group
# ---------------------------------------------------------------------------


def test_020_group_with_escaped_paren_does_not_break() -> None:
    inp = r"/x/(?P<val>a\)b\()$"
    out = regex_named_groups_to_template(inp)
    assert out == r"/x/{val}"


def test_021_group_with_character_class_and_escapes() -> None:
    inp = r"USER=(?P<user>[A-Za-z0-9_]+)\s+IP=(?P<ip>\d+\.\d+\.\d+\.\d+)$"
    out = regex_named_groups_to_template(inp)
    assert out == r"USER={user}\s+IP={ip}"


# ---------------------------------------------------------------------------
# Edge cases / limitations (explicitly tested)
# ---------------------------------------------------------------------------


def test_030_does_not_replace_numbered_groups() -> None:
    inp = r"/x/(\d+)$"
    out = regex_named_groups_to_template(inp)
    assert out == r"/x/(\d+)"


@pytest.mark.parametrize(
    ("inp", "expected"),
    [
        (r"(?P<_ok>\w+)$", r"{_ok}"),
        (r"(?P<ok123>\w+)$", r"{ok123}"),
        (r"(?P<OK_OK>\w+)$", r"{OK_OK}"),
    ],
)
def test_031_accepts_valid_identifier_like_names(inp: str, expected: str) -> None:
    out = regex_named_groups_to_template(inp)
    assert out == expected


def test_032_invalid_group_name_is_left_unchanged() -> None:
    inp = r"(?P<9bad>\w+)$"
    out = regex_named_groups_to_template(inp)
    assert out == r"(?P<9bad>\w+)"
