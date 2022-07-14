"""Module to support parsing environment variables."""

import dataclasses
import os
import re
from distutils.util import strtobool
from typing import Any, Dict, Mapping, Optional, Sequence, Type, TypeVar, Union, cast

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


T = TypeVar("T")


def from_environment_as_dataclass(dclass: Type[T]) -> T:
    """Obtain configuration values from the OS environment formatted in a dataclass.

    Environment variables are matched by using `upper()` on their
    dataclass field's name. The matching environment string is cast
    using the dataclass field's has a type (`strtobool` for bools).
    Then, the values are used to create a dataclass instance. All normal
    dataclass init-behavior is expected, like required fields
    (positional arguments), optional fields with defaults, default
    factories, post-init processing, etc.

    If a field uses a `typing._GenericAlias` type-hint
    (eg: `List[int]`), then the raw environment variable str is used
    (hint: use `__post_init__()`).

    Arguments:
        dclass - a (non-instantiated) dataclass, aka a type

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
        # collect the typecast value
        if not isinstance(field.type, type):  # field is a 'typing._GenericAlias'
            kwargs[field.name] = env_val
        elif field.type == bool:
            kwargs[field.name] = strtobool(env_val)
        else:
            try:
                kwargs[field.name] = field.type(env_val)
            except ValueError:
                raise ValueError(  # pylint: disable=raise-missing-from
                    f"'{field.type}'-indicated value is not a legal value: "
                    f"var='{field.name.upper()}' value='{env_val}'"
                )

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
