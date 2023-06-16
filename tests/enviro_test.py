"""Test enviro_tools.py."""


import os
import pathlib
import shutil
import sys
import tempfile
import unittest
from typing import Any, Dict, FrozenSet, List, Optional, Set, Union

from typing_extensions import Final  # 3.8+ get the real thing
from wipac_dev_tools import (  # noqa # pylint: disable=E0401,C0413
    from_environment,
    from_environment_as_dataclass,
)

if sys.version_info >= (3, 7):
    import dataclasses as dc


# pylint:disable=missing-class-docstring,disallowed-name,invalid-name


class FromEnvironmentTest(unittest.TestCase):
    """Test from_environment()."""

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

    def test_000(self) -> None:
        """Test normal use cases."""
        # str
        os.environ["FOO"] = "foobar"
        config = from_environment({"FOO": "baz"})
        self.assertEqual(config["FOO"], "foobar")

    def test_001(self) -> None:
        """Test normal use case."""
        # Required (No Type / None)
        os.environ["FOO"] = "bar"
        config = from_environment({"FOO": None})
        self.assertEqual(config["FOO"], "bar")

    def test_002(self) -> None:
        """Test normal use case."""
        # int
        os.environ["FOO"] = "543"
        config = from_environment({"FOO": 123})
        self.assertEqual(config["FOO"], 543)
        assert isinstance(config["FOO"], int)

    def test_003(self) -> None:
        """Test normal use case."""
        # float
        os.environ["FOO"] = "543."
        config = from_environment({"FOO": 123.0})
        self.assertEqual(config["FOO"], 543.0)
        assert isinstance(config["FOO"], float)

    def test_004(self) -> None:
        """Test normal use case."""
        # float - from int
        os.environ["FOO"] = "543"
        config = from_environment({"FOO": 123.0})
        self.assertEqual(config["FOO"], 543.0)
        assert isinstance(config["FOO"], float)

    def test_005(self) -> None:
        """Test normal use case."""
        # float - engineering notation
        os.environ["FOO"] = "2e-48"
        config = from_environment({"FOO": 123.0})
        self.assertEqual(config["FOO"], 2e-48)
        assert isinstance(config["FOO"], float)

    def test_006(self) -> None:
        """Test normal use case."""
        # bool - true
        for t in ("y", "yes", "t", "true", "on", "Y", "YES", "T", "TRUE", "ON", "1"):
            os.environ["FOO"] = t
            config = from_environment({"FOO": False})
            self.assertEqual(config["FOO"], True)

    def test_007(self) -> None:
        """Test normal use case."""
        # bool - false
        for f in ("n", "no", "f", "false", "off", "N", "NO", "F", "FALSE", "OFF", "0"):
            os.environ["FOO"] = f
            config = from_environment({"FOO": False})
            self.assertEqual(config["FOO"], False)

    def test_100_error(self) -> None:
        """Test error use case."""
        # Missing
        with self.assertRaises(OSError):
            from_environment({"FOO": None})

    def test_101_error(self) -> None:
        """Test error use case."""
        # Bad Type - int
        os.environ["FOO"] = "123.5"
        with self.assertRaises(ValueError):
            from_environment({"FOO": 123})

    def test_102_error(self) -> None:
        """Test error use case."""
        # Bad Type - float
        os.environ["FOO"] = "1x10^-1"
        with self.assertRaises(ValueError):
            from_environment({"FOO": 123.2})

    def test_103_error(self) -> None:
        """Test error use case."""
        # Bad Type - bool
        for val in ("tru", "nope", "2", "yup", "yeah, no", "no, yeah", "you betcha"):
            os.environ["FOO"] = val
            with self.assertRaises(ValueError):
                from_environment({"FOO": False})

    def test_200_convert(self) -> None:
        """Test conversion cases."""
        # from a string
        os.environ["FOO"] = "BAR"
        config = from_environment("FOO")
        self.assertEqual(config["FOO"], "BAR")
        # from a list
        os.environ["FUBAR"] = "547"
        os.environ["SNAFU"] = "557"
        os.environ["TARFU"] = "563"
        config = from_environment(["FUBAR", "SNAFU", "TARFU"])
        self.assertEqual(config["FUBAR"], "547")
        self.assertEqual(config["SNAFU"], "557")
        self.assertEqual(config["TARFU"], "563")
        # Expected string, list or dict
        with self.assertRaises(TypeError):
            from_environment(None)  # type: ignore


###############################################################################
# PYTHON 3.7+
###############################################################################
if sys.version_info >= (3, 7):

    class FromEnvironmentAsDataclassTest(unittest.TestCase):
        """Test from_environment_as_dataclass()."""

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

        def test__real_life_example(self) -> None:
            """An example of a realistic, robust usage."""

            class EvenState:
                def __init__(self, arg: str):
                    self.is_even = not bool(int(arg) % 2)  # 1%2 -> 1 -> T -> F

            @dc.dataclass(frozen=True)
            class Config:
                FPATH: pathlib.Path
                PORT: int
                HOST: str
                MSGS_PER_CLIENTS: Dict[str, int]
                USE_EVEN: EvenState
                RETRIES: Optional[int] = None
                TIMEOUT: int = 30

                def __post_init__(self) -> None:
                    if self.PORT <= 0:
                        raise ValueError("'PORT' is non-positive")

            os.environ["FPATH"] = "/home/example/path"
            os.environ["PORT"] = "9999"
            os.environ["HOST"] = "localhost"
            os.environ["MSGS_PER_CLIENTS"] = "alpha=0 beta=55 delta=3"
            os.environ["USE_EVEN"] = "22"
            os.environ["RETRIES"] = "3"
            config = from_environment_as_dataclass(Config)
            assert config.FPATH == pathlib.Path("/home/example/path")
            assert config.PORT == 9999
            assert config.HOST == "localhost"
            assert config.MSGS_PER_CLIENTS == {"alpha": 0, "beta": 55, "delta": 3}
            assert config.USE_EVEN.is_even
            assert config.RETRIES == 3
            assert config.TIMEOUT == 30

        def test_000__str(self) -> None:
            """Test normal use case."""
            # str
            @dc.dataclass(frozen=True)
            class Config:
                FOO: str

            os.environ["FOO"] = "foobar"
            config = from_environment_as_dataclass(Config)
            self.assertEqual(config.FOO, "foobar")

        def test_002__int(self) -> None:
            """Test normal use case."""
            # int
            @dc.dataclass(frozen=True)
            class Config:
                FOO: int

            os.environ["FOO"] = "543"
            config = from_environment_as_dataclass(Config)
            self.assertEqual(config.FOO, 543)
            assert isinstance(config.FOO, int)

        def test_003__float(self) -> None:
            """Test normal use case."""
            # float
            @dc.dataclass(frozen=True)
            class Config:
                FOO: float

            os.environ["FOO"] = "543."
            config = from_environment_as_dataclass(Config)
            self.assertEqual(config.FOO, 543.0)
            assert isinstance(config.FOO, float)

        def test_004__float_from_int(self) -> None:
            """Test normal use case."""
            # float - from int
            @dc.dataclass(frozen=True)
            class Config:
                FOO: float

            os.environ["FOO"] = "543"
            config = from_environment_as_dataclass(Config)
            self.assertEqual(config.FOO, 543.0)
            assert isinstance(config.FOO, float)

        def test_005__float_engineering(self) -> None:
            """Test normal use case."""
            # float - engineering notation
            @dc.dataclass(frozen=True)
            class Config:
                FOO: float

            os.environ["FOO"] = "2e-48"
            config = from_environment_as_dataclass(Config)
            self.assertEqual(config.FOO, 2e-48)
            assert isinstance(config.FOO, float)

        def test_006__bool_true(self) -> None:
            """Test normal use case."""
            # bool - true
            @dc.dataclass(frozen=True)
            class Config:
                FOO: bool

            for t in (
                "y",
                "yes",
                "t",
                "true",
                "on",
                "Y",
                "YES",
                "T",
                "TRUE",
                "ON",
                "1",
            ):
                os.environ["FOO"] = t
                config = from_environment_as_dataclass(Config)
                self.assertEqual(config.FOO, True)

        def test_007__bool_false(self) -> None:
            """Test normal use case."""
            # bool - false
            @dc.dataclass(frozen=True)
            class Config:
                FOO: bool

            for f in (
                "n",
                "no",
                "f",
                "false",
                "off",
                "N",
                "NO",
                "F",
                "FALSE",
                "OFF",
                "0",
            ):
                os.environ["FOO"] = f
                config = from_environment_as_dataclass(Config)
                self.assertEqual(config.FOO, False)

        def test_020__list(self) -> None:
            """Test normal use case."""

            @dc.dataclass(frozen=True)
            class Config:
                FOO: list

            os.environ["FOO"] = "foo bar baz"
            config = from_environment_as_dataclass(Config)
            self.assertEqual(config.FOO, ["foo", "bar", "baz"])

        def test_021__list_int(self) -> None:
            """Test normal use case."""

            @dc.dataclass(frozen=True)
            class Config:
                FOO: List[int]

            os.environ["FOO"] = "123 456 789"
            config = from_environment_as_dataclass(Config)
            self.assertEqual(config.FOO, [123, 456, 789])

        def test_022__set(self) -> None:
            """Test normal use case."""

            @dc.dataclass(frozen=True)
            class Config:
                FOO: set

            os.environ["FOO"] = "foo bar baz foo"
            config = from_environment_as_dataclass(Config)
            self.assertEqual(config.FOO, {"bar", "baz", "foo"})

        def test_023__set_int(self) -> None:
            """Test normal use case."""

            @dc.dataclass(frozen=True)
            class Config:
                FOO: Set[int]

            os.environ["FOO"] = "123 456 789 123"
            config = from_environment_as_dataclass(Config)
            self.assertEqual(config.FOO, {123, 456, 789})

        def test_024__dict(self) -> None:
            """Test normal use case."""

            @dc.dataclass(frozen=True)
            class Config:
                FOO: dict

            os.environ["FOO"] = "foo=1 bar=2 baz=3"
            config = from_environment_as_dataclass(Config)
            self.assertEqual(config.FOO, {"bar": "2", "baz": "3", "foo": "1"})

        def test_025__dict_str_int(self) -> None:
            """Test normal use case."""

            @dc.dataclass(frozen=True)
            class Config:
                FOO: Dict[str, int]

            os.environ["FOO"] = "foo=1 bar=2 baz=3"
            config = from_environment_as_dataclass(Config)
            self.assertEqual(config.FOO, {"bar": 2, "baz": 3, "foo": 1})

        def test_026__frozen_set(self) -> None:
            """Test normal use case."""

            @dc.dataclass(frozen=True)
            class Config:
                FOO: frozenset

            os.environ["FOO"] = "foo bar baz foo"
            config = from_environment_as_dataclass(Config)
            self.assertEqual(config.FOO, frozenset({"bar", "baz", "foo"}))

        def test_027__frozen_int(self) -> None:
            """Test normal use case."""

            @dc.dataclass(frozen=True)
            class Config:
                FOO: FrozenSet[int]

            os.environ["FOO"] = "123 456 789 123"
            config = from_environment_as_dataclass(Config)
            self.assertEqual(config.FOO, frozenset({123, 456, 789}))

        def test_028__class(self) -> None:
            """Test normal use case."""

            class OneArgClass:
                def __init__(self, arg: str):
                    self.arg = arg

            @dc.dataclass(frozen=True)
            class Config:
                FOO: OneArgClass

            os.environ["FOO"] = "this is my extra cool string"
            config = from_environment_as_dataclass(Config)
            self.assertEqual(config.FOO.arg, "this is my extra cool string")

        def test_029__dict_class_int(self) -> None:
            """Test normal use case."""

            class OneArgClass:
                def __init__(self, arg: str):
                    self.arg = arg

                def __eq__(self, other: object) -> bool:
                    return isinstance(other, OneArgClass) and self.arg == other.arg

                def __hash__(self) -> int:
                    return hash(self.arg)

            @dc.dataclass(frozen=True)
            class Config:
                FOO: Dict[OneArgClass, int]

            os.environ["FOO"] = "this-is-my-extra-cool-string = 2"
            config = from_environment_as_dataclass(
                Config, dict_kv_joiner=" = ", collection_sep=" | "
            )
            self.assertEqual(
                config.FOO, {OneArgClass("this-is-my-extra-cool-string"): 2}
            )

        def test_050__final_int(self) -> None:
            """Test normal use case."""

            @dc.dataclass(frozen=True)
            class Config:
                FOO: Final[int]  # type: ignore[misc]

            os.environ["FOO"] = "512"
            config = from_environment_as_dataclass(Config)
            self.assertEqual(config.FOO, 512)

        def test_051__final_dict_str_int(self) -> None:
            """Test normal use case."""

            @dc.dataclass(frozen=True)
            class Config:
                FOO: Final[Dict[str, int]]  # type: ignore[misc]

            os.environ["FOO"] = "foo=1 bar=2 baz=3"
            config = from_environment_as_dataclass(Config)
            self.assertEqual(config.FOO, {"bar": 2, "baz": 3, "foo": 1})

        def test_052__optional_bool(self) -> None:
            """Test normal use case."""

            @dc.dataclass(frozen=True)
            class Config:
                FOO: Optional[bool]

            os.environ["FOO"] = "T"
            config = from_environment_as_dataclass(Config)
            self.assertEqual(config.FOO, True)

        def test_053__optional_dict_str_int(self) -> None:
            """Test normal use case."""

            @dc.dataclass(frozen=True)
            class Config:
                FOO: Optional[Dict[str, int]]

            os.environ["FOO"] = "foo=1 bar=2 baz=3"
            config = from_environment_as_dataclass(Config)
            self.assertEqual(config.FOO, {"bar": 2, "baz": 3, "foo": 1})

        def test_054__optional_dict(self) -> None:
            """Test normal use case."""

            @dc.dataclass(frozen=True)
            class Config:
                FOO: Optional[dict]

            os.environ["FOO"] = "foo=1 bar=2 baz=3"
            config = from_environment_as_dataclass(Config)
            self.assertEqual(config.FOO, {"bar": "2", "baz": "3", "foo": "1"})

        def test_070__union_none__int(self) -> None:
            """Test normal use case."""

            @dc.dataclass(frozen=True)
            class Config:
                FOO: Union[None, int]

            os.environ["FOO"] = "1"
            config = from_environment_as_dataclass(Config)
            self.assertEqual(config.FOO, 1)

            del os.environ["FOO"]
            config = from_environment_as_dataclass(Config)
            self.assertEqual(config.FOO, None)

        def test_071__union_none__bool(self) -> None:
            """Test normal use case."""

            @dc.dataclass(frozen=True)
            class Config:
                FOO: Union[None, bool]

            os.environ["FOO"] = "True"
            config = from_environment_as_dataclass(Config)
            self.assertEqual(config.FOO, True)

            del os.environ["FOO"]
            config = from_environment_as_dataclass(Config)
            self.assertEqual(config.FOO, None)

        def test_071__union_none__dict(self) -> None:
            """Test normal use case."""

            @dc.dataclass(frozen=True)
            class Config:
                FOO: Union[None, Dict[str, int]]

            os.environ["FOO"] = "foo=1 bar=2 baz=3"
            config = from_environment_as_dataclass(Config)
            self.assertEqual(config.FOO, {"bar": 2, "baz": 3, "foo": 1})

            del os.environ["FOO"]
            config = from_environment_as_dataclass(Config)
            self.assertEqual(config.FOO, None)

        # TODO: add `|`-tests for py 3.11

        def test_100_error__missing_required(self) -> None:
            """Test error use case."""
            # Missing
            @dc.dataclass(frozen=True)
            class Config:
                FOO: bool

            with self.assertRaises(OSError):
                from_environment_as_dataclass(Config)

        def test_101_error__int(self) -> None:
            """Test error use case."""
            # Bad Type - int
            @dc.dataclass(frozen=True)
            class Config:
                FOO: int

            os.environ["FOO"] = "123.5"
            with self.assertRaises(ValueError):
                from_environment_as_dataclass(Config)

        def test_102_error__float(self) -> None:
            """Test error use case."""
            # Bad Type - float
            @dc.dataclass(frozen=True)
            class Config:
                FOO: float

            os.environ["FOO"] = "1x10^-1"
            with self.assertRaises(ValueError):
                from_environment_as_dataclass(Config)

        def test_103_error__bool(self) -> None:
            """Test error use case."""

            @dc.dataclass(frozen=True)
            class Config:
                FOO: bool

            # Bad Type - bool
            for val in (
                "tru",
                "nope",
                "2",
                "yup",
                "yeah, no",
                "no, yeah",
                "you betcha",
            ):
                os.environ["FOO"] = val
                with self.assertRaises(ValueError):
                    from_environment_as_dataclass(Config)

        def test_104_error__bytes(self) -> None:
            """Test error use case."""
            # using a bytes, this is similar to any multi-arg built-in type
            @dc.dataclass(frozen=True)
            class Config:
                FOO: bytes = bytes()

            os.environ["FOO"] = "foo bar baz"
            with self.assertRaises(TypeError):
                from_environment_as_dataclass(Config)

        def test_105_error__overly_nested_type_alias(self) -> None:
            """Test error use case."""
            # using a bytes, this is similar to any multi-arg built-in type
            @dc.dataclass(frozen=True)
            class Config:
                FOO: List[Dict[str, int]]

            os.environ["FOO"] = "doesn't matter, this won't get read before error"
            with self.assertRaises(ValueError) as cm:
                from_environment_as_dataclass(Config)
            assert str(cm.exception) == (
                "'typing.List[typing.Dict[str, int]]' is not a "
                "supported type: field='FOO' (the typing-module's alias types "
                "must resolve to 'type' within 1 nesting, or 2 if using "
                "'Final' or 'Optional')"
            )

        def test_106__dict_delims(self) -> None:
            """Test error use case."""

            @dc.dataclass(frozen=True)
            class Config:
                FOO: Dict[str, int]

            os.environ["FOO"] = "this-is-my-extra-cool-string = 2"
            with self.assertRaises(RuntimeError) as cm:
                from_environment_as_dataclass(Config, dict_kv_joiner=" = ")
            assert str(cm.exception) == (
                r"'collection_sep' ('None'='\s+') cannot overlap with "
                "'dict_kv_joiner': 'None' & ' = '"
            )

        def test_107__dict_delims(self) -> None:
            """Test error use case."""

            @dc.dataclass(frozen=True)
            class Config:
                FOO: Dict[str, int]

            os.environ["FOO"] = "this-is-my-extra-cool-string = 2"
            with self.assertRaises(RuntimeError) as cm:
                from_environment_as_dataclass(
                    Config, dict_kv_joiner=" = ", collection_sep=" "
                )
            assert str(cm.exception) == (
                r"'collection_sep' ('None'='\s+') cannot overlap with "
                "'dict_kv_joiner': ' ' & ' = '"
            )

        def test_108_error__bytes(self) -> None:
            """Test error use case."""

            @dc.dataclass(frozen=True)
            class Config:
                FOO: bytes

            os.environ["FOO"] = "foo bar baz"
            with self.assertRaises(TypeError):
                from_environment_as_dataclass(Config)

        # NOTE: mypy crashes with an un-typed non-initialized 'Final'
        # see https://github.com/python/mypy/issues/10090
        # def test_109_error__final_only(self) -> None:
        #     """Test error use case."""

        #     @dc.dataclass(frozen=True)
        #     class Config:
        #         FOO: Final  # type: ignore[misc] # ...this is an error after all

        #     os.environ["FOO"] = "foo bar baz"
        #     with self.assertRaises(ValueError):
        #         from_environment_as_dataclass(Config)

        def test_110_error__any(self) -> None:
            """Test error use case."""

            @dc.dataclass(frozen=True)
            class Config:
                FOO: Any

            os.environ["FOO"] = "foo bar baz"
            with self.assertRaises(ValueError):
                from_environment_as_dataclass(Config)

        def test_170__union__not_none_2tuple(self) -> None:
            """Test error use case."""

            @dc.dataclass(frozen=True)
            class Config:
                FOO: Union[int, bool]

            with self.assertRaises(TypeError):
                from_environment_as_dataclass(Config)

        def test_171__union__not_none_2tuple(self) -> None:
            """Test error use case."""

            @dc.dataclass(frozen=True)
            class Config:
                FOO: Union[int, str]

            with self.assertRaises(TypeError):
                from_environment_as_dataclass(Config)

        # TODO: add `|`-tests for py 3.11

        def test_171__union__not_none_2tuple(self) -> None:
            """Test error use case."""

            @dc.dataclass(frozen=True)
            class Config:
                FOO: Union[None, int, str]

            with self.assertRaises(TypeError):
                from_environment_as_dataclass(Config)

        def test_200_convert(self) -> None:
            """Test conversion cases."""
            with self.assertRaises(TypeError):
                from_environment_as_dataclass(None)  # type: ignore

            @dc.dataclass(frozen=True)
            class Config:
                FOO: bool = True

            with self.assertRaises(TypeError):
                from_environment_as_dataclass(Config())  # type: ignore

        def test_300_post_init__int_range(self) -> None:
            """Test post-init processing."""

            @dc.dataclass(frozen=True)
            class Config:
                FOO: int

                def __post_init__(self) -> None:
                    if self.FOO <= 0:
                        raise ValueError("'FOO' is non-positive")

            os.environ["FOO"] = "-123456"
            with self.assertRaises(ValueError):
                from_environment_as_dataclass(Config)


###############################################################################
# PYTHON <3.7
###############################################################################
else:

    class FromEnvironmentAsDataclassTest(unittest.TestCase):
        """Test from_environment_as_dataclass()."""

        def test_000(self) -> None:
            """Test normal use case."""
            with self.assertRaises(NotImplementedError):
                from_environment_as_dataclass(object)  # arg doesn't matter
