<!--- Top of README Badges (automated) --->
[![PyPI](https://img.shields.io/pypi/v/wipac-dev-tools)](https://pypi.org/project/wipac-dev-tools/) [![GitHub release (latest by date including pre-releases)](https://img.shields.io/github/v/release/WIPACrepo/wipac-dev-tools?include_prereleases)](https://github.com/WIPACrepo/wipac-dev-tools/) [![PyPI - License](https://img.shields.io/pypi/l/wipac-dev-tools)](https://github.com/WIPACrepo/wipac-dev-tools/blob/main/LICENSE) [![Lines of code](https://img.shields.io/tokei/lines/github/WIPACrepo/wipac-dev-tools)](https://github.com/WIPACrepo/wipac-dev-tools/) [![GitHub issues](https://img.shields.io/github/issues/WIPACrepo/wipac-dev-tools)](https://github.com/WIPACrepo/wipac-dev-tools/issues?q=is%3Aissue+sort%3Aupdated-desc+is%3Aopen) [![GitHub pull requests](https://img.shields.io/github/issues-pr/WIPACrepo/wipac-dev-tools)](https://github.com/WIPACrepo/wipac-dev-tools/pulls?q=is%3Apr+sort%3Aupdated-desc+is%3Aopen) 
<!--- End of README Badges (automated) --->
# wipac-dev-tools
Common, basic, and reusable development tools


## Utilities

### Logging Tools

#### `wipac_dev_tools.logging_tools.set_level()`
_Available for Python 3.6+_
```
def set_level(
    level: str,
    first_party_loggers: Optional[List[Union[str, logging.Logger]]] = None,
    third_party_level: LoggerLevel = "WARNING",
    use_coloredlogs: bool = False,
) -> None:
    """Set the level of the root logger, first-party loggers, and third-party loggers.

    The root logger and first-party logger(s) are set to the same level
    (`level`). The third-party loggers are non-root and non-first-party
    loggers that are defined at the time of invocation. If a logger is
    created after this function call, then its level defaults to its
    parent (that's the root logger for non-child loggers).

    Passing `use_coloredlogs=True` will import and use the `coloredlogs`
    package. This will set the logger format and use colored text.
    """
```

#### `wipac_dev_tools.logging_tools.log_argparse_args()`
_Available for Python 3.6+_
```
def log_argparse_args(
    args: argparse.Namespace,
    logger: Optional[Union[str, logging.Logger]] = None,
    level: LoggerLevel = "WARNING",
) -> argparse.Namespace:
    """Log the argparse args and their values at the given level.

    Return the args (Namespace) unchanged.

    Example:
        2022-05-13 22:37:21 fv-az136-643 my-logs[61] WARNING in_file: in_msg.pkl
        2022-05-13 22:37:21 fv-az136-643 my-logs[61] WARNING out_file: out_msg.pkl
        2022-05-13 22:37:21 fv-az136-643 my-logs[61] WARNING log: DEBUG
        2022-05-13 22:37:21 fv-az136-643 my-logs[61] WARNING log_third_party: WARNING
    """
```


### Environment Variable Tool(s)

#### `wipac_dev_tools.from_environment()`
_Available for Python 3.6+_
```
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
```

#### `wipac_dev_tools.from_environment_as_dataclass()`
_Available for Python 3.7+_
```
def from_environment_as_dataclass(
    dclass: Type[T],
    collection_sep: Optional[str] = None,
    dict_kv_joiner: str = "=",
) -> T:
    """Obtain configuration values from the OS environment formatted in a dataclass.

    Environment variables are matched to a dataclass field's name. The
    matching environment string is cast using the dataclass field's type
    (there are some special cases for built-in types, see below). Then,
    the values are used to create a dataclass instance. All normal
    dataclass init-behavior is expected, like required fields
    (positional arguments), optional fields with defaults, default
    factories, post-init processing, etc.

    If a field's type is a bool, `strtobool` is used for typecasting.

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
```