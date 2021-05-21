"""Setup."""

import os

from setuptools import setup  # type: ignore[import]

from wipac_dev_tools import SetupShop

shop = SetupShop(
    "wipac_dev_tools",
    os.path.abspath(os.path.dirname(__file__)),
    ((3, 6), (3, 8)),
    "WIPAC Python Development Tools",
    allow_git_urls=False,
)

setup(
    **shop.get_kwargs(other_classifiers=["License :: OSI Approved :: MIT License"]),
    url="https://github.com/WIPACrepo/wipac-dev-tools",
    license="MIT",
    package_data={shop.name: ["data/www/*", "data/www_templates/*", "py.typed"]},
)
