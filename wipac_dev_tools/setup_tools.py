"""DEPRECATED: Module to support the `setuptools.setup` utility within `setup.py` files."""


import os
import pprint
import re
import sys
from typing import List, Optional, Tuple, TypedDict

PythonVersion = Tuple[int, int]


class SetupShopKwargs(TypedDict):
    """The auto-created kwargs for `setuptools.setup()`."""

    name: str
    version: str
    author: str
    author_email: str
    description: str
    long_description: str
    long_description_content_type: str
    keywords: List[str]
    classifiers: List[str]
    license: str
    packages: List[str]
    install_requires: List[str]


class SetupShop:
    """Programmatically construct arguments for use in `setuptools.setup()`.

    This class is not intended to replace `setuptools.setup()`, but
    rather supplement more complex boilerplate code to reduce errors.
    All computation (IO things, compatibility checks, etc.) is done
    up-front in the constructor; so if a SetupShop instance is made,
    you're go to go.

    All required packages (`install_requires` list) are found by parsing
    `requirements.txt`. PyPI packages are assumed to be backwards-
    compatible, so these use the indicated version as a *MINIMAL*
    requirement (`==` is replaced with `>=`; this can be turned off by
    adding each package to `pinned_packages`). Conversely, GitHub-URL
    packages ARE pinned to their indicated version/tag. These packages
    are re-parsed to point to the standard `.zip` file/url.

    Example:
        `shop = SetupShop(...)`
        `setuptools.setup(..., **shop.get_kwargs(...))`

    Arguments:
        package_name -- the name of your package
        abspath_to_root -- use: `os.path.abspath(os.path.dirname(__file__))`
        py_min_max -- the min and max supported python releases: Ex: `((3,6), (3,8))`
        description -- a one-line description of your package

    Keyword arguments:
        allow_git_urls -- whether to allow github URLs in `install_requires` list
        pinned_packages -- packages to pin with version indicated in `requirements.txt`
                             (does not auto-upgrade package version)
    """

    def __init__(
        self,
        package_name: str,
        abspath_to_root: str,
        py_min_max: Tuple[PythonVersion, PythonVersion],
        description: str,
        allow_git_urls: bool = True,
        pinned_packages: Optional[List[str]] = None,
    ):
        print(  # DEPRECATION WARNING
            "\033[93m"
            + "\033[1m"
            + "SetupShop is deprecated. Use GH Action: WIPACrepo/wipac-dev-py-setup-action"
            + "\033[0m"
        )

        py_min, py_max = SetupShop._get_py_min_max(py_min_max)

        if not re.match(r"\w+$", package_name):
            raise Exception(f"Package name contains illegal characters: {package_name}")
        self.name = package_name

        # Before anything else, check that the current python version is okay
        SetupShop._ensure_python_compatibility(self.name, py_min, py_max)

        if not abspath_to_root.startswith("/"):
            raise Exception(
                f"Path is not absolute: `{abspath_to_root}`; "
                "use: `os.path.abspath(os.path.dirname(__file__))`"
            )
        self._here = abspath_to_root

        self._version = SetupShop._get_version(self._here, self.name)
        print(f"SetupShop --> version: {self._version}")

        # Make Description(s)
        self._description = description
        # include new-lines in long description
        try:
            self._readme = os.path.join(self._here, "README.md")
            self._long_description = open(self._readme).read()
        except FileNotFoundError:
            self._readme = os.path.join(self._here, "README.rst")
            self._long_description = open(self._readme).read()
        print(
            f"SetupShop --> long_description: {len(self._long_description.splitlines())} lines "
            f"(from {self._readme})"
        )

        # Gather Classifiers List
        self._classifiers = SetupShop._get_py_classifiers(py_min, py_max)
        self._classifiers.append(SetupShop._get_development_status(self._version))
        for pyc in self._classifiers:
            print(f"SetupShop --> classifier: '{pyc}'")

        # Parse requirements.txt -> 'install_requires'
        self._install_requires, req_path = SetupShop._get_install_requires(
            self._here,
            self.name,
            allow_git_urls,
            pinned_packages if pinned_packages else [],
        )
        print(
            f"SetupShop --> install_requires: {len(self._install_requires)} packages "
            f"(from {req_path})"
        )

        print()

    @staticmethod
    def _get_py_min_max(
        py_min_max: Tuple[PythonVersion, PythonVersion]
    ) -> Tuple[PythonVersion, PythonVersion]:
        """Check that the given `get_py_min_max` is valid, then return."""
        if (
            len(py_min_max) != 2
            or py_min_max[0] > py_min_max[1]
            or any(len(p) != 2 for p in py_min_max)
        ):
            raise Exception(
                "'py_min_max' must be a 2-tuple of non-decreasing 2-tuples; "
                "examples: `((3,6),(3,8))` or `((3,6),(3,6))`"
            )
        return py_min_max

    @staticmethod
    def _ensure_python_compatibility(
        name: str, py_min: PythonVersion, py_max: PythonVersion
    ) -> None:
        """If current python version is not compatible, warn and/or exit."""
        current = (sys.version_info.major, sys.version_info.minor)  # ignore micro

        if current < py_min:  # Ex: 3.5.2 < 3.5
            raise Exception(
                f"{name} requires at least Python "
                f"{py_min[0]}.{py_min[1]} to run "
                f"(current={current})"
            )
        elif current > py_max:  # ignore micro
            print(
                f"WARNING: {name} does not officially support Python "
                f"{current[0]}.{current[1]}+ "
                f"(max={py_max})"
            )

    @staticmethod
    def _find_file(here: str, pkg_name: str, fname: str) -> str:
        """Find the file `fname` and return its path."""
        # check 'here'
        if fname in os.listdir(here):
            return os.path.join(here, fname)
        # check 'here/pkg_name'
        elif fname in os.listdir(os.path.join(here, pkg_name)):
            return os.path.join(here, pkg_name, fname)
        else:
            raise FileNotFoundError(
                f"'{fname}' not found: "
                f"it can either be in '{here}' or '{os.path.join(here, pkg_name)}'"
            )

    @staticmethod
    def _get_version(here: str, name: str) -> str:
        """Get the package's `__version__` string.

        `__version__` needs to be parsed as plain text due to potential
        race condition, see:
        https://stackoverflow.com/a/2073599/13156561
        """
        init_path = SetupShop._find_file(here, name, "__init__.py")

        with open(init_path) as f:
            for line in f.readlines():
                if "__version__" in line:
                    # grab "X.Y.Z" from `__version__ = 'X.Y.Z'`
                    # - quote-style insensitive
                    return line.replace('"', "'").split("=")[-1].split("'")[1]

        raise Exception(
            f"cannot find __version__ in lowest-level __init__.py ({init_path})"
        )

    @staticmethod
    def _get_install_requires(
        here: str, name: str, allow_git_urls: bool, pinned_packages: List[str]
    ) -> Tuple[List[str], str]:
        """Get the `install_requires` list & the path to requirements.txt."""
        reqs_path = SetupShop._find_file(here, name, "requirements.txt")

        def parse_package_name(req: str) -> str:
            # https://www.python.org/dev/peps/pep-0508/#names
            rematch = re.match(r"^[A-Za-z0-9._-]+", req)
            if not rematch:
                raise Exception(f"Malformed package requirement line: '{req}'")
            return rematch.group(0)

        def convert(req: str) -> str:
            # GitHub Packages
            if "github.com" in req:
                if not allow_git_urls:
                    raise Exception(
                        "This package cannot contain any git/github url dependencies. "
                        "This is to prevent any circular dependencies. "
                        f"The culprit: {req} from {reqs_path}"
                    )
                pat = r"^git\+(?P<url>https://github\.com/[^/]+/[^/]+)@(?P<tag>(v)?\d+\.\d+\.\d+)#egg=(?P<package>\w+)$"
                re_match = re.match(pat, req)
                if not re_match:
                    raise Exception(
                        f"from {reqs_path}: "
                        f"pip-install git-package url is not in standardized format {pat} ({req})"
                    )
                groups = re_match.groupdict()
                # point right to .zip (https://stackoverflow.com/a/56635563/13156561)
                return f'{groups["package"]} @ {groups["url"]}/archive/refs/tags/{groups["tag"]}.zip'
            # PyPI Packages: my-package==5.6.7
            else:
                if parse_package_name(req) in pinned_packages:
                    return req
                return req.replace("==", ">=")

        return [convert(m) for m in open(reqs_path).read().splitlines()], reqs_path

    @staticmethod
    def _get_py_classifiers(py_min: PythonVersion, py_max: PythonVersion) -> List[str]:
        """Get auto-detected `Programming Language :: Python :: *` list.

        NOTE: Will not work after the '3.* -> 4.0'-transition.
        """
        if py_min[0] < 3:
            raise Exception("Python-classifier automation does not work for python <3.")
        if py_max[0] >= 4:
            raise Exception("Python-classifier automation does not work for python 4+.")

        return [
            f"Programming Language :: Python :: 3.{r}"
            for r in range(py_min[1], py_max[1] + 1)
        ]

    @staticmethod
    def _get_development_status(version: str) -> str:
        """Detect the development status from the package's version.

        Known Statuses (not all are supported by `SetupShop`):
            `"Development Status :: 1 - Planning"`
            `"Development Status :: 2 - Pre-Alpha"`
            `"Development Status :: 3 - Alpha"`
            `"Development Status :: 4 - Beta"`
            `"Development Status :: 5 - Production/Stable"`
            `"Development Status :: 6 - Mature"`
            `"Development Status :: 7 - Inactive"`
        """
        if version.startswith("0.0.0"):
            return "Development Status :: 2 - Pre-Alpha"
        elif version.startswith("0.0."):
            return "Development Status :: 3 - Alpha"
        elif version.startswith("0."):
            return "Development Status :: 4 - Beta"
        elif int(version.split(".")[0]) >= 1:
            return "Development Status :: 5 - Production/Stable"
        else:
            raise Exception(
                f"Could not figure Development Status for version: {version}"
            )

    @staticmethod
    def _get_packages(name: str, subpackages: Optional[List[str]]) -> List[str]:
        """Return an aggregated list of packages.

        Optionally, include the given sub-packages now fully-prefixed
        with the main package's name.
        """

        def ensure_full_prefix(sub: str) -> str:
            if sub.startswith(f"{name}."):
                return sub
            return f"{name}.{sub}"

        pkgs = [name]
        if subpackages:
            pkgs.extend(ensure_full_prefix(p) for p in subpackages)

        return pkgs

    def get_kwargs(
        self,
        other_classifiers: Optional[List[str]] = None,
        subpackages: Optional[List[str]] = None,
    ) -> SetupShopKwargs:
        """Return a dict of auto-created arguments for `setuptools.setup()`.

        Simply collate already auto-created attributes with optionally
        given keyword arguments. Apply like: `setup(..., **shop.get_kwargs())`

        NOTE: There should be no exceptions raised.
        """
        keywords = self._description.split() + self.name.split("_")

        if not other_classifiers:
            other_classifiers = []

        if self._readme.endswith(".md"):
            long_description_content_type = "text/markdown"
        elif self._readme.endswith(".rst"):
            long_description_content_type = "text/x-rst"
        else:
            long_description_content_type = "text/plain"

        kwargs: SetupShopKwargs = {
            "name": self.name,
            "version": self._version,
            "author": "IceCube Collaboration",
            "author_email": "developers@icecube.wisc.edu",
            "description": self._description,
            "long_description": self._long_description,
            "long_description_content_type": long_description_content_type,
            "keywords": keywords,
            "classifiers": sorted(
                self._classifiers
                + other_classifiers
                + ["License :: OSI Approved :: MIT License"]
            ),
            "license": "MIT",
            "packages": SetupShop._get_packages(self.name, subpackages),
            "install_requires": self._install_requires,
        }

        print("SetupShop Kwargs...")
        pprint.pprint(kwargs)
        print()
        return kwargs
