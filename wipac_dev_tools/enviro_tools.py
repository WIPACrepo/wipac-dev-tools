"""Module to support parsing environment variables."""


import os
import re
import sys
from distutils.util import strtobool
from typing import (
    Any,
    Dict,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

if sys.version_info >= (3, 7):
    import dataclasses

    try:
        from typing import _GenericAlias as GenericAlias  # type: ignore[attr-defined]
    except ImportError:
        from typing import GenericAlias  # type: ignore[attr-defined]


RetVal = Union[str, int, float, bool]
OptionalDict = Mapping[str, Optional[RetVal]]
KeySpec = Union[str, Sequence[str], OptionalDict]


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


def _typecast_for_dataclass(
    env_val: str,
    typ: type,
    arg_typs: Optional[Tuple[type, ...]],
    collection_sep: Optional[str],
    dict_kv_joiner: str,
) -> Any:
    """Collect the typecast value"""
    if typ == list:
        _list = env_val.split(collection_sep)
        if arg_typs:
            return [arg_typs[0](x) for x in _list]
        return _list

    elif typ == dict:
        _dict = {
            x.split(dict_kv_joiner)[0]: int(x.split(dict_kv_joiner)[1])
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


T = TypeVar("T")


def from_environment_as_dataclass(
    dclass: Type[T],
    collection_sep: Optional[str] = None,
    dict_kv_joiner: str = "=",
) -> T:
    """Obtain configuration values from the OS environment formatted in a dataclass.

    Environment variables are matched by using `upper()` on their
    dataclass field's name. The matching environment string is cast
    using the dataclass field's has a type (`strtobool` for bools).
    Then, the values are used to create a dataclass instance. All normal
    dataclass init-behavior is expected, like required fields
    (positional arguments), optional fields with defaults, default
    factories, post-init processing, etc.

    If a field's type is a `list`, `dict`, `set`, `frozenset`, or
    an analogous type alias from the 'typing' module, then a conversion
    is made (see `collection_sep` and `dict_kv_joiner`). Sub-types
    are cast if using a typing-module type alias. The typing module's
    alias types must resolve to `type` within 1 nesting (eg: List[bool]
    and Dict[int, float] are okay; List[Dict[int, float]] is not).

    Arguments:
        dclass - a (non-instantiated) dataclass, aka a type
        collection_sep - the delimiter to split collections on ("1 2 5")
        dict_kv_joiner - the delimiter that joins key-value pairs ("a=1 b=2 c=1")

    Returns:
        a dataclass instance mapping configuration keys to configuration values

    Example:
        @dataclasses.dataclass(frozen=True)
        class Config:
           required_from_environment: str  # matches REQUIRED_FROM_ENVIRONMENT
           host: str = "localhost"  # matches HOST
           port: int = 8080  # matches PORT
       }
       config_dclass = from_environment_as_dataclass(Config)

    Raises:
        OSError - If a configuration value is requested and no default
                  value is provided, to indicate that the
                  component's configuration is incomplete due to missing
                  data from the OS.
        ValueError - If a type-indicated value is not a legal value
    """

    if sys.version_info >= (3, 7):
        return _from_environment_as_dataclass(dclass, collection_sep, dict_kv_joiner)
    else:
        raise NotImplementedError(
            "Sorry, from_environment_as_dataclass() is only available for 3.7+"
        )


def _from_environment_as_dataclass(
    dclass: Type[T],
    collection_sep: Optional[str],
    dict_kv_joiner: str,
) -> T:

    if (
        (dict_kv_joiner == collection_sep)
        or (not collection_sep and " " in dict_kv_joiner)  # collection_sep=None is \s+
        or (collection_sep and collection_sep in dict_kv_joiner)
    ):
        raise RuntimeError(
            r"'collection_sep' ('None'='\s+') cannot overlap with 'dict_kv_joiner': "
            f"'{collection_sep}' & '{dict_kv_joiner}'"
        )

    if not (dataclasses.is_dataclass(dclass) and isinstance(dclass, type)):
        raise TypeError(f"Expected (non-instantiated) dataclass: 'dclass' ({dclass})")

    kwargs: Dict[str, Any] = {}
    for field in dataclasses.fields(dclass):
        if not field.init:
            continue  # don't try to get a field that can't be set via __init__
        # get value
        try:
            env_val = os.environ[field.name.upper()]
        except KeyError:
            continue

        # take care of 'GenericAlias' types
        if isinstance(field.type, GenericAlias):
            typ, arg_typs = field.type.__origin__, field.type.__args__
            if not all(isinstance(x, type) for x in [typ] + list(arg_typs)):
                raise ValueError(
                    f"'{field.type}'-indicated type is not a legal type: "
                    f"field='{field.name}' (the typing module's alias "
                    f"types must resolved to 'type' within 1 nesting)"
                )
        else:
            typ, arg_typs = field.type, None

        try:
            kwargs[field.name] = _typecast_for_dataclass(
                env_val, typ, arg_typs, collection_sep, dict_kv_joiner
            )
        except ValueError as e:
            raise ValueError(
                f"'{field.type}'-indicated value is not a legal value: "
                f"var='{field.name.upper()}' value='{env_val}'"
            ) from e

    try:
        return dclass(**kwargs)
    except TypeError as e:
        m = re.fullmatch(
            r"__init__\(\) missing \d+ required positional argument(?P<s>s?): (?P<args>.+)",
            str(e),
        )
        if m:
            raise OSError(
                f"Missing required environment variable{m.groupdict()['s']}: "
                f"{m.groupdict()['args'].upper().replace(' AND ', ' and ')}"
            ) from e
        raise  # some other kind of TypeError
