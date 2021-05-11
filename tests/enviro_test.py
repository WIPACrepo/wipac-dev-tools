"""Test enviro_tools.py."""


import os
import shutil
import sys
import tempfile
import unittest

# local imports
sys.path.append(".")
from wipac_dev_tools import from_environment  # noqa # pylint: disable=E0401,C0413


class EnviroToolsTest(unittest.TestCase):
    """Test enviro_tools.py."""

    def setUp(self):
        super().setUp()
        self.test_dir = tempfile.mkdtemp(dir=os.getcwd())

        def cleanup():
            shutil.rmtree(self.test_dir)

        self.addCleanup(cleanup)
        environ = os.environ.copy()

        def clean_env():
            for k in list(os.environ):
                if k not in environ:
                    del os.environ[k]

        self.addCleanup(clean_env)

    def test_00_from_environment(self) -> None:
        """Test normal use cases."""
        # str
        os.environ["FOO"] = "foobar"
        config = from_environment({"FOO": "baz"})
        self.assertEqual(config["FOO"], "foobar")

        # No Type / None
        os.environ["FOO"] = "bar"
        config = from_environment({"FOO": None})
        self.assertEqual(config["FOO"], "bar")

        # int
        os.environ["FOO"] = "543"
        config = from_environment({"FOO": 123})
        self.assertEqual(config["FOO"], 543)
        assert isinstance(config["FOO"], int)

        # float
        os.environ["FOO"] = "543."
        config = from_environment({"FOO": 123.0})
        self.assertEqual(config["FOO"], 543.0)
        assert isinstance(config["FOO"], float)

        # float - from int
        os.environ["FOO"] = "543"
        config = from_environment({"FOO": 123.0})
        self.assertEqual(config["FOO"], 543.0)
        assert isinstance(config["FOO"], float)

        # float - engineering notation
        os.environ["FOO"] = "2e-48"
        config = from_environment({"FOO": 123.0})
        self.assertEqual(config["FOO"], 2e-48)
        assert isinstance(config["FOO"], float)

        # bool - true
        for t in ("y", "yes", "t", "true", "on", "Y", "YES", "T", "TRUE", "ON", "1"):
            os.environ["FOO"] = t
            config = from_environment({"FOO": False})
            self.assertEqual(config["FOO"], True)

        # bool - false
        for f in ("n", "no", "f", "false", "off", "N", "NO", "F", "FALSE", "OFF", "0"):
            os.environ["FOO"] = f
            config = from_environment({"FOO": False})
            self.assertEqual(config["FOO"], False)

    def test_01_from_environment_errors(self) -> None:
        """Test error use cases."""
        # Missing
        with self.assertRaises(OSError):
            from_environment({"FOO": None})

        # Bad Type - int
        os.environ["FOO"] = "123.5"
        with self.assertRaises(ValueError):
            from_environment({"FOO": 123})

        # Bad Type - float
        os.environ["FOO"] = "1x10^-1"
        with self.assertRaises(ValueError):
            from_environment({"FOO": 123.2})

        # Bad Type - bool
        for val in ("tru", "nope", "2", "yup", "yeah, no", "no, yeah", "you betcha"):
            with self.assertRaises(ValueError):
                os.environ["FOO"] = val
                from_environment({"FOO": False})
