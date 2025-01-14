from pprint import pprint

import pytest
from prometheus_client import REGISTRY, GC_COLLECTOR, PLATFORM_COLLECTOR, PROCESS_COLLECTOR
from wipac_dev_tools import prometheus_tools as prometheus

# disable these for testing
REGISTRY.unregister(GC_COLLECTOR)
REGISTRY.unregister(PLATFORM_COLLECTOR)
REGISTRY.unregister(PROCESS_COLLECTOR)


@pytest.fixture(autouse=True)
def clear_registry():
    collectors = tuple(REGISTRY._collector_to_names.keys())
    for collector in collectors:
        REGISTRY.unregister(collector)
    yield


def test_counter():
    gl = prometheus.GlobalLabels({"foo": "bar"})
    c = gl.counter('test', "Test labels")
    c.inc()

    pprint(list(REGISTRY.collect()))
    metric = REGISTRY.get_sample_value('test_total', {
        "foo": "bar"
    })
    assert metric == 1


def test_counter_extra_labels():
    gl = prometheus.GlobalLabels({"foo": "bar"})
    c = gl.counter('test', "Test labels", {"part": "baz"})
    for _ in range(10):
        c.inc()

    pprint(list(REGISTRY.collect()))
    metric = REGISTRY.get_sample_value('test_total', {
        "foo": "bar",
        "part": "baz",
    })
    assert metric == 10


def test_gauge():
    gl = prometheus.GlobalLabels({"foo": "bar"})
    g = gl.gauge('test', "Test labels")
    g.set(12)

    pprint(list(REGISTRY.collect()))
    metric = REGISTRY.get_sample_value('test', {
        "foo": "bar"
    })
    assert metric == 12


def test_summary():
    gl = prometheus.GlobalLabels({"foo": "bar"})
    s = gl.summary('test', "Test labels")
    s.observe(0.35)
    s.observe(1.234)

    pprint(list(REGISTRY.collect()))
    metric = REGISTRY.get_sample_value('test_count', {
        "foo": "bar"
    })
    assert metric == 2

    metric = REGISTRY.get_sample_value('test_sum', {
        "foo": "bar"
    })
    assert metric == 0.35 + 1.234


def test_histogram():
    gl = prometheus.GlobalLabels({"foo": "bar"})
    s = gl.histogram('test', "Test labels")
    s.observe(0.35)
    s.observe(1.234)

    pprint(list(REGISTRY.collect()))
    metric = REGISTRY.get_sample_value('test_count', {
        "foo": "bar"
    })
    assert metric == 2

    metric = REGISTRY.get_sample_value('test_sum', {
        "foo": "bar"
    })
    assert metric == 0.35 + 1.234


def test_info():
    gl = prometheus.GlobalLabels({"foo": "bar"})
    s = gl.info('test', "Test labels")
    s.info({"version": "1.2.3"})

    pprint(list(REGISTRY.collect()))
    metric = REGISTRY.get_sample_value('test_info', {
        "foo": "bar",
        "version": "1.2.3",
    })
    assert metric == 1


def test_enum():
    gl = prometheus.GlobalLabels({"foo": "bar"})
    s = gl.enum('test', "Test labels", states=['start', 'stop'])
    s.state("stop")

    pprint(list(REGISTRY.collect()))
    metric = REGISTRY.get_sample_value('test', {
        "foo": "bar",
        "test": "start"
    })
    assert metric == 0

    metric = REGISTRY.get_sample_value('test', {
        "foo": "bar",
        "test": "stop"
    })
    assert metric == 1
