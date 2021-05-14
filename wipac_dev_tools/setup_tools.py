"""Module to support the `setuptools.setup` utility within `setup.py` files."""


import os
import re
import sys
from typing import List, Optional, Tuple


class SetupShop:
    """Programmatically construct arguments for use in `setuptools.setup()`.

    This class is not intended to replace `setuptools.setup()`, but
    rather supplement more complex boilerplate code to reduce errors.

    Arguments:
        package_name -- the name of your package
        path_to_setup_py -- use: `os.path.abspath(os.path.dirname(__file__))`
        py_min_max -- the min and max supported py release: Ex: `((3,6), (3,8))`
        description -- a one-line description of your package

    Keyword arguments:
        requirements_dir -- a sub-directory containing `requirements.txt` (default: {""})
                            (if `requirements.txt` is in the root, ignore this)
    """

    def __init__(
        self,
        package_name: str,
        path_to_setup_py: str,
        py_min_max: Tuple[Tuple[int, int], Tuple[int, int]],
        description: str,
        requirements_dir: str = "",
    ):
        self.name = package_name
        self.here = path_to_setup_py
        self.py_min = min(py_min_max)
        self.py_max = max(py_min_max)
        self.requirements_path = os.path.join(
            self.here, requirements_dir, "requirements.txt"
        )
        self.version = self._find_version()

        # dicts to be used like: `**this_kwarg`
        self.author_kwargs = {
            "author": "IceCube Collaboration",
            "author_email": "developers@icecube.wisc.edu",
        }
        self.description_kwargs = {
            "description": description,
            # include new-lines
            "long_description": open(os.path.join(self.here, "README.md")).read(),
            "long_description_content_type": "text/markdown",
            "keywords": description.split() + self.name.split(),
        }

        self._ensure_python_competibilty()

    def _ensure_python_competibilty(self) -> None:
        if sys.version_info < self.py_min:
            print(
                f"ERROR: {self.name} requires at least Python "
                f"{self.py_min[0]}.{self.py_min[1]} to run "
                f"( {sys.version_info} < {self.py_min} )"
            )
            sys.exit(1)
        elif sys.version_info > self.py_max:
            print(
                f"WARNING: {self.name} does not officially support Python "
                f"{sys.version_info[0]}.{sys.version_info[1]}+ "
                f"( {sys.version_info} > {self.py_max} )"
            )

    def _find_version(self) -> str:
        """Grab the package's version string."""
        with open(os.path.join(self.here, self.name, "__init__.py")) as init_f:
            for line in init_f.readlines():
                if "__version__" in line:
                    # grab "X.Y.Z" from "__version__ = 'X.Y.Z'" (quote-style insensitive)
                    return line.replace('"', "'").split("=")[-1].split("'")[1]

        raise Exception("cannot find __version__")

    def get_install_requires(self, allow_git_urls: bool = True) -> List[str]:
        """Get the `install_requires` list."""

        def convert(req: str) -> str:
            # GitHub Packages
            if "github.com" in req:
                if not allow_git_urls:
                    raise Exception(
                        "This package cannot contain any git/github url dependencies. "
                        "This is to prevent any circular dependencies. "
                        f"The culprit: {req} from {self.requirements_path}"
                    )
                pat = r"^git\+(?P<url>https://github\.com/[^/]+/[^/]+)@(?P<tag>(v)?\d+\.\d+\.\d+)#egg=(?P<package>\w+)$"
                re_match = re.match(pat, req)
                if not re_match:
                    raise Exception(
                        f"from {self.requirements_path}: "
                        f"pip-install git-package url is not in standardized format {pat} ({req})"
                    )
                groups = re_match.groupdict()
                # point right to .zip (https://stackoverflow.com/a/56635563/13156561)
                return f'{groups["package"]} @ {groups["url"]}/archive/refs/tags/{groups["tag"]}.zip'
            # PyPI Packages
            else:
                return req.replace("==", ">=")

        return [convert(m) for m in open(self.requirements_path).read().splitlines()]

    def _get_py_classifiers(self) -> List[str]:
        """NOTE: Will not work after the '3.* -> 4.0'-transition."""
        if self.py_min[0] < 3:
            raise Exception("Python-classifier automation does not work for python <3.")
        if self.py_max[0] >= 4:
            raise Exception("Python-classifier automation does not work for python 4+.")

        return [
            f"Programming Language :: Python :: 3.{r}"
            for r in range(self.py_min[1], self.py_max[1] + 1)
        ]

    def _get_development_status(self) -> str:
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

    def get_classifiers(
        self, other_classifiers: Optional[List[str]] = None
    ) -> List[str]:
        """Return an aggregated list of classifiers.

        Include Python Language (`Programming Language :: Python :: *`)
        and Development Status (`Development Status :: * - *`) classifiers.
        """
        classifiers = self._get_py_classifiers() + [self._get_development_status()]
        if other_classifiers:
            classifiers.extend(other_classifiers)

        return sorted(classifiers)

    def get_packages(self, subpackages: Optional[List[str]] = None) -> List[str]:
        """Return an aggregated list of packages.

        Optionally, include the given sub-packages now fully-prefixed
        with the main package's name.
        """

        def ensure_full_prefix(sub: str) -> str:
            if sub.startswith(f"{self.name}."):
                return sub
            return f"{self.name}.{sub}"

        pkgs = [self.name]
        if subpackages:
            pkgs.extend(ensure_full_prefix(p) for p in subpackages)

        return pkgs
