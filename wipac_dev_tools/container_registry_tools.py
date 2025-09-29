"""Utilities for dealing with docker/cvmfs/singularity images."""

import logging
from pathlib import Path
from typing import Iterable, Union

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


def get_cvmfs_image_path(
    cvmfs_images_dir: Path,
    image_name: str,
    tag: str,
    check_exists: bool = False,
) -> Path:
    """Get the image path for 'tag' (optionally, check if it exists)."""
    dpath = cvmfs_images_dir / f"{image_name}:{tag}"

    # optional guardrail
    if check_exists and not dpath.exists():
        raise ImageNotFoundException(dpath)

    return dpath


def iter_x_y_z_cvmfs_tags(cvmfs_images_dir: Path, image_name: str) -> Iterable[str]:
    """Iterate over all 'X.Y.Z' skymap scanner tags on CVMFS, youngest to oldest."""

    # grab all container dirs -- ordered by age
    # ex: /cvmfs/icecube.opensciencegrid.org/containers/realtime/skymap_scanner:*
    cvmfs_tags = sorted(
        cvmfs_images_dir.glob(f"{image_name}:*"),
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


def resolve_tag_on_cvmfs(
    cvmfs_images_dir: Path,
    image_name: str,
    docker_tag: str,
) -> str:
    """Get the 'X.Y.Z' tag on CVMFS corresponding to `docker_tag`.

    Examples:
        3.4.5     ->  3.4.5
        3.1       ->  3.1.5 (forever)
        3         ->  3.3.5 (on 2023/03/08)
        latest    ->  3.4.2 (on 2023/03/15)
        test-foo  ->  test-foo
        typO_t4g  ->  `ImageNotFoundException`
    """
    LOGGER.info(f"checking tag exists on cvmfs: {docker_tag}")

    # step 0: prep tag
    try:
        docker_tag = strip_v_prefix(docker_tag)
    except ValueError as e:
        raise ImageNotFoundException(docker_tag) from e

    # step 1: does the tag simply exist on cvmfs?
    try:
        _path = get_cvmfs_image_path(
            cvmfs_images_dir,
            image_name,
            docker_tag,
            check_exists=True,
        )
        LOGGER.debug(f"tag exists on cvmfs: {_path}")
        return docker_tag
    except ImageNotFoundException:
        pass

    # step 2: was the tag a non-specific tag (like 'latest', 'v4.1', 'v4', etc.)
    # -- case 1: user gave 'latest'
    if docker_tag == "latest":
        for tag in iter_x_y_z_cvmfs_tags(cvmfs_images_dir, image_name):
            LOGGER.debug(f"resolved 'latest' to youngest X.Y.Z tag: {tag}")
            return tag
    # -- case 2: user gave an non-specific semver tag (like 'v4.1', 'v4', etc.)
    elif RE_VERSION_X_Y.fullmatch(docker_tag) or RE_VERSION_X.fullmatch(docker_tag):
        for tag in iter_x_y_z_cvmfs_tags(cvmfs_images_dir, image_name):
            if tag.startswith(docker_tag + "."):  # ex: '3.1.4' startswith '3.1.'
                LOGGER.debug(f"resolved '{docker_tag}' to '{tag}'")
                return tag

    # fall-through
    raise ImageNotFoundException(docker_tag)
