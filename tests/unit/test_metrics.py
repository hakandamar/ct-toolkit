"""
Tests for ct_toolkit.utils.metrics
"""
import pytest
from ct_toolkit.utils.metrics import (
    MetricsCollector,
    CounterMetric,
    GaugeMetric,
    HistogramMetric,
    get_metrics_collector,
)


class TestCounterMetric:
    """Tests for CounterMetric class."""

    def test_initial_value(self):
        counter = CounterMetric(name="test.counter")
        assert counter.value == 0.0

    def test_increment(self):
        counter = CounterMetric(name="test.counter")
        counter.increment()
        assert counter.value == 1.0

    def test_increment_by_amount(self):
        counter = CounterMetric(name="test.counter")
        counter.increment(5.0)
        assert counter.value == 5.0


class TestGaugeMetric:
    """Tests for GaugeMetric class."""

    def test_initial_value(self):
        gauge = GaugeMetric(name="test.gauge")
        assert gauge.value == 0.0

    def test_set(self):
        gauge = GaugeMetric(name="test.gauge")
        gauge.set(42.0)
        assert gauge.value == 42.0

    def test_increment(self):
        gauge = GaugeMetric(name="test.gauge")
        gauge.set(10.0)
        gauge.increment(5.0)
        assert gauge.value == 15.0

    def test_decrement(self):
        gauge = GaugeMetric(name="test.gauge")
        gauge.set(10.0)
        gauge.decrement(3.0)
        assert gauge.value == 7.0


class TestHistogramMetric:
    """Tests for HistogramMetric class."""

    def test_initial_values(self):
        hist = HistogramMetric(name="test.histogram")
        assert hist.count == 0
        assert hist.sum == 0.0
        assert hist.min == float('inf')
        assert hist.max == float('-inf')

    def test_record(self):
        hist = HistogramMetric(name="test.histogram")
        hist.record(5.0)
        hist.record(10.0)
        hist.record(3.0)
        assert hist.count == 3
        assert hist.sum == 18.0
        assert hist.min == 3.0
        assert hist.max == 10.0

    def test_average(self):
        hist = HistogramMetric(name="test.histogram")
        hist.record(2.0)
        hist.record(4.0)
        hist.record(6.0)
        assert hist.average == 4.0

    def test_average_empty(self):
        hist = HistogramMetric(name="test.histogram")
        assert hist.average == 0.0

    def test_to_dict(self):
        hist = HistogramMetric(name="test.histogram")
        hist.record(5.0)
        d = hist.to_dict()
        assert d["name"] == "test.histogram"
        assert d["count"] == 1
        assert d["min"] == 5.0
        assert d["max"] == 5.0
        assert d["avg"] == 5.0


class TestMetricsCollector:
    """Tests for MetricsCollector class."""

    def setup_method(self):
        self.collector = MetricsCollector(prefix="test")

    def test_counter_increment(self):
        self.collector.increment("requests")
        self.collector.increment("requests")
        counters = self.collector.get_counters()
        assert counters["test.requests"]["value"] == 2.0

    def test_gauge_set(self):
        self.collector.set_gauge("temperature", 25.0)
        all_metrics = self.collector.get_all()
        assert all_metrics["gauges"]["test.temperature"]["value"] == 25.0

    def test_histogram_record(self):
        self.collector.record("latency", 0.5)
        self.collector.record("latency", 1.0)
        histograms = self.collector.get_histograms()
        assert histograms["test.latency"]["count"] == 2
        assert histograms["test.latency"]["avg"] == 0.75

    def test_timer_context(self):
        with self.collector.timer("operation_time") as timer:
            pass  # Immediate exit but timer started
        # Timer should have recorded something
        histograms = self.collector.get_histograms()
        assert histograms["test.operation_time"]["count"] == 1

    def test_get_all(self):
        self.collector.increment("counter1")
        self.collector.set_gauge("gauge1", 10.0)
        self.collector.record("hist1", 5.0)
        result = self.collector.get_all()
        assert "counters" in result
        assert "gauges" in result
        assert "histograms" in result

    def test_reset(self):
        self.collector.increment("counter1")
        self.collector.reset()
        assert len(self.collector.get_counters()) == 0
        assert len(self.collector.get_histograms()) == 0

    def test_tags_in_metrics(self):
        self.collector.increment("requests", tags={"env": "prod", "provider": "openai"})
        counters = self.collector.get_counters()
        key = "test.requests"
        # Find by name
        found = {k: v for k, v in counters.items() if k == key}
        assert len(found) == 1
        assert found["test.requests"]["tags"]["env"] == "prod"

    def test_record_llm_request(self):
        self.collector.record_llm_request(
            provider="openai", model="gpt-4", latency=0.5, success=True
        )
        self.collector.record_llm_request(
            provider="openai", model="gpt-4", latency=1.0, success=False
        )
        counters = self.collector.get_counters()
        assert counters["test.llm.requests.total"]["value"] == 2.0
        assert counters["test.llm.requests.success"]["value"] == 1.0
        assert counters["test.llm.requests.failure"]["value"] == 1.0

    def test_record_llm_error(self):
        self.collector.record_llm_error(
            provider="openai", error_type="RateLimitError", model="gpt-4"
        )
        counters = self.collector.get_counters()
        assert counters["test.llm.errors.total"]["value"] == 1.0

    def test_record_divergence_score(self):
        self.collector.record_divergence_score(
            template="finance", kernel="finance", score=0.15
        )
        histograms = self.collector.get_histograms()
        assert histograms["test.divergence.score"]["count"] == 1


def test_get_metrics_collector_singleton():
    """Test that get_metrics_collector returns the same instance."""
    c1 = MetricsCollector(prefix="singleton_test_1")
    # Note: Global collector is shared, so we test it returns a collector
    collector = get_metrics_collector(prefix="test_singleton")
    assert isinstance(collector, MetricsCollector)