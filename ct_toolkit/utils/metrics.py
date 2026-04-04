"""
ct_toolkit.utils.metrics
========================
Simple metrics collection for monitoring and observability.

Provides:
- MetricsCollector: Thread-safe metrics collection
- Counter, Gauge, Histogram metric types
- Export to dict for Prometheus/OpenTelemetry integration

Usage:
    metrics = MetricsCollector()
    metrics.increment("llm.requests.total", tags={"provider": "openai"})
    metrics.record("llm.latency.seconds", 0.5, tags={"model": "gpt-4"})
    stats = metrics.get_all()
"""
from __future__ import annotations

import time
import math
import threading
from typing import Any
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class CounterMetric:
    """A monotonically increasing counter."""
    name: str
    value: float = 0.0
    tags: dict[str, str] = field(default_factory=dict)
    
    def increment(self, amount: float = 1.0) -> None:
        self.value += amount


@dataclass
class GaugeMetric:
    """A metric that can go up or down."""
    name: str
    value: float = 0.0
    tags: dict[str, str] = field(default_factory=dict)
    
    def set(self, value: float) -> None:
        self.value = value
    
    def increment(self, amount: float = 1.0) -> None:
        self.value += amount
    
    def decrement(self, amount: float = 1.0) -> None:
        self.value -= amount


@dataclass
class HistogramMetric:
    """Tracks distribution of values (min, max, sum, count)."""
    name: str
    count: int = 0
    sum: float = 0.0
    min: float = float('inf')
    max: float = float('-inf')
    tags: dict[str, str] = field(default_factory=dict)
    
    @property
    def average(self) -> float:
        return self.sum / self.count if self.count > 0 else 0.0
    
    def record(self, value: float) -> None:
        self.count += 1
        self.sum += value
        if value < self.min:
            self.min = value
        if value > self.max:
            self.max = value
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "count": self.count,
            "sum": round(self.sum, 4),
            "min": round(self.min, 4) if self.min != float('inf') else 0.0,
            "max": round(self.max, 4) if self.max != float('-inf') else 0.0,
            "avg": round(self.average, 4),
            "tags": self.tags,
        }


class _MetricKey:
    """Hashable key for metric identification."""
    def __init__(self, name: str, tags: dict[str, str] | None = None):
        self.name = name
        self.tags = tuple(sorted((tags or {}).items()))
    
    def __hash__(self) -> int:
        return hash((self.name, self.tags))
    
    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, _MetricKey):
            return False
        return self.name == other.name and self.tags == other.tags


class MetricsCollector:
    """
    Thread-safe metrics collection and export.
    
    Collects counters, gauges, and histograms for observability.
    Exports to dict for integration with monitoring systems.
    
    Usage:
        collector = MetricsCollector()
        collector.counter("llm.requests", tags={"provider": "openai"})
        collector.histogram("llm.latency", tags={"model": "gpt-4"})
        
        # Record metrics
        collector.increment("llm.requests", tags={"provider": "openai"})
        with collector.timer("llm.latency", tags={"model": "gpt-4"}):
            call_llm()
        
        # Export
        stats = collector.get_all()
    """
    
    def __init__(self, prefix: str = "ct_toolkit") -> None:
        self._prefix = prefix
        self._counters: dict[_MetricKey, CounterMetric] = {}
        self._gauges: dict[_MetricKey, GaugeMetric] = {}
        self._histograms: dict[_MetricKey, HistogramMetric] = {}
        self._lock = threading.RLock()
    
    def _full_name(self, name: str) -> str:
        """Build fully qualified metric name."""
        if self._prefix:
            return f"{self._prefix}.{name}"
        return name
    
    def _counter_key(self, name: str, tags: dict[str, str] | None = None) -> _MetricKey:
        return _MetricKey(self._full_name(name), tags)
    
    def _gauge_key(self, name: str, tags: dict[str, str] | None = None) -> _MetricKey:
        return _MetricKey(self._full_name(name), tags)
    
    def _histogram_key(self, name: str, tags: dict[str, str] | None = None) -> _MetricKey:
        return _MetricKey(self._full_name(name), tags)
    
    # ── Counter Operations ────────────────────────────────────────────────────
    
    def counter(self, name: str, tags: dict[str, str] | None = None ) -> CounterMetric:
        """Get or create a counter."""
        key = self._counter_key(name, tags)
        with self._lock:
            if key not in self._counters:
                self._counters[key] = CounterMetric(
                    name=self._full_name(name),
                    value=0.0,
                    tags=dict(tags or {}),
                )
            return self._counters[key]
    
    def increment(self, name: str, tags: dict[str, str] | None = None, amount: float = 1.0) -> None:
        """Increment a counter."""
        self.counter(name, tags).increment(amount)
    
    # ── Gauge Operations ──────────────────────────────────────────────────────────
        
    def gauge(self, name: str, tags: dict[str, str] | None = None) -> GaugeMetric:
        """Get or create a gauge."""
        key = self._gauge_key(name, tags)
        with self._lock:
            if key not in self._gauges:
                self._gauges[key] = GaugeMetric(
                    name=self._full_name(name),
                    value=0.0,
                    tags=dict(tags or {}),
                )
            return self._gauges[key]
    
    def set_gauge(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        """Set a gauge value."""
        self.gauge(name, tags).set(value)
    
    def increment_gauge(self, name: str, amount: float = 1.0, tags: dict[str, str] | None = None) -> None:
        """Increment a gauge."""
        self.gauge(name, tags).increment(amount)
    
    def decrement_gauge(self, name: str, amount: float = 1.0, tags: dict[str, str] | None = None) -> None:
        """Decrement a gauge."""
        self.gauge(name, tags).decrement(amount)
    
    # ── Histogram Operations ────────────────────────────────────────────────────
    
    def histogram(self, name: str, tags: dict[str, str] | None = None) -> HistogramMetric:
        """Get or create a histogram."""
        key = self._histogram_key(name, tags)
        with self._lock:
            if key not in self._histograms:
                self._histograms[key] = HistogramMetric(
                    name=self._full_name(name),
                    tags=dict(tags or {}),
                )
            return self._histograms[key]
    
    def record(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        """Record a value in a histogram."""
        self.histogram(name, tags).record(value)
    
    # ── Timer Context Manager ──────────────────────────────────────────────────
    
    class _TimerContext:
        """Context manager for timing operations."""
        def __init__(self, collector: "MetricsCollector", metric_name: str, tags: dict[str, str] | None):
            self._collector = collector
            self._metric_name = metric_name
            self._tags = tags
            self._start_time = 0.0
            self._elapsed = 0.0
        
        def __enter__(self) -> "MetricsCollector._TimerContext":
            self._start_time = time.monotonic()
            return self
        
        def __exit__(self, *args: Any) -> None:
            self._elapsed = time.monotonic() - self._start_time
            self._collector.record(self._metric_name, self._elapsed, self._tags)
        
        @property
        def elapsed(self) -> float:
            return time.monotonic() - self._start_time if self._start_time > 0 else 0.0
    
    def timer(self, metric_name: str, tags: dict[str, str] | None = None) -> _TimerContext:
        """Create a timer context manager.
        
        Usage:
            with collector.timer("llm.latency", tags={"model": "gpt-4"}):
                call_llm()
        """
        return self._TimerContext(self, metric_name, tags)

    # ── Export ─────────────────────────────────────────────────────────────────
    
    def get_all(self) -> dict[str, Any]:
        """Get all metrics as a dictionary."""
        with self._lock:
            result: dict[str, Any] = {
                "counters": {},
                "gauges": {},
                "histograms": {},
            }
            
            for key, counter in self._counters.items():
                result["counters"][counter.name] = {
                    "value": round(counter.value, 2),
                    "tags": counter.tags,
                }
            
            for key, gauge in self._gauges.items():
                result["gauges"][gauge.name] = {
                    "value": round(gauge.value, 4),
                    "tags": gauge.tags,
                }
            
            for key, histogram in self._histograms.items():
                result["histograms"][histogram.name] = histogram.to_dict()
            
            return result
    
    def get_counters(self) -> dict[str, dict[str, Any]]:
        """Get only counter metrics."""
        with self._lock:
            return {
                counter.name: {"value": round(counter.value, 2), "tags": counter.tags}
                for counter in self._counters.values()
            }
    
    def get_histograms(self) -> dict[str, dict[str, Any]]:
        """Get only histogram metrics."""
        with self._lock:
            return {h.name: h.to_dict() for h in self._histograms.values()}
    
    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
    
    def reset_counter(self, name: str, tags: dict[str, str] | None = None) -> None:
        """Reset a specific counter."""
        key = self._counter_key(name, tags)
        with self._lock:
            if key in self._counters:
                self._counters[key].value = 0.0
    
    # ── Pre-defined Metrics for LLM Monitoring ──────────────────────────────────
    
    def record_llm_request(self, provider: str, model: str, latency: float, success: bool = True) -> None:
        """Record an LLM request with standard metrics."""
        tags = {"provider": provider, "model": model}
        success_tags = {**tags, "success": str(success)}
        
        # Total requests
        self.increment("llm.requests.total", tags=tags)
        
        # Success/failure counts
        if success:
            self.increment("llm.requests.success", tags=tags)
        else:
            self.increment("llm.requests.failure", tags=tags)
        
        # Latency histogram
        self.record("llm.latency.seconds", latency, tags=tags)
    
    def record_llm_error(self, provider: str, error_type: str, model: str = "unknown") -> None:
        """Record an LLM API error."""
        tags = {"provider": provider, "error_type": error_type, "model": model}
        self.increment("llm.errors.total", tags=tags)
    
    def record_divergence_score(self, template: str, kernel: str, score: float) -> None:
        """Record a divergence score."""
        tags = {"template": template, "kernel": kernel}
        self.record("divergence.score", score, tags=tags)
        self.increment("divergence.evaluations.total", tags=tags)
    
    def record_circuit_breaker_state(self, name: str, state: str) -> None:
        """Record circuit breaker state change."""
        self.set_gauge("circuit_breaker.state", 1.0, tags={"name": name, "state": state})


# ── Global Metrics Collector ──────────────────────────────────────────────────

_global_collector: MetricsCollector | None = None
_global_lock = threading.Lock()


def get_metrics_collector(prefix: str = "ct_toolkit") -> MetricsCollector:
    """Get the global metrics collector instance."""
    global _global_collector
    if _global_collector is None:
        with _global_lock:
            if _global_collector is None:
                _global_collector = MetricsCollector(prefix=prefix)
    return _global_collector