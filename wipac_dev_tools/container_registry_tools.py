"""Utilities for working with container registries."""

import logging
import re
from pathlib import Path
from typing import Iterable, Union

import requests
from dateutil import parser as dateutil_parser

from .semver_parser_tools import (
    RE_VERSION_X,
    RE_VERSION_X_Y,
    RE_VERSION_X_Y_Z,
    strip_v_prefix,
)

LOGGER = logging.getLogger(__name__)


class ImageNotFoundException(Exception):
    """Raised when an image (tag) cannot be found."""

    def __init__(self, image: Union[str, Path]):
        super().__init__(f"Image '{image}' cannot be found.")


IMAGE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,128}$")

########################################################################################
# REGISTRY: CVMFS -- apptainer directory/sandbox containers
########################################################################################


class CVMFSRegistryTools:
    """Tools for working with CVMFS images directory."""

    def __init__(self, cvmfs_images_dir: Path, image_name: str):

        # ex: /cvmfs/icecube.opensciencegrid.org/containers/realtime/
        self.cvmfs_images_dir = cvmfs_images_dir

        # ex: skymap_scanner
        if not IMAGE_NAME_PATTERN.fullmatch(image_name):
            raise ValueError("'image_name' is invalid.")
        self.image_name = image_name

    def get_image_path(
        self,
        tag: str,
        check_exists: bool = False,
    ) -> Path:
        """Get the image path for 'tag' (optionally, check if it exists)."""

        # ex: /cvmfs/icecube.opensciencegrid.org/containers/realtime/skymap_scanner:v4.5.62
        dpath = self.cvmfs_images_dir / f"{self.image_name}:{tag}"

        # optional guardrail
        if check_exists and not dpath.exists():
            raise ImageNotFoundException(dpath)

        return dpath

    def iter_x_y_z_tags(self) -> Iterable[str]:
        """Iterate over all 'X.Y.Z' skymap scanner tags on CVMFS, newest semver to oldest."""
        x_y_z_tags: list[tuple[tuple[int, int, int], str]] = []

        for p in self.cvmfs_images_dir.glob(f"{self.image_name}:*"):
            try:
                tag = p.name.split(":", maxsplit=1)[1]
            except IndexError:
                continue
            if not RE_VERSION_X_Y_Z.fullmatch(tag):
                continue
            parts = tag.split(".")
            x_y_z_tags.append(
                (
                    (int(parts[0]), int(parts[1]), int(parts[2])),
                    tag,
                )
            )

        # yield tags in reverse semver order (v4.0.1 before v3.9.8)
        # -> sort by 'x_y_z' (tuple), yield 'tag' (str)
        for _, tag in sorted(x_y_z_tags, key=lambda t: t[0], reverse=True):
            yield tag

    def resolve_tag(self, source_tag: str) -> str:
        """Get the 'X.Y.Z' tag on CVMFS corresponding to `source_tag`.

        Examples:
            3.4.5     ->  3.4.5
            3.1       ->  3.1.5 (forever)
            3         ->  3.3.5 (on 2023/03/08)
            latest    ->  3.4.2 (on 2023/03/15)
            test-foo  ->  test-foo
            typO_t4g  ->  `ImageNotFoundException`
        """
        LOGGER.info(f"checking tag exists on cvmfs: {source_tag}")

        # step 0: prep tag
        try:
            source_tag = strip_v_prefix(source_tag)
        except ValueError as e:
            raise ImageNotFoundException(source_tag) from e

        # step 1: does the tag simply exist on cvmfs?
        try:
            _path = self.get_image_path(source_tag, check_exists=True)
            LOGGER.debug(f"tag exists on cvmfs: {_path}")
            return source_tag
        except ImageNotFoundException:
            pass

        # step 2: was the tag a non-specific tag (like 'latest', 'v4.1', 'v4', etc.)
        # -- case 1: user gave 'latest'
        if source_tag == "latest":
            for t in self.iter_x_y_z_tags():
                LOGGER.debug(f"resolved 'latest' to youngest X.Y.Z tag: {t}")
                return t
        # -- case 2: user gave an non-specific semver tag (like 'v4.1', 'v4', etc.)
        elif RE_VERSION_X_Y.fullmatch(source_tag) or RE_VERSION_X.fullmatch(source_tag):
            for t in self.iter_x_y_z_tags():
                # ex: '3.1.4' startswith '3.1.'
                if t.startswith(source_tag + "."):
                    LOGGER.debug(f"resolved '{source_tag}' to '{t}'")
                    return t

        # fall-through
        raise ImageNotFoundException(source_tag)


########################################################################################
# REGISTRY: DOCKER HUB
########################################################################################


class DockerHubRegistryTools:
    """Tools for working with the Docker Hub API."""

    def __init__(self, image_namespace: str, image_name: str):
        if not IMAGE_NAME_PATTERN.fullmatch(image_namespace):
            raise ValueError("'image_namespace' is invalid.")

        if not IMAGE_NAME_PATTERN.fullmatch(image_name):
            raise ValueError("'image_name' is invalid.")

        self.api_tags_url = f"https://hub.docker.com/v2/repositories/{image_namespace}/{image_name}/tags"

    def request_info(self, tag: str) -> tuple[dict, str]:
        """Get the json dict from GET @ Docker Hub, and the non v-prefixed tag (see below).

        Accepts v-prefixed tags, like 'v2.3.4', 'v4', etc. -- and non-v-prefixed tags.
        """
        LOGGER.info(f"retrieving tag info on docker hub: {tag}")

        # prep tag
        try:
            tag = strip_v_prefix(tag)
        except ValueError as e:
            raise ImageNotFoundException(tag) from e

        # look for tag on docker hub
        try:
            LOGGER.debug(f"looking at {self.api_tags_url} for {tag}...")
            r = requests.get(f"{self.api_tags_url.rstrip('/')}/{tag}")
            r.raise_for_status()
            resp = r.json()
        # -> http issue
        except requests.exceptions.HTTPError as e:
            LOGGER.exception(e)
            raise ImageNotFoundException(tag) from e
        # -> tag issue
        except Exception as e:
            LOGGER.exception(e)
            raise ImageNotFoundException(tag) from ValueError(
                "Image tag verification failed"
            )

        LOGGER.debug(resp)
        return resp, tag

    @staticmethod
    def parse_image_ts(info: dict) -> float:
        """Get the timestamp for when the image was created."""
        try:
            return dateutil_parser.parse(info["last_updated"]).timestamp()
        except Exception as e:
            LOGGER.exception(e)
            raise e
