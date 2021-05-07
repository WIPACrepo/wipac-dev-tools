"""Module to support parsing environment variables."""

import os
from distutils.util import strtobool
from typing import Dict, Mapping, Optional, Sequence, Union, cast

RetVal = Union[str, int, float, bool]
OptionalDict = Mapping[str, Optional[RetVal]]
KeySpec = Union[str, Sequence[str], OptionalDict]


def _typecast(source: str, type_: type, legacy_bool: bool) -> RetVal:
    if type_ == bool:
        if legacy_bool:
            return source.lower() in ("true", "t", "1", "yes", "y")
        else:
            return bool(strtobool(source.lower()))
    elif type_ == int:
        return int(source)
    elif type_ == float:
        return float(source)
    else:
        return source


def from_environment(keys: KeySpec, legacy_bool: bool = False) -> Dict[str, RetVal]:
    """Obtain configuration values from the OS environment.

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
                       "PORT": "8080",
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

    Keyword Arguments:
        legacy_bool: Use the less strict bool-casting, where
                        True  => ("y", "yes", "t", "true", or "1"),
                        False => any other string.
                     As opposed to utilizing distutils.util.strtobool, where
                        True  => ("y", "yes", "t", "true", "on", or "1"),
                        False => ("n", "no", "f", "false", "off", or "0"),
                        Error => any other string.
                     - ***both methods are case-insensitive***

    Returns:
        a dictionary mapping configuration keys to configuration values

    Raises:
        OSError - If a configuration value is requested and no default
                  value is provided (via a dict), to indicate that the
                  component's configuration is incomplete due to missing
                  data from the OS.
        ValueError - If a bool-indicated value is not a legal value
                     (see `legacy_bool` above)
    """
    if isinstance(keys, str):
        keys = {keys: None}
    elif isinstance(keys, list):
        keys = dict.fromkeys(keys, None)
    elif not isinstance(keys, dict):
        raise TypeError("keys: Expected string, list or dict")

    config = keys.copy()

    for key in config:
        if key in os.environ:
            if config[key] is not None:
                config[key] = _typecast(os.environ[key], type(config[key]), legacy_bool)
            else:
                config[key] = os.environ[key]

        elif config[key] is None:
            raise OSError(f"Missing environment variable '{key}'")

    return cast(Dict[str, RetVal], config)
