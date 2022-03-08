"""Module to build `setup.cfg` sections for use by `setup.py`/`setuptools`.

Used in CI/CD, used by GH Action.
"""

import argparse
import configparser
import os
import re
from dataclasses import dataclass
from typing import Iterator, List, Optional, Tuple, cast

import requests

BUILDER_SECTION_NAME = "wipac:cicd_setup_builder"
GENERATED_STR = f"generated by {BUILDER_SECTION_NAME}"
AUTHOR = "WIPAC Developers"
AUTHOR_EMAIL = "developers@icecube.wisc.edu"
DEFAULT_KEYWORDS = ["WIPAC", "IceCube"]
LICENSE = "MIT"

REAMDE_BADGES_START_DELIMITER = "<!--- Top of README Badges (automated) --->"
REAMDE_BADGES_END_DELIMITER = "<!--- End of README Badges (automated) --->"

_PYTHON_MINOR_RELEASE_MAX = 50

PythonMinMax = Tuple[Tuple[int, int], Tuple[int, int]]


def get_latest_py3_release() -> Tuple[int, int]:
    """Return the latest python3 release version as tuple."""
    minor = 10  # start with 3.10
    while True:
        url = f"https://docs.python.org/release/3.{minor}.0/"
        if requests.get(url).status_code >= 300:  # not a success (404 likely)
            return (3, minor - 1)
        if minor == _PYTHON_MINOR_RELEASE_MAX:
            raise Exception(
                "Latest python-release detection failed (unless python 3.50 is real?)"
            )
        minor += 1


class GitHubAPI:
    """Relay info from the GitHub API."""

    def __init__(self, github_full_repo: str) -> None:
        self.url = f"https://github.com/{github_full_repo}"

        _json = requests.get(f"https://api.github.com/repos/{github_full_repo}").json()
        self.default_branch = cast(str, _json["default_branch"])  # main/master/etc.
        self.description = cast(str, _json["description"])


@dataclass
class BuilderSection:
    """Encapsulates the `BUILDER_SECTION_NAME` section & checks for required/invalid fields."""

    pypi_name: str
    python_min: str  # python_requires
    keywords_spaced: str = ""  # comes as "A B C"

    def _python3_min_max(self) -> PythonMinMax:
        """Get the `PythonMinMax` version of `self.python_min`."""
        m = re.match(r"(?P<maj>\d+)\.(?P<min>\d+)$", self.python_min)
        if not m:
            raise Exception(f"'python_min' is not a valid release: '{self.python_min}'")

        major, minor = int(m.groupdict()["maj"]), int(m.groupdict()["min"])

        if major < 3:
            raise Exception("Python-release automation does not work for python <3.")
        if major >= 4:
            raise Exception("Python-release automation does not work for python 4+.")

        versions = ((3, minor), get_latest_py3_release())
        return cast(PythonMinMax, tuple(sorted(versions)))

    def python_requires(self) -> str:
        """Get a `[metadata]/python_requires` string from `self.python_range`.

        Ex: "">=3.6, <3.10" (cannot do "<=3.9" because 3.9.1 > 3.9)
        """
        py_min_max = self._python3_min_max()
        return f">={py_min_max[0][0]}.{py_min_max[0][1]}, <{py_min_max[1][0]}.{py_min_max[1][1]+1}"

    def python_classifiers(self) -> List[str]:
        """Get auto-detected `Programming Language :: Python :: *` list.

        NOTE: Will not work after the '3.* -> 4.0'-transition.
        """
        py_min_max = self._python3_min_max()

        return [
            f"Programming Language :: Python :: 3.{r}"
            for r in range(py_min_max[0][1], py_min_max[1][1] + 1)
        ]

    def keywords_list(self) -> List[str]:
        """Get the user-defined keywords as a list."""
        return self.keywords_spaced.strip().split()


def list_to_dangling(lines: List[str], sort: bool = False) -> str:
    """Create a "dangling" multi-line formatted list."""
    return "\n" + "\n".join(sorted(lines) if sort else lines)


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
        self.readme, self.readme_ext = self._get_readme_ext()
        self.version = self._get_version()
        self.development_status = self._get_development_status()

    def _get_package(self) -> str:
        """Find the package."""

        def _get_packages() -> Iterator[str]:
            """This is essentially [options]'s `packages = find:`."""
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

    def _get_readme_ext(self) -> Tuple[str, str]:
        """Return the 'README' file and its extension."""
        for fname in os.listdir(self.root):
            if fname.startswith("README."):
                return fname, fname.split("README.")[1]
        raise Exception(f"No README file found in '{self.root}'")

    def _get_version(self) -> str:
        """Get the package's `__version__` string.

        This is essentially [metadata]'s `version = attr: <module-path to __version__>`.

        `__version__` needs to be parsed as plain text due to potential
        race condition, see:
        https://stackoverflow.com/a/2073599/13156561
        """
        with open(self.pkg_path + "/__init__.py") as f:
            for line in f.readlines():
                if "__version__" in line:
                    # grab "X.Y.Z" from `__version__ = 'X.Y.Z'`
                    # - quote-style insensitive
                    return line.replace('"', "'").split("=")[-1].split("'")[1]

        raise Exception(f"cannot find __version__ in {self.pkg_path}/__init__.py")

    def _get_development_status(self) -> str:
        """Detect the development status from the package's version.

        Known Statuses (**not all are supported**):
            `"Development Status :: 1 - Planning"`
            `"Development Status :: 2 - Pre-Alpha"`
            `"Development Status :: 3 - Alpha"`
            `"Development Status :: 4 - Beta"`
            `"Development Status :: 5 - Production/Stable"`
            `"Development Status :: 6 - Mature"`
            `"Development Status :: 7 - Inactive"`
        """
        if self.version.startswith("0.0.0"):
            return "Development Status :: 2 - Pre-Alpha"
        elif self.version.startswith("0.0."):
            return "Development Status :: 3 - Alpha"
        elif self.version.startswith("0."):
            return "Development Status :: 4 - Beta"
        elif int(self.version.split(".")[0]) >= 1:
            return "Development Status :: 5 - Production/Stable"
        else:
            raise Exception(
                f"Could not figure Development Status for version: {self.version}"
            )


class READMEMarkdownManager:
    """Add some automation to README.md."""

    def __init__(
        self,
        readme: str,
        github_full_repo: str,
        bsec: BuilderSection,
        gh_api: GitHubAPI,
    ) -> None:
        self.readme = readme
        self.github_full_repo = github_full_repo
        self.bsec = bsec
        self.gh_api = gh_api
        with open(readme, "r") as f:
            lines_to_keep = []
            in_badges = False
            for line in f.readlines():
                if line.strip() == REAMDE_BADGES_START_DELIMITER:
                    in_badges = True
                    continue
                if line.strip() == REAMDE_BADGES_END_DELIMITER:
                    in_badges = False
                    continue
                if in_badges:
                    continue
                lines_to_keep.append(line)
        self.lines = self.badges_lines() + lines_to_keep

    def badges_lines(self) -> List[str]:
        """Create and return the lines used to append to a README.md containing various linked-badges."""
        return [
            REAMDE_BADGES_START_DELIMITER,
            "\n",
            f"[![CircleCI](https://img.shields.io/circleci/build/github/{self.github_full_repo})](https://app.circleci.com/pipelines/github/{self.github_full_repo}?branch={self.gh_api.default_branch}&filter=all) ",
            f"[![PyPI](https://img.shields.io/pypi/v/{self.bsec.pypi_name})](https://pypi.org/project/{self.bsec.pypi_name}/) ",
            f"[![GitHub release (latest by date including pre-releases)](https://img.shields.io/github/v/release/{self.github_full_repo}?include_prereleases)]({self.gh_api.url}/) ",
            f"[![PyPI - License](https://img.shields.io/pypi/l/{self.bsec.pypi_name})]({self.gh_api.url}/blob/{self.gh_api.default_branch}/LICENSE) ",
            f"[![Lines of code](https://img.shields.io/tokei/lines/github/{self.github_full_repo})]({self.gh_api.url}/) ",
            f"[![GitHub issues](https://img.shields.io/github/issues/{self.github_full_repo})]({self.gh_api.url}/issues?q=is%3Aissue+sort%3Aupdated-desc+is%3Aopen) ",
            f"[![GitHub pull requests](https://img.shields.io/github/issues-pr/{self.github_full_repo})]({self.gh_api.url}/pulls?q=is%3Apr+sort%3Aupdated-desc+is%3Aopen) ",
            "\n",
            REAMDE_BADGES_END_DELIMITER,
            "\n",
        ]


def _build_out_sections(
    cfg: configparser.ConfigParser, root_path: str, github_full_repo: str
) -> Optional[READMEMarkdownManager]:
    """Build out the `[metadata]`, `[semantic_release]`, and `[options]` sections.

    Return a 'READMEMarkdownManager' instance to write out. If, necessary.
    """

    bsec = BuilderSection(**dict(cfg[BUILDER_SECTION_NAME]))  # checks req/extra fields
    ffile = FromFiles(root_path)  # get things that require reading files
    gh_api = GitHubAPI(github_full_repo)

    # [metadata]
    cfg["metadata"] = {
        "name": bsec.pypi_name,
        "version": f"attr: {ffile.package}.__version__",  # "wipac_dev_tools.__version__"
        "url": gh_api.url,
        "author": AUTHOR,
        "author_email": AUTHOR_EMAIL,
        "description": gh_api.description,
        "long_description": f"file: README.{ffile.readme_ext}",
        "long_description_content_type": long_description_content_type(
            ffile.readme_ext
        ),
        "keywords": list_to_dangling(bsec.keywords_list() + DEFAULT_KEYWORDS),
        "license": LICENSE,
        "classifiers": list_to_dangling(
            [ffile.development_status]
            + ["License :: OSI Approved :: MIT License"]
            + bsec.python_classifiers(),
        ),
    }

    # [semantic_release]
    cfg["semantic_release"] = {
        "version_variable": f"{ffile.package}/__init__.py:__version__",  # "wipac_dev_tools/__init__.py:__version__"
        "upload_to_pypi": "True",
        "patch_without_tag": "True",
        "commit_parser": "semantic_release.history.tag_parser",
        "minor_tag": "[minor]",
        "fix_tag": "[fix]",
        "branch": gh_api.default_branch,
    }

    # [options] -- override/augment specific options
    cfg["options"]["python_requires"] = bsec.python_requires()
    cfg["options"]["packages"] = "find:"  # NOTE: this finds all packages & sub-packages
    if cfg["options"].get("install_requires", fallback=""):
        # sort requirements if they're dangling
        if "\n" in cfg["options"]["install_requires"].strip():
            as_lines = cfg["options"]["install_requires"].strip().split("\n")
            cfg["options"]["install_requires"] = list_to_dangling(as_lines, sort=True)
    else:
        cfg["options"]["install_requires"] = ""

    # [options.package_data] -- add 'py.typed'
    if "py.typed" not in cfg["options.package_data"].get("*", fallback=""):
        if not cfg["options.package_data"].get("*"):
            star_data = "py.typed"
        else:  # append to existing list
            star_data = f"py.typed, {cfg['options.package_data']['*']}"
        cfg["options.package_data"]["*"] = star_data

    # Automate some README stuff
    if ffile.readme_ext == "md":
        return READMEMarkdownManager(ffile.readme, github_full_repo, bsec, gh_api)
    return None


def write_setup_cfg(
    setup_cfg: str, github_full_repo: str
) -> Optional[READMEMarkdownManager]:
    """Build/write the `setup.cfg` sections according to `BUILDER_SECTION_NAME`.

    Return a 'READMEMarkdownManager' instance to write out. If, necessary.
    """
    setup_cfg = os.path.abspath(setup_cfg)

    cfg = configparser.ConfigParser(allow_no_value=True, comment_prefixes="/")
    cfg.read(setup_cfg)
    assert cfg.has_section(BUILDER_SECTION_NAME)  # TODO
    cfg.remove_section("metadata")  # will be overridden
    cfg.remove_section("semantic_release")  # will be overridden
    if not cfg.has_section("options"):  # will only override some fields
        cfg["options"] = {}
    if not cfg.has_section("options.package_data"):  # will only override some fields
        cfg["options.package_data"] = {}

    # NOTE: 'install_requires' (& 'extras_require') are important and shouldn't be overridden
    # NOTE: 'entry_points' is to the user's discretion and isn't touched

    readme_mgr = _build_out_sections(cfg, os.path.dirname(setup_cfg), github_full_repo)

    # Re-order some sections to the top
    tops = [
        BUILDER_SECTION_NAME,
        "metadata",
        "semantic_release",
        "options",
        "options.package_data",
    ]
    # and any 'options.*', if present
    tops.extend(s for s in cfg.sections() if s.startswith("options.") and s not in tops)

    # Build new 'setup.cfg'
    cfg_new = configparser.ConfigParser(allow_no_value=True)
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
        c = c.replace(
            "[options.package_data]", f"[options.package_data]  # {GENERATED_STR}: '*'"
        )
        c = re.sub(r"(\t| )+\n", "\n", c)  # remove trailing whitespace
        print(c)
    with open(setup_cfg, "w") as f:
        f.write(c)

    return readme_mgr


def main(setup_cfg: str, github_full_repo: str) -> None:
    """Read and write all necessary files."""
    # build & write the setup.cfg
    readme_mgr = write_setup_cfg(setup_cfg, github_full_repo)

    # also, write the readme, if necessary
    if readme_mgr:
        with open(readme_mgr.readme, "w") as f:
            for line in readme_mgr.lines:
                f.write(line)


if __name__ == "__main__":

    def _assert_setup_cfg(arg: str) -> str:
        if not (arg.endswith("/setup.cfg") or arg == "setup.cfg"):
            raise ValueError()  # excepted by argparse & formatted nicely
        if not os.path.exists(arg):
            raise FileNotFoundError(arg)
        return arg

    def _assert_github_full_repo(arg: str) -> str:
        if not re.match(r"(\w|-)+/(\w|-)+$", arg):
            raise ValueError()  # excepted by argparse & formatted nicely
        return arg

    parser = argparse.ArgumentParser(
        description=f"Read/transform 'setup.cfg' and 'README.md' files. "
        f"Builds out 'setup.cfg' sections according to [{BUILDER_SECTION_NAME}].",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "setup_cfg_file",
        type=_assert_setup_cfg,
        help="path to the 'setup.cfg' file",
    )
    parser.add_argument(
        "github_full_repo",
        type=_assert_github_full_repo,
        help="Fully-named GitHub repo, ex: WIPACrepo/wipac-dev-tools",
    )
    args = parser.parse_args()
    main(args.setup_cfg_file, args.github_full_repo)
