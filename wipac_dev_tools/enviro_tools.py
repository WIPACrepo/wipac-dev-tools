"""Module to support parsing environment variables."""

import dataclasses
import logging
import os
import re
import sys
import types
from typing import (
    Any,
    Dict,
    Mapping,
    Optional,
    Sequence,
    TYPE_CHECKING,
    Tuple,
    Type,
    TypeVar,
    Union,
    _SpecialForm,
    cast,
)

from typing_extensions import Final

from . import logging_tools
from .strtobool import strtobool

try:
    from typing import _GenericAlias as GenericAlias  # type: ignore[attr-defined]
except ImportError:
    from typing import GenericAlias  # type: ignore[attr-defined]

# fmt: off
if TYPE_CHECKING:  # _typeshed only exists at runtime
    from _typeshed import DataclassInstance  # type: ignore[attr-defined]
    DataclassT = TypeVar("DataclassT", bound=DataclassInstance)
else:
    DataclassT = TypeVar("DataclassT")
# fmt: on


RetVal = Union[str, int, float, bool]
OptionalDict = Mapping[str, Optional[RetVal]]
KeySpec = Union[str, Sequence[str], OptionalDict]
sdict = Dict[str, Any]


# ---------------------------------------------------------------------------------------


def _typecast(source: str, type_: type) -> RetVal:
    if type_ == bool:
        return bool(strtobool(source.lower()))
    elif type_ == int:
        return int(source)
    elif type_ == float:
        return float(source)
    else:
        return source


def from_environment(keys: KeySpec) -> Dict[str, RetVal]:
    """Obtain configuration values from the OS environment.

    Parsing Details:
    Types are inferred from the default values, and casted as such:
    `bool`: *(case-insensitive)*:
        - `True`  => ("y", "yes", "t", "true", "on", or "1")
        - `False` => ("n", "no", "f", "false", "off", or "0")
        - `Error` => any other string
    `int`: normal cast (`int(str)`)
    `float`: normal cast (`float(str)`)
    `other`: no change (`str`)

    Arguments:
        keys - Specify the configuration values to obtain.

               This can be a string, specifying a single key, such as:

                   config_dict = from_environment("LANGUAGE")

               This can be a list of strings, specifying multiple keys,
               such as:

                   config_dict = from_environment(["HOME", "LANGUAGE"])

               This can be a dictionary that provides some default values,
               and will accept overrides from the environment:

                   default_config = {
                       "HOST": "localhost",
                       "PORT": 8080,
                       "REQUIRED_FROM_ENVIRONMENT": None
                   }
                   config_dict = from_environment(default_config)

               Note in this case that if 'HOST' or 'PORT' were defined in the
               environment, those values would be returned in config_dict. If
               the values were not defined in the environment, the default values
               from default_config would be returned in config_dict.

               Also note, that if 'REQUIRED_FROM_ENVIRONMENT' is not defined,
               an OSError will be raised. The sentinel value of None indicates
               that the configuration parameter MUST be sourced from the
               environment.

    Returns:
        a dictionary mapping configuration keys to configuration values

    Raises:
        OSError - If a configuration value is requested and no default
                  value is provided (via a dict), to indicate that the
                  component's configuration is incomplete due to missing
                  data from the OS.
        ValueError - If a type-indicated value is not a legal value
    """
    if isinstance(keys, str):
        keys = {keys: None}
    elif isinstance(keys, list):
        keys = dict.fromkeys(keys, None)
    elif not isinstance(keys, dict):
        raise TypeError("keys: Expected string, list or dict")

    config = keys.copy()

    for key in config:
        # grab & cast key-value
        if key in os.environ:
            try:
                config[key] = _typecast(os.environ[key], type(config[key]))
            except ValueError:
                raise ValueError(  # pylint: disable=raise-missing-from
                    f"'{type(config[key])}'-indicated value is not a legal value: "
                    f"key='{key}' value='{config[key]}'"
                )
        # missing key
        elif config[key] is None:
            raise OSError(f"Missing environment variable '{key}'")

    return cast(Dict[str, RetVal], config)


# ---------------------------------------------------------------------------------------


def _typecast_for_dataclass(
    env_val: str,
    typ: type,
    arg_typs: Optional[Tuple[type, ...]],
    collection_sep: Optional[str],
    dict_kv_joiner: str,
) -> Any:
    """Collect the typecast value."""

    if typ == list:
        _list = env_val.split(collection_sep)
        if arg_typs:
            return [arg_typs[0](x) for x in _list]
        return _list

    elif typ == dict:
        _dict = {
            x.split(dict_kv_joiner)[0]: x.split(dict_kv_joiner)[1]
            for x in env_val.split(collection_sep)
        }
        if arg_typs:
            return {arg_typs[0](k): arg_typs[1](v) for k, v in _dict.items()}
        return _dict

    elif typ == set:
        _set = set(env_val.split(collection_sep))
        if arg_typs:
            return {arg_typs[0](x) for x in _set}
        return _set

    elif typ == frozenset:
        _frozenset = frozenset(env_val.split(collection_sep))
        if arg_typs:
            return {arg_typs[0](x) for x in _frozenset}
        return _frozenset

    elif typ == bool:
        return strtobool(env_val)

    else:
        return typ(env_val)


def from_environment_as_dataclass(
    dclass: Type[DataclassT],
    collection_sep: Optional[str] = None,
    dict_kv_joiner: str = "=",
    log_vars: Optional[logging_tools.LoggerLevel] = "WARNING",
) -> DataclassT:
    """Obtain configuration values from the OS environment formatted in a
    dataclass.

    Environment variables are matched to a dataclass field's name. The
    matching environment string is cast using the dataclass field's type
    (there are some special cases for built-in types, see below). Then,
    the values are used to create a dataclass instance. All normal
    dataclass init-behavior is expected, like required fields
    (positional arguments), optional fields with defaults, default
    factories, post-init processing, etc.

    If a field's type is a bool, `wipac_dev_tools.strtobool` is applied.

    If a field's type is a `list`, `dict`, `set`, `frozenset`, or
    an analogous type alias from the 'typing' module, then a conversion
    is made (see `collection_sep` and `dict_kv_joiner`). Sub-types
    are cast if using a typing-module type alias. The typing-module's
    alias types must resolve to `type` within 1 nesting (eg: List[bool]
    and Dict[int, float] are okay; List[Dict[int, float]] is not), or
    2 if using 'Final' or 'Optional' (ex: Final[Dict[int, float]]).

    If a field's type is a class that accepts 1 argument, it is
    instantiated as such.

    Arguments:
        dclass - a (non-instantiated) dataclass, aka a type
        collection_sep - the delimiter to split collections on ("1 2 5")
        dict_kv_joiner - the delimiter that joins key-value pairs ("a=1 b=2 c=1")
        log_vars - what level to log the collected environment variables (set to `None` to not log)

    Returns:
        a dataclass instance mapping configuration keys to configuration values

    Example:
        env:
            FPATH=/home/example/path
            PORT=9999
            HOST=localhost
            MSGS_PER_CLIENTS=alpha=0 beta=55 delta=3
            USE_EVEN=22
            RETRIES=3

        python:
            @dataclasses.dataclass(frozen=True)
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

            class EvenState:
                def __init__(self, arg: str):
                    self.is_even = not bool(int(arg) % 2)  # 1%2 -> 1 -> T -> F
                def __repr__(self) -> str:
                    return f"EvenState(is_even={self.is_even})"

            config = from_environment_as_dataclass(Config)
            print(config)

        stdout:
            Config(
                FPATH=PosixPath('/home/example/path'),
                PORT=9999,
                HOST='localhost',
                MSGS_PER_CLIENTS={'alpha': 0, 'beta': 55, 'delta': 3},
                USE_EVEN=EvenState(is_even=True),
                RETRIES=3,
                TIMEOUT=30)


    Raises:
        OSError - If a configuration value is requested and no default
                  value is provided, to indicate that the component's
                  configuration is incomplete due to missing data from
                  the OS.
        ValueError - If an indicated value is not a legal value
        TypeError - If an argument or indicated value is not a legal type
    """
    return _from_environment_as_dataclass(
        dclass, collection_sep, dict_kv_joiner, log_vars
    )


def _resolve_optional(
    typ_origin: Any,  # at this point, types kind of break down since there is no common base-type among the many variations
    typ_args: tuple,
):
    # Optional[bool] *is* typing.Union[bool, NoneType]
    # similarly...
    #   Optional[bool]
    #   Union[bool, None]
    #   Union[None, bool]
    #   bool | None
    #   None | bool
    if (
        typ_origin == Union
        and len(typ_args) == 2
        and type(None) in typ_args  # doesn't matter where None is
    ):
        return next(x for x in typ_args if x is not type(None))  # get the non-None
    else:
        return None


def _resolve_final(
    typ_origin: Any,  # at this point, types kind of break down since there is no common base-type among the many variations
    typ_args: tuple,
):
    if typ_origin == Final:
        return typ_args[0]
    else:
        return None


def _check_invalid_typehints(
    typ_origin: Any,  # at this point, types kind of break down since there is no common base-type among the many variations
    typ_args: tuple,
    field: dataclasses.Field,
):
    if isinstance(typ_origin, _SpecialForm) and not typ_args:
        # ERROR: detect bare 'Final' and 'Optional'
        raise ValueError(
            f"'{field.type}' is not a supported type: "
            f"field='{field.name}' (any of the typing-module's SpecialForm "
            f"types, 'Final' and 'Optional', must have a nested type attached)"
        )
    elif typ_origin is Any:
        # ERROR: Any is not ok
        raise ValueError(
            f"'{field.type}' is not a supported type: "
            f"field='{field.name}' (the 'Any' type and subclasses are not "
            f"valid environment variable types)"
        )
    elif typ_origin == Union and (len(typ_args) != 2 or type(None) not in typ_args):
        # ERROR: disallowed Union usage (only single w/ None ok)
        raise ValueError(
            f"'{field.type}' is not a supported type: "
            f"field='{field.name}' (the only allowed 'Union' type "
            f"is one that makes a single-typed value optional, ex: "
            f"'Union[bool, None]', 'Union[None, dict[str,int]]', "
            f"'int | None', or 'None | str'"
            ")"
        )
    # fall-through: okay


def deconstruct_typehint(
    field: dataclasses.Field,
) -> Tuple[type, Optional[Tuple[type, ...]]]:
    """Take a type hint and return its type and its arguments' types."""
    _check_invalid_typehints(field.type, tuple(), field)

    if isinstance(field.type, (GenericAlias, types.GenericAlias)):
        # Ex:
        #   List[int]     -> list, [int]
        #   dict[str,int] -> dict, [str,int]
        typ_origin, typ_args = field.type.__origin__, field.type.__args__
    elif sys.version_info >= (3, 10) and isinstance(field.type, types.UnionType):
        # Ex:
        #   None | int, bool | str, ...
        typ_origin, typ_args = Union, field.type.__args__
    elif isinstance(field.type, type):
        # Ex:
        #   bool, str, int, ...
        return field.type, None
    else:
        # ERROR: ???
        raise ValueError(
            f"'{field.type}' is not a supported type: field='{field.name}'"
        )

    _check_invalid_typehints(typ_origin, typ_args, field)

    #
    # every typehint that is left is some kind of wrapper. iow, not a primitive
    #

    # resolve nesting, get a workable type
    if (inner := _resolve_optional(typ_origin, typ_args)) or (
        inner := _resolve_final(typ_origin, typ_args)
    ):
        # Ex: Final[int], Optional[Dict[str,int]]
        if isinstance(inner, type):  # Ex: Final[int], Optional[int]
            typ_origin, typ_args = inner, None
        else:  # Final[Dict[str,int]], Optional[Dict[str,int]]
            typ_origin, typ_args = inner.__origin__, inner.__args__

    #
    # validate what we got, then return
    #
    _check_invalid_typehints(typ_origin, typ_args, field)
    too_nested_error_msg = (
        f"'{field.type}' is not a supported type: field='{field.name}' "
        f"(typehints must resolve to 'type' within 1 nesting, "
        f"or 2 if using 'Final', 'Optional', or a None-'Union' pairing)"
    )
    if not isinstance(typ_origin, type):
        raise ValueError(too_nested_error_msg)
    if typ_args and not (all(isinstance(x, type) for x in typ_args)):
        raise ValueError(too_nested_error_msg)

    return typ_origin, typ_args


def _validate_delimiters(collection_sep: Optional[str], dict_kv_joiner: str) -> None:
    if (
        (dict_kv_joiner == collection_sep)
        or (not collection_sep and " " in dict_kv_joiner)  # collection_sep=None is \s+
        or (collection_sep and collection_sep in dict_kv_joiner)
    ):
        raise RuntimeError(
            r"'collection_sep' ('None'='\s+') cannot overlap with 'dict_kv_joiner': "
            f"'{collection_sep}' & '{dict_kv_joiner}'"
        )


def _validate_is_non_instantiated_dataclass(dclass: Type[DataclassT]) -> None:
    if not (dataclasses.is_dataclass(dclass) and isinstance(dclass, type)):
        raise TypeError(f"Expected (non-instantiated) dataclass: 'dclass' ({dclass})")


def _cast_to_dataclass(dclass: Type[DataclassT], env_var_attrs: sdict) -> DataclassT:
    try:
        return cast(DataclassT, dclass(**env_var_attrs))
    except TypeError as e:
        m = re.fullmatch(
            r".*__init__\(\) missing \d+ required positional argument(?P<s>s?): (?P<args>.+)",
            str(e),
        )  # in 3.10 the class's qualname is used before "__init__()..."
        if m:
            raise OSError(
                f"Missing required environment variable{m.groupdict()['s']}: "
                f"{m.groupdict()['args']}"
            ) from e
        raise  # some other kind of TypeError


def _from_environment_as_dataclass(
    dclass: Type[DataclassT],
    collection_sep: Optional[str],
    dict_kv_joiner: str,
    log_vars: Optional[logging_tools.LoggerLevel],
) -> DataclassT:
    # check args
    _validate_delimiters(collection_sep, dict_kv_joiner)
    _validate_is_non_instantiated_dataclass(dclass)

    # iterate fields and find env vars
    env_var_attrs: sdict = {}
    for field in dataclasses.fields(dclass):
        if not field.init:
            continue  # don't try to get a field that can't be set via __init__

        # get value
        try:
            env_val = os.environ[field.name]
        except KeyError:
            continue

        # get type
        typ, arg_typs = deconstruct_typehint(field)

        # cast value to type
        try:
            env_var_attrs[field.name] = _typecast_for_dataclass(
                env_val, typ, arg_typs, collection_sep, dict_kv_joiner
            )
        except ValueError as e:
            raise ValueError(
                f"'{field.type}'-indicated value is not a legal value: "
                f"var='{field.name}' value='{env_val}'"
            ) from e

    # to dataclass!
    env_vars_dc = _cast_to_dataclass(dclass, env_var_attrs)

    # log & return
    if log_vars:
        logging_tools.log_dataclass(
            env_vars_dc,
            logging.getLogger(),
            log_vars,
            prefix="(env)",
            obfuscate_sensitive_substrings=True,
        )
    return env_vars_dc
