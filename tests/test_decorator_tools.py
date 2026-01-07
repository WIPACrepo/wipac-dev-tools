"""Unit tests for 'decorator_tools' module."""

import pytest

from wipac_dev_tools.decorator_tools import success_or_exception


def test_000_sync_success_calls_on_success_only() -> None:
    """Calls on_success with the return value for sync functions."""
    calls: list[tuple[str, object]] = []

    @success_or_exception(
        on_success=lambda out: calls.append(("success", out)),
        on_exception=lambda e: calls.append(("exception", e)),
    )
    def f(x: int) -> int:
        return x + 1

    assert f(2) == 3
    assert calls == [("success", 3)]


def test_001_sync_exception_calls_on_exception_only_and_reraises() -> None:
    """Calls on_exception and re-raises for sync functions that raise."""
    calls: list[tuple[str, object]] = []

    @success_or_exception(
        on_success=lambda out: calls.append(("success", out)),
        on_exception=lambda e: calls.append(("exception", e)),
    )
    def f(x: int) -> int:
        raise ValueError(f"bad {x}")

    with pytest.raises(ValueError, match=r"bad 7"):
        f(7)

    assert len(calls) == 1
    assert calls[0][0] == "exception"
    assert isinstance(calls[0][1], ValueError)


def test_002_sync_mixed_success_and_exception_sequences() -> None:
    """Records successes and exceptions in call order across repeated invocations."""
    calls: list[tuple[str, object]] = []

    @success_or_exception(
        on_success=lambda out: calls.append(("success", out)),
        on_exception=lambda e: calls.append(("exception", type(e))),
    )
    def f(x: int) -> int:
        if x < 0:
            raise ValueError("neg")
        return x + 1

    assert f(0) == 1

    with pytest.raises(ValueError, match=r"neg"):
        f(-1)

    assert f(2) == 3

    assert calls == [
        ("success", 1),
        ("exception", ValueError),
        ("success", 3),
    ]


@pytest.mark.asyncio
async def test_010_async_success_calls_on_success_only() -> None:
    """Calls on_success with the return value for async functions."""
    calls: list[tuple[str, object]] = []

    @success_or_exception(
        on_success=lambda out: calls.append(("success", out)),
        on_exception=lambda e: calls.append(("exception", e)),
    )
    async def f(x: int) -> int:
        return x + 1

    assert await f(2) == 3
    assert calls == [("success", 3)]


@pytest.mark.asyncio
async def test_011_async_exception_calls_on_exception_only_and_reraises() -> None:
    """Calls on_exception and re-raises for async functions that raise."""
    calls: list[tuple[str, object]] = []

    @success_or_exception(
        on_success=lambda out: calls.append(("success", out)),
        on_exception=lambda e: calls.append(("exception", e)),
    )
    async def f(x: int) -> int:
        raise RuntimeError(f"nope {x}")

    with pytest.raises(RuntimeError, match=r"nope 5"):
        await f(5)

    assert len(calls) == 1
    assert calls[0][0] == "exception"
    assert isinstance(calls[0][1], RuntimeError)


def test_020_preserves_wrapped_metadata() -> None:
    """Preserves __name__ and __doc__ via functools.wraps()."""
    calls: list[tuple[str, object]] = []

    @success_or_exception(
        on_success=lambda out: calls.append(("success", out)),
        on_exception=lambda e: calls.append(("exception", e)),
    )
    def my_func(x: int) -> int:
        """docstring should be preserved"""
        return x

    assert my_func.__name__ == "my_func"
    assert my_func.__doc__ == "docstring should be preserved"
