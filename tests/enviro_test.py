"""Test enviro_tools.py."""

import dataclasses as dc
import os
import pathlib
import shutil
import sys
import tempfile
import unittest
from typing import Any, Dict, FrozenSet, List, Optional, Set, Union

import pytest
from typing_extensions import Final

from wipac_dev_tools import (  # noqa
    from_environment,
    from_environment_as_dataclass,
)


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


########################################################################################
# Test from_environment_as_dataclass()


@pytest.fixture()
def isolated_env():
    test_dir = tempfile.mkdtemp(dir=os.getcwd())

    def cleanup():
        shutil.rmtree(test_dir)

    environ = os.environ.copy()

    def clean_env():
        for k in list(os.environ):
            if k not in environ:
                del os.environ[k]

    yield
    cleanup()
    clean_env()


@pytest.mark.usefixtures("isolated_env")
def test__real_life_example() -> None:
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


@pytest.mark.usefixtures("isolated_env")
def test_000__str() -> None:
    """Test normal use case."""

    # str
    @dc.dataclass(frozen=True)
    class Config:
        FOO: str

    os.environ["FOO"] = "foobar"
    config = from_environment_as_dataclass(Config)
    assert config.FOO == "foobar"


@pytest.mark.usefixtures("isolated_env")
def test_002__int() -> None:
    """Test normal use case."""

    # int
    @dc.dataclass(frozen=True)
    class Config:
        FOO: int

    os.environ["FOO"] = "543"
    config = from_environment_as_dataclass(Config)
    assert config.FOO == 543
    assert isinstance(config.FOO, int)


@pytest.mark.usefixtures("isolated_env")
def test_003__float() -> None:
    """Test normal use case."""

    # float
    @dc.dataclass(frozen=True)
    class Config:
        FOO: float

    os.environ["FOO"] = "543."
    config = from_environment_as_dataclass(Config)
    assert config.FOO == 543.0
    assert isinstance(config.FOO, float)


@pytest.mark.usefixtures("isolated_env")
def test_004__float_from_int() -> None:
    """Test normal use case."""

    # float - from int
    @dc.dataclass(frozen=True)
    class Config:
        FOO: float

    os.environ["FOO"] = "543"
    config = from_environment_as_dataclass(Config)
    assert config.FOO == 543.0
    assert isinstance(config.FOO, float)


@pytest.mark.usefixtures("isolated_env")
def test_005__float_engineering() -> None:
    """Test normal use case."""

    # float - engineering notation
    @dc.dataclass(frozen=True)
    class Config:
        FOO: float

    os.environ["FOO"] = "2e-48"
    config = from_environment_as_dataclass(Config)
    assert config.FOO == 2e-48
    assert isinstance(config.FOO, float)


@pytest.mark.usefixtures("isolated_env")
def test_006__bool_true() -> None:
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
        assert config.FOO is True


@pytest.mark.usefixtures("isolated_env")
def test_007__bool_false() -> None:
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
        assert config.FOO is False


@pytest.mark.usefixtures("isolated_env")
def test_020__list() -> None:
    """Test normal use case."""

    @dc.dataclass(frozen=True)
    class Config:
        FOO: list

    os.environ["FOO"] = "foo bar baz"
    config = from_environment_as_dataclass(Config)
    assert config.FOO == ["foo", "bar", "baz"]


@pytest.mark.parametrize(
    "typo",
    [
        List[int],
        list[int],
    ],
)
@pytest.mark.usefixtures("isolated_env")
def test_021__list_int(typo) -> None:
    """Test normal use case."""

    @dc.dataclass(frozen=True)
    class Config:
        FOO: typo  # type: ignore

    os.environ["FOO"] = "123 456 789"
    config = from_environment_as_dataclass(Config)
    assert config.FOO == [123, 456, 789]


@pytest.mark.usefixtures("isolated_env")
def test_022__set() -> None:
    """Test normal use case."""

    @dc.dataclass(frozen=True)
    class Config:
        FOO: set

    os.environ["FOO"] = "foo bar baz foo"
    config = from_environment_as_dataclass(Config)
    assert config.FOO == {"bar", "baz", "foo"}


@pytest.mark.parametrize(
    "typo",
    [
        Set[int],
        set[int],
    ],
)
@pytest.mark.usefixtures("isolated_env")
def test_023__set_int(typo) -> None:
    """Test normal use case."""

    @dc.dataclass(frozen=True)
    class Config:
        FOO: typo  # type: ignore

    os.environ["FOO"] = "123 456 789 123"
    config = from_environment_as_dataclass(Config)
    assert config.FOO == {123, 456, 789}


@pytest.mark.usefixtures("isolated_env")
def test_024__dict() -> None:
    """Test normal use case."""

    @dc.dataclass(frozen=True)
    class Config:
        FOO: dict

    os.environ["FOO"] = "foo=1 bar=2 baz=3"
    config = from_environment_as_dataclass(Config)
    assert config.FOO == {"bar": "2", "baz": "3", "foo": "1"}


@pytest.mark.parametrize(
    "typo",
    [
        Dict[str, int],
        dict[str, int],
    ],
)
@pytest.mark.usefixtures("isolated_env")
def test_025__dict_str_int(typo) -> None:
    """Test normal use case."""

    @dc.dataclass(frozen=True)
    class Config:
        FOO: typo  # type: ignore

    os.environ["FOO"] = "foo=1 bar=2 baz=3"
    config = from_environment_as_dataclass(Config)
    assert config.FOO == {"bar": 2, "baz": 3, "foo": 1}


@pytest.mark.usefixtures("isolated_env")
def test_026__frozen_set() -> None:
    """Test normal use case."""

    @dc.dataclass(frozen=True)
    class Config:
        FOO: frozenset

    os.environ["FOO"] = "foo bar baz foo"
    config = from_environment_as_dataclass(Config)
    assert config.FOO == frozenset({"bar", "baz", "foo"})


@pytest.mark.parametrize(
    "typo",
    [
        FrozenSet[int],
        frozenset[int],
    ],
)
@pytest.mark.usefixtures("isolated_env")
def test_027__frozen_int(typo) -> None:
    """Test normal use case."""

    @dc.dataclass(frozen=True)
    class Config:
        FOO: typo  # type: ignore

    os.environ["FOO"] = "123 456 789 123"
    config = from_environment_as_dataclass(Config)
    assert config.FOO == frozenset({123, 456, 789})


@pytest.mark.usefixtures("isolated_env")
def test_028__class() -> None:
    """Test normal use case."""

    class OneArgClass:
        def __init__(self, arg: str):
            self.arg = arg

    @dc.dataclass(frozen=True)
    class Config:
        FOO: OneArgClass

    os.environ["FOO"] = "this is my extra cool string"
    config = from_environment_as_dataclass(Config)
    assert config.FOO.arg == "this is my extra cool string"


@pytest.mark.usefixtures("isolated_env")
def test_029__dict_class_int() -> None:
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
    assert config.FOO == {OneArgClass("this-is-my-extra-cool-string"): 2}


@pytest.mark.usefixtures("isolated_env")
def test_050__final_int() -> None:
    """Test normal use case."""

    @dc.dataclass(frozen=True)
    class Config:
        FOO: Final[int]  # type: ignore[misc]

    os.environ["FOO"] = "512"
    config = from_environment_as_dataclass(Config)
    assert config.FOO == 512


@pytest.mark.usefixtures("isolated_env")
def test_051__final_dict_str_int() -> None:
    """Test normal use case."""

    @dc.dataclass(frozen=True)
    class Config:
        FOO: Final[Dict[str, int]]  # type: ignore[misc]

    os.environ["FOO"] = "foo=1 bar=2 baz=3"
    config = from_environment_as_dataclass(Config)
    assert config.FOO == {"bar": 2, "baz": 3, "foo": 1}


if sys.version_info >= (3, 10):
    # this trips up the py <3.9 interpreter
    extra_params = [
        bool | None,
        None | bool,
    ]
else:
    extra_params = []  # type: ignore[var-annotated]


@pytest.mark.parametrize(
    "typo",
    [
        Optional[bool],
        Union[bool, None],
        Union[None, bool],
    ]
    + extra_params,  # type: ignore
)
@pytest.mark.usefixtures("isolated_env")
def test_060__optional_bool(typo) -> None:
    """Test normal use case."""

    @dc.dataclass(frozen=True)
    class Config:
        FOO: typo  # type: ignore

    os.environ["FOO"] = "T"
    config = from_environment_as_dataclass(Config)
    assert config.FOO is True


if sys.version_info >= (3, 10):
    # this trips up the py <3.9 interpreter
    extra_params = [
        Dict[str, int] | None,
        None | Dict[str, int],
    ]
else:
    extra_params = []


@pytest.mark.parametrize(
    "typo",
    [
        Optional[Dict[str, int]],
        Union[Dict[str, int], None],
        Union[None, Dict[str, int]],
    ]
    + extra_params,  # type: ignore
)
@pytest.mark.usefixtures("isolated_env")
def test_061__optional_dict_str_int(typo) -> None:
    """Test normal use case."""

    @dc.dataclass(frozen=True)
    class Config:
        FOO: typo  # type: ignore

    os.environ["FOO"] = "foo=1 bar=2 baz=3"
    config = from_environment_as_dataclass(Config)
    assert config.FOO == {"bar": 2, "baz": 3, "foo": 1}


if sys.version_info >= (3, 10):
    # this trips up the py <3.9 interpreter
    extra_params = [
        dict | None,
        None | dict,
    ]
else:
    extra_params = []


@pytest.mark.parametrize(
    "typo",
    [
        Optional[dict],
        Union[dict, None],
        Union[None, dict],
    ]
    + extra_params,  # type: ignore
)
@pytest.mark.usefixtures("isolated_env")
def test_062__optional_dict(typo) -> None:
    """Test normal use case."""

    @dc.dataclass(frozen=True)
    class Config:
        FOO: typo  # type: ignore

    os.environ["FOO"] = "foo=1 bar=2 baz=3"
    config = from_environment_as_dataclass(Config)
    assert config.FOO == {"bar": "2", "baz": "3", "foo": "1"}


@pytest.mark.usefixtures("isolated_env")
def test_100_error__missing_required() -> None:
    """Test error use case."""

    # Missing
    @dc.dataclass(frozen=True)
    class Config:
        FOO: bool

    with pytest.raises(OSError):
        from_environment_as_dataclass(Config)


@pytest.mark.usefixtures("isolated_env")
def test_101_error__int() -> None:
    """Test error use case."""

    # Bad Type - int
    @dc.dataclass(frozen=True)
    class Config:
        FOO: int

    os.environ["FOO"] = "123.5"
    with pytest.raises(ValueError):
        from_environment_as_dataclass(Config)


@pytest.mark.usefixtures("isolated_env")
def test_102_error__float() -> None:
    """Test error use case."""

    # Bad Type - float
    @dc.dataclass(frozen=True)
    class Config:
        FOO: float

    os.environ["FOO"] = "1x10^-1"
    with pytest.raises(ValueError):
        from_environment_as_dataclass(Config)


@pytest.mark.usefixtures("isolated_env")
def test_103_error__bool() -> None:
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
        with pytest.raises(ValueError):
            from_environment_as_dataclass(Config)


@pytest.mark.usefixtures("isolated_env")
def test_104_error__bytes() -> None:
    """Test error use case."""

    # using a bytes, this is similar to any multi-arg built-in type
    @dc.dataclass(frozen=True)
    class Config:
        FOO: bytes = bytes()

    os.environ["FOO"] = "foo bar baz"
    with pytest.raises(TypeError):
        from_environment_as_dataclass(Config)


@pytest.mark.usefixtures("isolated_env")
def test_105_error__overly_nested_type_alias() -> None:
    """Test error use case."""

    # using a bytes, this is similar to any multi-arg built-in type
    @dc.dataclass(frozen=True)
    class Config:
        FOO: List[Dict[str, int]]

    os.environ["FOO"] = "doesn't matter, this won't get read before error"
    with pytest.raises(ValueError) as cm:
        from_environment_as_dataclass(Config)
    assert str(cm.value) == (
        "'typing.List[typing.Dict[str, int]]' is not a "
        "supported type: field='FOO' (typehints "
        "must resolve to 'type' within 1 nesting, or "
        "2 if using 'Final', 'Optional', or a None-'Union' pairing)"
    )


@pytest.mark.usefixtures("isolated_env")
def test_106__dict_delims() -> None:
    """Test error use case."""

    @dc.dataclass(frozen=True)
    class Config:
        FOO: Dict[str, int]

    os.environ["FOO"] = "this-is-my-extra-cool-string = 2"
    with pytest.raises(RuntimeError) as cm:
        from_environment_as_dataclass(Config, dict_kv_joiner=" = ")
    assert str(cm.value) == (
        r"'collection_sep' ('None'='\s+') cannot overlap with "
        "'dict_kv_joiner': 'None' & ' = '"
    )


@pytest.mark.usefixtures("isolated_env")
def test_107__dict_delims() -> None:
    """Test error use case."""

    @dc.dataclass(frozen=True)
    class Config:
        FOO: Dict[str, int]

    os.environ["FOO"] = "this-is-my-extra-cool-string = 2"
    with pytest.raises(RuntimeError) as cm:
        from_environment_as_dataclass(Config, dict_kv_joiner=" = ", collection_sep=" ")
    assert str(cm.value) == (
        r"'collection_sep' ('None'='\s+') cannot overlap with "
        "'dict_kv_joiner': ' ' & ' = '"
    )


@pytest.mark.usefixtures("isolated_env")
def test_108_error__bytes() -> None:
    """Test error use case."""

    @dc.dataclass(frozen=True)
    class Config:
        FOO: bytes

    os.environ["FOO"] = "foo bar baz"
    with pytest.raises(TypeError):
        from_environment_as_dataclass(Config)


def test_109_error__final_only() -> None:
    """Test error use case."""

    @dc.dataclass(frozen=True)
    class Config:
        FOO: Final  # type: ignore[misc] # ...this is an error after all

    os.environ["FOO"] = "foo bar baz"
    with pytest.raises(ValueError):
        from_environment_as_dataclass(Config)


@pytest.mark.usefixtures("isolated_env")
def test_110_error__any() -> None:
    """Test error use case."""

    @dc.dataclass(frozen=True)
    class Config:
        FOO: Any

    os.environ["FOO"] = "foo bar baz"
    with pytest.raises(ValueError):
        from_environment_as_dataclass(Config)


@pytest.mark.usefixtures("isolated_env")
def test_200_convert() -> None:
    """Test conversion cases."""
    with pytest.raises(TypeError):
        from_environment_as_dataclass(None)  # type: ignore

    @dc.dataclass(frozen=True)
    class Config:
        FOO: bool = True

    with pytest.raises(TypeError):
        from_environment_as_dataclass(Config())  # type: ignore


@pytest.mark.usefixtures("isolated_env")
def test_300_post_init__int_range() -> None:
    """Test post-init processing."""

    @dc.dataclass(frozen=True)
    class Config:
        FOO: int

        def __post_init__(self) -> None:
            if self.FOO <= 0:
                raise ValueError("'FOO' is non-positive")

    os.environ["FOO"] = "-123456"
    with pytest.raises(ValueError):
        from_environment_as_dataclass(Config)
