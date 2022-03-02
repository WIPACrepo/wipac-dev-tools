"""Module to build `setup.cfg` sections for use by `setup.py`/`setuptools`.

Used in CI/CD, used by GH Action.
"""

import argparse
import configparser
import os
import re
from dataclasses import dataclass
from typing import Iterator, List, Tuple, cast

BUIDLER_SECTION_NAME = "wipac:cicd_setup_builder"
GENERATED_STR = f"generated by {BUIDLER_SECTION_NAME}"
AUTHOR = "WIPAC Developers"
AUTHOR_EMAIL = "developers@icecube.wisc.edu"
DEFAULT_KEYWORDS = ["WIPAC", "IceCube"]
LICENSE = "MIT"

PythonMinMax = Tuple[Tuple[int, int], Tuple[int, int]]


@dataclass
class BuilderSection:
    """Encapsulates the `BUIDLER_SECTION_NAME` section & checks for required/invalid fields."""

    pypi_name: str
    description: str
    url: str
    python_range: str  # python_requires
    main_or_master: str = "main"
    keywords_spaced: str = ""  # comes as "A B C"

    def _python_min_max(self) -> PythonMinMax:
        """Get the `PythonMinMax` version of `self.python_range`."""
        m = re.match(
            r"(?P<lo_maj>\d+)\.(?P<lo_min>\d+) *- *(?P<hi_maj>\d+)\.(?P<hi_min>\d+).*",
            self.python_range,
        )
        assert m  # TODO
        versions = (
            (int(m.groupdict()["lo_maj"]), int(m.groupdict()["lo_min"])),
            (int(m.groupdict()["hi_maj"]), int(m.groupdict()["hi_min"])),
        )
        return cast(PythonMinMax, tuple(sorted(versions)))

    def python_requires(self) -> str:
        """Get a `[metadata]/python_requires` string from `self.python_range`.

        Ex: "">=3.6, <=3.10"
        """
        py_min_max = self._python_min_max()
        return f">={py_min_max[0][0]}.{py_min_max[0][1]}, <{py_min_max[1][0]}.{py_min_max[1][1]+1}"

    def python_classifiers(self) -> List[str]:
        """Get auto-detected `Programming Language :: Python :: *` list.

        NOTE: Will not work after the '3.* -> 4.0'-transition.
        """
        py_min_max = self._python_min_max()
        if py_min_max[0][0] < 3:
            raise Exception("Python-classifier automation does not work for python <3.")
        if py_min_max[1][0] >= 4:
            raise Exception("Python-classifier automation does not work for python 4+.")

        return [
            f"Programming Language :: Python :: 3.{r}"
            for r in range(py_min_max[0][1], py_min_max[1][1] + 1)
        ]

    def keywords_list(self) -> List[str]:
        """Get the user-defined keywords as a list."""
        return self.keywords_spaced.strip().split()


def list_to_dangling(lines: List[str]) -> str:
    """Create a "dangling"-lines formatted list."""
    return "\n" + "\n".join(lines)


def long_description_content_type(extension: str) -> str:
    """Return the long_description_content_type for the given file extension (no dot)."""
    if extension == "md":
        return "text/markdown"
    elif extension == ".rst":
        return "text/x-rst"
    else:
        return "text/plain"


class FromFiles:
    """Get things that require reading files."""

    def __init__(self, root: str) -> None:
        assert os.path.exists(root)
        self.root = os.path.abspath(root)
        self.pkg_path = self._get_package()
        self.package = os.path.basename(self.pkg_path)
        self.readme_ext = self._get_readme_ext()

    def _get_package(self) -> str:
        """Find the package."""

        def _get_packages() -> Iterator[str]:
            for directory in os.listdir(self.root):
                directory = os.path.join(self.root, directory)
                if not os.path.isdir(directory):
                    continue
                if "__init__.py" in os.listdir(directory):
                    yield directory

        pkgs = list(_get_packages())
        if not pkgs:
            raise Exception(
                f"No package found in '{self.root}'. Are you missing an __init__.py?"
            )
        if len(pkgs) > 1:
            raise Exception(
                f"More than one package found in '{self.root}' ({pkgs}). Remove extra __init__.py files."
            )
        return pkgs[0]

    def _get_readme_ext(self) -> str:
        """Return the file extension of the 'README' file."""
        for fname in os.listdir(self.root):
            if fname.startswith("README."):
                return fname.split("README.")[1]
        raise Exception(f"No README file found in '{self.root}'")


def _build_out_sections(cfg: configparser.RawConfigParser, root_path: str) -> None:
    """Build out the `[metadata]`, `[semantic_release]`, and `[options]` sections."""

    bsec = BuilderSection(**dict(cfg[BUIDLER_SECTION_NAME]))  # checks req/extra fields
    ffile = FromFiles(root_path)  # get things that require reading files

    # [metadata]
    cfg["metadata"] = {
        "name": bsec.pypi_name,
        "version": f"attr: {ffile.package}.__version__",  # "wipac_dev_tools.__version__"
        "author": AUTHOR,
        "author_email": AUTHOR_EMAIL,
        "description": bsec.description,
        # any of these files that don't exist are simply ignored, so list everything that could be
        "long_description": f"file: README.{ffile.readme_ext}, CHANGELOG.{ffile.readme_ext}, LICENSE.{ffile.readme_ext}",
        "long_description_content_type": long_description_content_type(
            ffile.readme_ext
        ),
        "keywords": list_to_dangling(bsec.keywords_list() + DEFAULT_KEYWORDS),
        "license": LICENSE,
        # TODO: add "Development Status :: *", any way to do this without knowing abspath?
        "classifiers": list_to_dangling(bsec.python_classifiers()),
    }

    # [semantic_release]
    cfg["semantic_release"] = {
        "version_variable": f"attr: {ffile.package}/__init__.py:__version__",  # "wipac_dev_tools/__init__.py:__version__"
        "upload_to_pypi": "True",
        "patch_without_tag": "True",
        "commit_parser": "semantic_release.history.tag_parser",
        "minor_tag": "[minor]",
        "fix_tag": "[fix]",
        "branch": bsec.main_or_master,
    }

    # [options] -- override specific options
    cfg["options"]["python_requires"] = bsec.python_requires()
    cfg["options"]["packages"] = "find:"


def build(setup_cfg: str) -> None:
    """Build the `setup.cfg` sections according to `BUIDLER_SECTION_NAME`."""
    setup_cfg = os.path.abspath(setup_cfg)

    cfg = configparser.RawConfigParser(allow_no_value=True, comment_prefixes="/")
    cfg.read(setup_cfg)
    assert cfg.has_section(BUIDLER_SECTION_NAME)  # TODO
    cfg.remove_section("metadata")  # will be overridden
    cfg.remove_section("semantic_release")  # will be overridden
    if not cfg.has_section("options"):  # will only override some options (fields)
        cfg["options"] = {}

    # NOTE: 'install_requires' (& 'extras_require') are important and shouldn't be overridden

    _build_out_sections(cfg, os.path.dirname(setup_cfg))

    # Re-order some sections to the top
    tops = [BUIDLER_SECTION_NAME, "metadata", "semantic_release", "options"]
    for sec in cfg.sections():  # and any 'options.*', if present
        if sec.startswith("options."):
            tops.append(sec)

    # Build new 'setup.cfg'
    cfg_new = configparser.RawConfigParser()
    for sec in tops:
        cfg_new[sec] = cfg[sec]
    for sec in cfg.sections():  # add rest of existing sections
        if sec not in tops:
            cfg_new[sec] = cfg[sec]
    cfg_new.write(open(setup_cfg, "w"))

    # Comment generated sections w/ comments saying so & clean up whitespace
    with open(setup_cfg) as f:
        c = f.read()
        c = c.replace("[metadata]", f"[metadata]  # {GENERATED_STR}")
        c = c.replace("[semantic_release]", f"[semantic_release]  # {GENERATED_STR}")
        c = c.replace(
            "[options]", f"[options]  # {GENERATED_STR}: 'python_requires', 'packages'"
        )
        c = re.sub(r"(\t| )+\n", "\n", c)  # remove trailing whitespace
        print(c)
    with open(setup_cfg, "w") as f:
        f.write(c)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=f"Read and transform 'setup.cfg' file. "
        f"Builds out sections according to [{BUIDLER_SECTION_NAME}].",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("setup_cfg_file")
    args = parser.parse_args()
    build(args.setup_cfg_file)
