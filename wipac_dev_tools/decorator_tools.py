"""Tools in the form of simple decorators."""

import functools
import inspect
from collections.abc import Awaitable, Callable
from typing import Any, ParamSpec, TypeVar, overload

P = ParamSpec("P")
R = TypeVar("R")


# --------------------------------------------------------------------------------------
# success_or_exception()
# --------------------------------------------------------------------------------------


@overload
def success_or_exception(
    on_success: Callable[[R], None],
    on_exception: Callable[[BaseException], None],
) -> Callable[[Callable[P, R]], Callable[P, R]]: ...


@overload
def success_or_exception(
    on_success: Callable[[R], None],
    on_exception: Callable[[BaseException], None],
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]: ...


def success_or_exception(
    on_success: Callable[[R], None],
    on_exception: Callable[[BaseException], None],
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Create a decorator that runs callbacks after success or after an exception.

    The returned decorator works with both synchronous and async functions.

    Args:
        on_success:
            Called with the function's return value when the wrapped call completes
            successfully.
        on_exception:
            Called with the raised exception when the wrapped call raises. The
            exception is re-raised after this callback.

    Returns:
        A decorator that preserves the wrapped function's signature and return type (sync or
        async).

    Notes:
        - Exceptions are not suppressed.
        - Callbacks are invoked after the wrapped function returns/raises (not before).

    Example:
        ```
        @success_or_exception(
            on_success=lambda out: print(f"ok: {out=}"),
            on_exception=lambda e: print(f"err: {e!r}"),
        )
        def add_one(x: int) -> int:
            if x < 0:
                raise ValueError("x must be >= 0")
            return x + 1
        ```
    """

    def wrapper(fn: Callable[..., Any]) -> Callable[..., Any]:

        # ASYNC
        if inspect.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def _a_impl(*args: P.args, **kwargs: P.kwargs) -> R:
                try:
                    out = await fn(*args, **kwargs)
                except BaseException as e:
                    on_exception(e)
                    raise
                on_success(out)
                return out

            return _a_impl

        # SYNC
        else:

            @functools.wraps(fn)
            def _impl(*args: P.args, **kwargs: P.kwargs) -> R:
                try:
                    out = fn(*args, **kwargs)
                except BaseException as e:
                    on_exception(e)
                    raise
                on_success(out)
                return out

            return _impl

    return wrapper


# --------------------------------------------------------------------------------------
