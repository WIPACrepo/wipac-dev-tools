"""Tools for python's typing module."""

import sys
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

from typing_extensions import Final  # 3.8+ get the real thing

# IMPORTS for PYTHON 3.7+
if sys.version_info >= (3, 7):
    from typing import _SpecialForm

    try:
        from typing import _GenericAlias as GenericAlias  # type: ignore[attr-defined]
    except ImportError:
        from typing import GenericAlias  # type: ignore[attr-defined]


# some helper functions
def _is_optional(typ: GenericAlias) -> bool:
    # Optional[int] *is* typing.Union[int, NoneType]
    return (
        typ.__origin__ == Union
        and len(typ.__args__) == 2
        and typ.__args__[-1] == type(None)  # noqa: E721
    )


def _is_final(typ: GenericAlias) -> bool:
    return bool(typ.__origin__ == Final)


class AnyTypeReductionError(Exception):
    """Raise when an `Any` type fails type-reduction."""


class BareSpecialFormReductionError(Exception):
    """Raise when a non-nested `Final`/`Optional` type fails type-reduction.

    Example: Final vs Final[int]
    """


class UnresolvedReductionError(Exception):
    """Raised if type reduction fails."""


def reduce_type(
    typ: Union[type, _SpecialForm, GenericAlias],
) -> Tuple[type, Optional[Tuple[type, ...]]]:
    """Reduce the `typing` module's typehints to actual types.

    Examples:
        List[str] -> list, str
        Final[bool] -> bool, None
        int -> int, None
    """
    if isinstance(typ, type):
        return typ, None

    # detect bare 'Final' and 'Optional'
    if isinstance(typ, _SpecialForm):
        raise BareSpecialFormReductionError()

    # take care of 'typing'-module types
    if isinstance(typ, GenericAlias):
        # Ex: Final[int], Optional[Dict[str,int]]
        if _is_optional(typ) or _is_final(typ):
            if isinstance(typ.__args__[0], type):  # Ex: Final[int], Optional[int]
                typ, arg_typs = typ.__args__[0], None
            else:  # Final[Dict[str,int]], Optional[Dict[str,int]]
                typ, arg_typs = typ.__args__[0].__origin__, typ.__args__[0].__args__
        # Ex: List[int], Dict[str,int]
        else:
            typ, arg_typs = typ.__origin__, typ.__args__
        if not (
            isinstance(typ, type)
            and (arg_typs is None or all(isinstance(x, type) for x in arg_typs))
        ):
            raise ValueError(
                f"'{field.type}' is not a supported type: "
                f"field='{field.name}' (the typing-module's alias "
                f"types must resolve to 'type' within 1 nesting, "
                f"or 2 if using 'Final' or 'Optional')"
            )

    # detect here 'Any'
    if typ == Any:
        raise AnyTypeReductionError()

    if not isinstance(typ, type):
        raise UnresolvedReductionError()

    return typ, arg_typs
