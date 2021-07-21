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
        # TEST BASIC DESCRIPTION PARSING
        {
            "description": "Upper Description",
            "name": "name",
            "keywords": ["Upper", "Description", "Upper Description", "name"],
        },
        {  # removes unimportant words
            "description": "not all lower case Description",
            "name": "name",
            "keywords": ["Description", "name"],
        },
        #
        # TEST DESCRIPTION UPPER'ING
        {  # if the entire description is lower case, initialize each word first
            "description": "all lower description for 5",
            "name": "name",
            "keywords": [
                "All Lower Description For 5",
                "All",
                "Lower",
                "Description",
                "For",
                "5",
                "name",
            ],
        },
        #
        # TEST NAME SPLITTING
        {
            "description": "description",
            "name": "name_split_by_underscores",
            "keywords": ["name", "split", "by", "underscores", "Description"],
        },
        #
        # TEST DESCRIPTION SUB-STRING SPLITTING
        {  # removes unimportant words
            "description": "Description Sub-string and Green 5am",
            "name": "name",
            "keywords": [
                "Description",
                "Sub-string",
                "Green",
                "5am",
                "Description Sub-string",
                "Green 5am",
                "name",
            ],
        },
        #
        #
        # REALISTIC EXAMPLES
        {
            "description": "Module for Parsing Setup Utilities",
            "name": "wipac_dev_tools",
            "keywords": [
                "Module",
                "Parsing",
                "Parsing Setup Utilities",
                "Setup",
                "Utilities",
                "dev",
                "tools",
                "wipac",
            ],
        },
        {
            "description": "WIPAC Python Development Tools",
            "name": "wipac_dev_tools",
            "keywords": [
                "WIPAC",
                "Python",
                "WIPAC Python Development Tools",
                "Development",
                "Tools",
                "dev",
                "tools",
                "wipac",
            ],
        },
        {
            "description": "Message Queue Client API with Google Cloud Platform (GCP)",
            "name": "mqclient_gcp",
            "keywords": [
                "mqclient",
                "gcp",
                "Message Queue Client API",
                "Google Cloud Platform (GCP)",
                "Message",
                "Queue",
                "Client",
                "API",
                "Google",
                "Cloud",
                "Platform",
                "GCP",
            ],
        },
    ]

    for args in test_args:
        print(args)
        out = setup_tools.SetupShop._make_keywords(args["description"], args["name"])
        assert out == sorted(args["keywords"])
