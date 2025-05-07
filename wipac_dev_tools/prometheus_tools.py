"""Tools for Prometheus monitoring."""

from collections.abc import Callable
from functools import partialmethod, wraps
from typing import Any, Union

# 'prometheus' imports
try:
    from prometheus_client import (
        Counter,
        Gauge,
        Summary,
        Histogram,
        Info,
        Enum,
        disable_created_metrics,
    )
except (ImportError, ModuleNotFoundError) as e:
    raise ImportError(
        "the 'prometheus' option must be installed in order to use 'prometheus_tools'"
    ) from e

# https://prometheus.github.io/client_python/instrumenting/#disabling-_created-metrics
disable_created_metrics()

# fmt:off


class _MetricWrapper:
    def __init__(self, metric: Any, labels: dict):
        self.metric = metric
        self.common_labels = labels

    def labels(self, labels: dict) -> Any:
        labels = self.common_labels | labels
        return self.metric.labels(**labels)


class GlobalLabels:
    """
    Add global / common labels for all metrics.  Can be overridden.

    Example usage::

        metrics = GlobalLabels({"instance": "test-abc", "part": "a"})
        c = metrics.counter("thing", "The Thing")
        c.inc()
        # will have labels for instance and part

        c2 = metrics.counter("thing", "Thing 2", {"part": "b"})
        c2.inc()
        # will have labels for instance and part, with part=b

        c3 = metrics.counter("thing", "Thing 2", {"extra": "test"})
        c3.inc()
        # will have labels for instance, part, and extra
    """
    def __init__(self, labels: Union[dict, None] = None):
        self.common_labels = labels if labels else {}

    def _wrap(
        self,
        cls: Callable[..., Any],
        name: str,
        documentation: Union[str, None] = None,
        labels: Union[dict, list, None] = None,
        finalize: bool = True,
        **kwargs,
    ) -> Any:
        all_labels = self.common_labels.copy()
        if labels:
            if isinstance(labels, list):
                if finalize:
                    raise RuntimeError('cannot use a list of labels with finalize')
                labels = dict.fromkeys(labels, '')
            all_labels.update(labels)

        metric = cls(
            name,
            documentation=documentation,
            labelnames=list(all_labels),
            **kwargs
        )
        if finalize:
            return metric.labels(**all_labels)
        else:
            return _MetricWrapper(metric, all_labels)

    counter = partialmethod(_wrap, Counter)
    gauge = partialmethod(_wrap, Gauge)
    summary = partialmethod(_wrap, Summary)
    histogram = partialmethod(_wrap, Histogram)
    info = partialmethod(_wrap, Info)
    enum = partialmethod(_wrap, Enum)


def PromWrapper(prom_metric_fn):
    """
    Create a metric instance for a classmethod, using the class
    instance `self` during creation.  Pass the metric to the
    classmethod for use inside the function.

    Args:
        prom_metric_fn: function that returns a prometheus metric obj

    Example:
        @PromWrapper(lambda self: self.prom.counter('foo'))
        def func(self, prom_metric, my_arg):
            prom_metric.inc()
    """
    def wrapper(method):
        _metric = None

        @wraps(method)
        def _impl(self, *args, **kwargs):
            nonlocal _metric
            if not _metric:
                _metric = prom_metric_fn(self)
            return method(self, _metric, *args, **kwargs)
        return _impl
    return wrapper


def AsyncPromWrapper(prom_metric_fn):
    """
    Create a metric instance for a classmethod, using the class
    instance `self` during creation.  Pass the metric to the
    classmethod for use inside the function.

    Args:
        prom_metric_fn: function that returns a prometheus metric obj

    Example:
        @AsyncPromWrapper(lambda self: self.prom.counter('foo'))
        async def func(self, prom_metric, my_arg):
            prom_metric.inc()
    """
    def wrapper(method):
        _metric = None

        @wraps(method)
        async def _impl(self, *args, **kwargs):
            nonlocal _metric
            if not _metric:
                _metric = prom_metric_fn(self)
            return await method(self, _metric, *args, **kwargs)
        return _impl
    return wrapper


def PromTimer(prom_metric_fn):
    """
    Create a Histogram instance for a classmethod, using the class
    instance `self` during creation.  Time the classmethod using
    the histogram.

    Args:
        prom_metric_fn: function that returns a prometheus Histogram obj

    Example:
        @PromTimer(lambda self: self.prom.histogram('foo'))
        def func(self, my_arg):
            # do things
    """
    def wrapper(method):
        _metric = None

        @wraps(method)
        def _impl(self, *args, **kwargs):
            nonlocal _metric
            if not _metric:
                _metric = prom_metric_fn(self)
            with _metric.time():
                return method(self, *args, **kwargs)
        return _impl
    return wrapper


def AsyncPromTimer(prom_metric_fn):
    """
    Create a Histogram instance for a classmethod, using the class
    instance `self` during creation.  Time the classmethod using
    the histogram.

    Args:
        prom_metric_fn: function that returns a prometheus Histogram obj

    Example:
        @AsyncPromTimer(lambda self: self.prom.histogram('foo'))
        async def func(self, my_arg):
            # do things
    """
    def wrapper(method):
        _metric = None

        @wraps(method)
        async def _impl(self, *args, **kwargs):
            nonlocal _metric
            if not _metric:
                _metric = prom_metric_fn(self)
            with _metric.time():
                return await method(self, *args, **kwargs)
        return _impl
    return wrapper
