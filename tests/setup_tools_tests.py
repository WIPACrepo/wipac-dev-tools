"""Unit test setup tools where easily possible."""

import sys
from typing import List, TypedDict

# local imports
sys.path.append(".")
from wipac_dev_tools import setup_tools  # noqa # pylint: disable=E0401,C0413


def test_00_make_keywords() -> None:
    """Test `_make_keywords()`."""

    class _Args(TypedDict):
        description: str
        name: str
        keywords: List[str]

    test_args: List[_Args] = [
        {
            "description": "description",
            "name": "name",
            "keywords": ["description", "name"],
        },
        {
            "description": "all lower case description",
            "name": "name",
            "keywords": ["all_lower_case_description", "name"],
        },
        {
            "description": "description",
            "name": "name_split_by_underscores",
            "keywords": ["description", "name", "split", "by", "underscores"],
        },
        {
            "description": "description",
            "name": "name",
            "keywords": ["description", "name"],
        },
        {
            "description": "description",
            "name": "name",
            "keywords": ["description", "name"],
        },
        {
            "description": "description",
            "name": "name",
            "keywords": ["description", "name"],
        },
    ]

    for args in test_args:
        print(args)
        out = setup_tools.SetupShop._make_keywords(args["description"], args["name"])
        assert out == args["keywords"]
