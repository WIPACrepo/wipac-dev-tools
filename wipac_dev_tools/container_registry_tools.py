"""Utilities for dealing with docker/cvmfs/singularity images."""

import logging
from pathlib import Path
from typing import Iterable, Union

import requests

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


########################################################################################
# REGISTRY: CVMFS -- apptainer directory/sandbox containers
########################################################################################


class ImageCVMFS:
    """Tools for working with CVMFS images."""

    def __init__(self, cvmfs_images_dir: Path):
        # ex: /cvmfs/icecube.opensciencegrid.org/containers/realtime/
        self.cvmfs_images_dir = cvmfs_images_dir

    def get_image_path(
        self,
        image_name: str,
        tag: str,
        check_exists: bool = False,
    ) -> Path:
        """Get the image path for 'tag' (optionally, check if it exists)."""

        # ex: /cvmfs/icecube.opensciencegrid.org/containers/realtime/skymap_scanner:v4.5.62
        dpath = self.cvmfs_images_dir / f"{image_name}:{tag}"

        # optional guardrail
        if check_exists and not dpath.exists():
            raise ImageNotFoundException(dpath)

        return dpath

    def iter_x_y_z_tags(self, image_name: str) -> Iterable[str]:
        """Iterate over all 'X.Y.Z' skymap scanner tags on CVMFS, youngest to oldest."""

        # grab all container dirs -- ordered by age
        # ex: /cvmfs/icecube.opensciencegrid.org/containers/realtime/skymap_scanner:*
        cvmfs_tags = sorted(
            self.cvmfs_images_dir.glob(f"{image_name}:*"),
            key=lambda x: x.stat().st_mtime,  # filesystem modification time
            reverse=True,  # newest -> oldest
        )

        # yield only 'X.Y.Z' tags
        for p in cvmfs_tags:
            try:
                tag = p.name.split(":", maxsplit=1)[1]
            except IndexError:
                continue
            if not RE_VERSION_X_Y_Z.fullmatch(tag):
                continue
            # tag is a full 'X.Y.Z' tag
            yield tag

    def resolve_tag(
        self,
        image_name: str,
        source_tag: str,
    ) -> str:
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
            _path = self.get_image_path(image_name, source_tag, check_exists=True)
            LOGGER.debug(f"tag exists on cvmfs: {_path}")
            return source_tag
        except ImageNotFoundException:
            pass

        # step 2: was the tag a non-specific tag (like 'latest', 'v4.1', 'v4', etc.)
        # -- case 1: user gave 'latest'
        if source_tag == "latest":
            for source_tag in self.iter_x_y_z_tags(image_name):
                LOGGER.debug(f"resolved 'latest' to youngest X.Y.Z tag: {source_tag}")
                return source_tag
        # -- case 2: user gave an non-specific semver tag (like 'v4.1', 'v4', etc.)
        elif RE_VERSION_X_Y.fullmatch(source_tag) or RE_VERSION_X.fullmatch(source_tag):
            for source_tag in self.iter_x_y_z_tags(image_name):
                if source_tag.startswith(
                    source_tag + "."
                ):  # ex: '3.1.4' startswith '3.1.'
                    LOGGER.debug(f"resolved '{source_tag}' to '{source_tag}'")
                    return source_tag

        # fall-through
        raise ImageNotFoundException(source_tag)


########################################################################################
# REGISTRY: DOCKERHUB
########################################################################################


class ImageToolsDockerHub:
    """Tools for working with DockerHub images."""

    def __init__(self, api_tags_url: str):
        # ex: https://hub.docker.com/v2/repositories/icecube/skymap_scanner/tags
        self.api_tags_url = api_tags_url

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
