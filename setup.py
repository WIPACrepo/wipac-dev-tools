"""Setup."""

import os

from setuptools import setup  # type: ignore[import]

from wipac_dev_tools import SetupShop

setupshop = SetupShop(
    "wipac_dev_tools",
    os.path.abspath(os.path.dirname(__file__)),
    ((3, 6), (3, 8)),
    "WIPAC Python Development Tools",
)

setup(
    name=setupshop.name,
    version=setupshop.version,
    **setupshop.author_kwargs,
    **setupshop.description_kwargs,
    url="https://github.com/WIPACrepo/wipac-dev-tools",
    license="MIT",
    classifiers=setupshop.get_classifiers(["License :: OSI Approved :: MIT License"]),
    packages=setupshop.get_packages(),
    install_requires=setupshop.get_install_requires(allow_git_urls=False),
    package_data={setupshop.name: ["data/www/*", "data/www_templates/*", "py.typed"]},
)
