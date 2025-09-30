"""Tests for container_registry_tools.py"""

import logging
import os
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
import requests

from wipac_dev_tools.container_registry_tools import (
    CVMFSRegistryTools,
    DockerHubRegistryTools,
    ImageNotFoundException,
)

LOGGER = logging.getLogger(__name__)


def log_cvmfs_dir(d: Path) -> None:
    """Log all files in `d` with their mtime."""
    entries = [(p, p.stat().st_mtime) for p in d.iterdir()]

    for p, mtime in sorted(entries, key=lambda x: x[1], reverse=True):
        iso = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
        LOGGER.debug(f"{mtime=} ({iso}) {p.name}")


# --------------------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------------------


@pytest.fixture()
def cvmfs_dir(tmp_path: Path) -> Path:
    """
    Create a CVMFS-like directory where mtimes are randomized so semver ordering
    does not correlate with filesystem age.
    """
    semver_order = ["4.1.5", "4.0.2", "3.9.9"]

    # only junk that won't be parsed or matched as semver tags
    non_semvers = ["foo", "feat", "test-tag"]

    for tag in [*semver_order, *non_semvers]:
        (tmp_path / f"skymap_scanner:{tag}").mkdir(parents=True)

    # assign random mtimes
    for tag in [*semver_order, *non_semvers]:
        p = tmp_path / f"skymap_scanner:{tag}"
        mtime = time.time() + random.uniform(-10_000, 10_000)  # ± ~3 hours range
        os.utime(p, (mtime, mtime))

    log_cvmfs_dir(tmp_path)

    return tmp_path


@pytest.fixture()
def cvmfs_tools(cvmfs_dir: Path) -> CVMFSRegistryTools:
    """Return a CVMFSRegistryTools instance pointing to the temporary CVMFS dir."""
    return CVMFSRegistryTools(cvmfs_dir, "skymap_scanner")


# --------------------------------------------------------------------------------------
# CVMFS
# --------------------------------------------------------------------------------------


def test_1000_iter_x_y_z_tags_semver_order(cvmfs_tools: CVMFSRegistryTools) -> None:
    """iter_x_y_z_tags should yield only X.Y.Z tags in reverse semver order."""
    got = list(cvmfs_tools.iter_x_y_z_tags())
    assert got == ["4.1.5", "4.0.2", "3.9.9"]


def test_1010_get_image_path_exists_and_missing(
    cvmfs_tools: CVMFSRegistryTools, cvmfs_dir: Path
) -> None:
    """get_image_path should return existing paths and raise for missing ones."""
    p = cvmfs_tools.get_image_path("4.1.5", check_exists=True)
    assert p == cvmfs_dir / "skymap_scanner:4.1.5"
    assert p.exists()

    with pytest.raises(ImageNotFoundException):
        cvmfs_tools.get_image_path("9.9.9", check_exists=True)


def test_1020_resolve_tag_exact(cvmfs_tools: CVMFSRegistryTools) -> None:
    """resolve_tag should return the tag unchanged if it exists exactly."""
    assert cvmfs_tools.resolve_tag("4.0.2") == "4.0.2"
    assert cvmfs_tools.resolve_tag("foo") == "foo"


def test_1030_resolve_tag_latest(cvmfs_tools: CVMFSRegistryTools) -> None:
    """resolve_tag should map 'latest' to the newest X.Y.Z tag."""
    assert cvmfs_tools.resolve_tag("latest") == "4.1.5"


def test_1040_resolve_tag_major_and_minor(cvmfs_tools: CVMFSRegistryTools) -> None:
    """resolve_tag should map major- or minor-only tags to the newest matching X.Y.Z."""
    assert cvmfs_tools.resolve_tag("4") == "4.1.5"
    assert cvmfs_tools.resolve_tag("v4") == "4.1.5"
    assert cvmfs_tools.resolve_tag("4.0") == "4.0.2"
    assert cvmfs_tools.resolve_tag("v4.0") == "4.0.2"


def test_1050_resolve_tag_invalid_raises(cvmfs_tools: CVMFSRegistryTools) -> None:
    """resolve_tag should raise ImageNotFoundException for invalid or missing tags."""
    with pytest.raises(ImageNotFoundException):
        cvmfs_tools.resolve_tag("does-not-exist")
    with pytest.raises(ImageNotFoundException):
        cvmfs_tools.resolve_tag("v")


def test_1060_constructor_image_name_validation(cvmfs_dir: Path) -> None:
    """Constructor should reject invalid image names and accept valid ones."""
    with pytest.raises(ValueError):
        CVMFSRegistryTools(cvmfs_dir, "invalid name!")
    CVMFSRegistryTools(cvmfs_dir, "A._-9")


# --------------------------------------------------------------------------------------
# DockerHub
# --------------------------------------------------------------------------------------


class _DummyResp:
    """Dummy response object to mock requests.get."""

    def __init__(self, status_code: int, payload: dict[str, Any]):
        self.status_code = status_code
        self._payload = payload
        self.url = "https://foo-hub-docker.com/"
        self.reason = "OK" if status_code == 200 else "Not Found"

    def raise_for_status(self) -> None:
        if not (200 <= self.status_code < 300):
            raise requests.exceptions.HTTPError(f"{self.status_code} {self.reason}")

    def json(self) -> dict[str, Any]:
        return self._payload


def test_2000_dockerhub_request_info_strips_v_and_returns_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """request_info should strip 'v' prefix and return payload JSON."""
    payload = {"name": "4.1.5", "last_updated": "2025-09-01T12:34:56Z"}

    def fake_get(url: str) -> _DummyResp:  # noqa: ANN001
        assert url.endswith("/4.1.5")
        return _DummyResp(200, payload)

    monkeypatch.setattr(
        "wipac_dev_tools.container_registry_tools.requests.get", fake_get
    )

    dht = DockerHubRegistryTools("icecube", "skymap_scanner")
    info, tag = dht.request_info("v4.1.5")
    assert tag == "4.1.5"
    assert info == payload


def test_2010_dockerhub_request_info_http_error_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """request_info should raise ImageNotFoundException on HTTP error."""

    def fake_get(url: str) -> _DummyResp:  # noqa: ANN001
        return _DummyResp(404, {"detail": "not found"})

    monkeypatch.setattr(
        "wipac_dev_tools.container_registry_tools.requests.get", fake_get
    )

    dht = DockerHubRegistryTools("icecube", "skymap_scanner")
    with pytest.raises(ImageNotFoundException):
        dht.request_info("4.1.5")


def test_2020_parse_image_ts_parses_last_updated() -> None:
    """parse_image_ts should return a float timestamp from last_updated."""
    info = {"last_updated": "2025-09-01T12:34:56Z"}
    ts = DockerHubRegistryTools.parse_image_ts(info)
    expected = datetime(
        2025,
        9,
        1,
        12,
        34,
        56,
        tzinfo=timezone.utc,
    ).timestamp()
    assert abs(ts - expected) < 1e-6
