"""Module to support the `setuptools.setup` utility within `setup.py` files."""


import importlib
import os
import re
import sys
from typing import List, Optional, Tuple

try:
    from typing import TypedDict
except ImportError:  # pre-3.8 support
    from typing_extensions import TypedDict

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
    packages: List[str]
    install_requires: List[str]


class SetupShop:
    """Programmatically construct arguments for use in `setuptools.setup()`.

    This class is not intended to replace `setuptools.setup()`, but
    rather supplement more complex boilerplate code to reduce errors.
    All computation (IO things, compatibility checks, etc.) is done
    up-front in the constructor; so if a SetupShop instance is made,
    you're go to go.

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
    """

    def __init__(
        self,
        package_name: str,
        abspath_to_root: str,
        py_min_max: Tuple[PythonVersion, PythonVersion],
        description: str,
        allow_git_urls: bool = True,
    ):
        py_min, py_max = min(py_min_max), max(py_min_max)

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

        self._version = importlib.import_module(self.name).__version__  # type: ignore[attr-defined]

        # Make Description(s)
        self._description = description
        # include new-lines in long description
        self._long_description = open(os.path.join(self._here, "README.md")).read()

        # Gather Classifiers List
        self._classifiers = SetupShop._get_py_classifiers(py_min, py_max)
        self._classifiers.append(SetupShop._get_development_status(self._version))

        # Parse requirements.txt -> 'install_requires'
        self._install_requires = SetupShop._get_install_requires(
            self._here, self.name, allow_git_urls
        )

    @staticmethod
    def _ensure_python_compatibility(
        name: str, py_min: PythonVersion, py_max: PythonVersion
    ) -> None:
        """If current python version is not compatible, warn and/or exit."""
        if sys.version_info < py_min:
            print(
                f"ERROR: {name} requires at least Python "
                f"{py_min[0]}.{py_min[1]} to run "
                f"( {sys.version_info} < {py_min} )"
            )
            sys.exit(1)
        elif sys.version_info > py_max:
            print(
                f"WARNING: {name} does not officially support Python "
                f"{sys.version_info[0]}.{sys.version_info[1]}+ "
                f"( {sys.version_info} > {py_max} )"
            )

    @staticmethod
    def _find_version(here: str, name: str, init_version_dir: str) -> str:
        """Grab the package's version string."""
        fpath = os.path.join(here, name, init_version_dir, "__init__.py")
        with open(fpath) as init_f:
            for line in init_f.readlines():
                if "__version__" in line:
                    # grab "X.Y.Z" from "__version__ = 'X.Y.Z'" (quote-style insensitive)
                    return line.replace('"', "'").split("=")[-1].split("'")[1]

        raise Exception(f"cannot find `__version__` string in '{fpath}'")

    @staticmethod
    def _get_install_requires(here: str, name: str, allow_git_urls: bool) -> List[str]:
        """Get the `install_requires` list."""
        reqs_txt = "requirements.txt"
        if reqs_txt in os.listdir(here):
            reqs_path = os.path.join(here, reqs_txt)
        elif reqs_txt in os.listdir(os.path.join(here, name)):
            reqs_path = os.path.join(here, name, reqs_txt)
        else:
            raise Exception(
                "'requirements.txt' not found: "
                f"it can either be in '{here}' or '{os.path.join(here, name)}'"
            )
        print(reqs_path)

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
            # PyPI Packages
            else:
                return req.replace("==", ">=")

        return [convert(m) for m in open(reqs_path).read().splitlines()]

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

        return {
            "name": self.name,
            "version": self._version,
            "author": "IceCube Collaboration",
            "author_email": "developers@icecube.wisc.edu",
            "description": self._description,
            "long_description": self._long_description,
            "long_description_content_type": "text/markdown",
            "keywords": keywords,
            "classifiers": sorted(self._classifiers + other_classifiers),
            "packages": SetupShop._get_packages(self.name, subpackages),
            "install_requires": self._install_requires,
        }
