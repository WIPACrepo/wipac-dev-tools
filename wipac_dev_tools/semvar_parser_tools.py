"""Tools for parsing semantic release versions (strings)."""


import logging
from typing import List, Tuple

import requests
import semantic_version  # type: ignore[import-untyped]

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


def list_py3_releases(semvar_range: str) -> List[Tuple[int, int]]:
    """Get a list of the matching python3 releases for the semvar range."""
    spec = semantic_version.SimpleSpec(semvar_range.replace(" ", ""))
    LOGGER.info(f"getting the max supported python3 release for {spec}")

    latest_py3_minor = get_latest_py3_release()[1]  # 3.5 -> (3,5) -> 5

    filtered = spec.filter(
        semantic_version.Version(f"3.{i}.0") for i in range(latest_py3_minor + 1)
    )

    all_of_em = [(int(v.major), int(v.minor)) for v in filtered]
    LOGGER.info(f"supported Python releases: {all_of_em}")
    return all_of_em
