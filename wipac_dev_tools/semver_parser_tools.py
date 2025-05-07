"""Tools for parsing semantic release versions (strings)."""

import logging
import time
from typing import List, Tuple

import requests
import semantic_version  # type: ignore[import-untyped]
from dateutil import parser

LOGGER = logging.getLogger(__name__)


def get_latest_py3_release() -> Tuple[int, int]:
    """Return the latest python3 release version (supported by GitHub) as
    tuple."""
    url = "https://raw.githubusercontent.com/actions/python-versions/main/versions-manifest.json"
    LOGGER.info(f"querying {url}")

    manifest = requests.get(url).json()
    manifest = [d for d in manifest if d["stable"]]  # only stable releases

    manifest = sorted(  # sort by version
        manifest,
        key=lambda d: [int(y) for y in d["version"].split(".")],
        reverse=True,
    )

    version = manifest[0]["version"]
    LOGGER.info(f"latest is {version}")

    return int(version.split(".")[0]), int(version.split(".")[1])


def get_python_eol_ts(python_version: str) -> float:
    """Return the end-of-life timestamp of a python version.

    See https://devguide.python.org/versions/ or https://endoflife.date/python
    """
    url = "https://endoflife.date/api/v1/products/python/"
    LOGGER.info(f"querying {url}")

    resp = requests.get(url).json()

    LOGGER.info(f"finding info on {python_version}")
    try:
        info = next(
            p for p in resp["result"]["releases"] if p["name"] == python_version
        )
    except StopIteration:
        raise ValueError(f"no info on {python_version}")

    return parser.parse(info["eolFrom"]).timestamp()


def is_python_eol(python_version: str) -> bool:
    """Return whether this python version is end of life.

    See https://devguide.python.org/versions/ or https://endoflife.date/python
    """
    return time.time() > get_python_eol_ts(python_version)


def list_all_majmin_versions(
    major: int,
    semver_range: str,
    max_minor: int = 99,
) -> List[Tuple[int, int]]:
    """Get a list of the matching major-minor versions for the semver range.

    Example:
        major: 3  semver_range: >=3.5.1,<3.9    max_minor: default  -> [3.6, 3.7, 3.8]
        major: 3  semver_range: >=3.5.1         max_minor: 8        -> [3.6, 3.7, 3.8]
        major: 3  semver_range: >=3,<3.6,!=3.3  max_minor: default  -> [3.0, 3.1, 3.2, 3.4, 3.5]
    """
    spec = semantic_version.SimpleSpec(semver_range.replace(" ", ""))

    filtered = spec.filter(
        semantic_version.Version(f"{major}.{i}.0") for i in range(max_minor + 1)
    )

    all_of_em = [(int(v.major), int(v.minor)) for v in filtered]
    LOGGER.info(f"matching major-minor versions: {all_of_em}")
    return all_of_em
