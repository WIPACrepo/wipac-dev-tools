from functools import partialmethod

from prometheus_client import (
    Counter,
    Gauge,
    Summary,
    Histogram,
    Info,
    Enum,
)
from prometheus_client import disable_created_metrics

# https://prometheus.github.io/client_python/instrumenting/#disabling-_created-metrics
disable_created_metrics()


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
    def __init__(self, labels=None):
        self.common_labels = labels if labels else {}

    def _wrap(self, cls, name, documentation=None, labels=None, **kwargs):
        all_labels = self.common_labels.copy()
        if labels:
            all_labels.update(labels)
        return cls(
            name,
            documentation=documentation,
            labelnames=list(all_labels),
            **kwargs
        ).labels(**all_labels)

    counter = partialmethod(_wrap, Counter)
    gauge = partialmethod(_wrap, Gauge)
    summary = partialmethod(_wrap, Summary)
    histogram = partialmethod(_wrap, Histogram)
    info = partialmethod(_wrap, Info)
    enum = partialmethod(_wrap, Enum)
