"""
Tests for ct_toolkit.core.circuit_breaker
"""
import time
import pytest
from ct_toolkit.core.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerError,
    CircuitBreakerRegistry,
    CircuitState,
    CircuitBreakerStats,
)


class TestCircuitBreaker:
    """Tests for CircuitBreaker class."""

    def test_initial_state_closed(self):
        cb = CircuitBreaker(name="test")
        assert cb.state == CircuitState.CLOSED

    def test_allow_request_when_closed(self):
        cb = CircuitBreaker(name="test")
        assert cb.allow_request() is True

    def test_record_success(self):
        cb = CircuitBreaker(name="test")
        cb.record_success()
        assert cb.stats.successful_requests == 1
        assert cb.stats.total_requests == 1

    def test_record_failure_does_not_open_below_threshold(self):
        cb = CircuitBreaker(name="test", failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED

    def test_opens_after_threshold(self):
        cb = CircuitBreaker(name="test", failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_rejects_requests_when_open(self):
        cb = CircuitBreaker(name="test", failure_threshold=1)
        cb.record_failure()
        assert cb.allow_request() is False
        assert cb.stats.rejected_requests >= 1

    def test_transition_to_half_open_after_timeout(self):
        cb = CircuitBreaker(name="test", failure_threshold=1, recovery_timeout=0.1)
        cb.record_failure()
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN

    def test_recovery_on_success_in_half_open(self):
        cb = CircuitBreaker(name="test", failure_threshold=1, recovery_timeout=0.1)
        cb.record_failure()
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_returns_to_open_on_failure_in_half_open(self):
        cb = CircuitBreaker(name="test", failure_threshold=1, recovery_timeout=0.1)
        cb.record_failure()
        time.sleep(0.15)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_context_manager_records_success(self):
        cb = CircuitBreaker(name="test")
        with cb:
            pass  # Simulate successful call
        assert cb.stats.successful_requests == 1

    def test_context_manager_records_failure(self):
        cb = CircuitBreaker(name="test", failure_threshold=1)
        # Simulate context manager with an exception
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_context_manager_raises_circuit_breaker_error(self):
        cb = CircuitBreaker(name="test", failure_threshold=1)
        cb.record_failure()
        with pytest.raises(CircuitBreakerError):
            with cb:
                pass

    def test_reset(self):
        cb = CircuitBreaker(name="test", failure_threshold=1)
        cb.record_failure()
        cb.reset()
        assert cb.state == CircuitState.CLOSED
        assert cb.stats.failed_requests == 1  # Stats preserved

    def test_time_until_recovery(self):
        cb = CircuitBreaker(name="test", failure_threshold=1, recovery_timeout=1.0)
        cb.record_failure()
        wait_time = cb.time_until_recovery()
        assert 0.5 < wait_time <= 1.0

    def test_time_until_recovery_when_not_open(self):
        cb = CircuitBreaker(name="test")
        assert cb.time_until_recovery() == 0.0

    def test_stats_success_rate(self):
        cb = CircuitBreaker(name="test")
        cb.record_success()
        cb.record_success()
        cb.record_failure()
        stats = cb.get_stats()
        assert stats.success_rate == pytest.approx(66.67, rel=0.01)

    def test_get_stats_returns_dict(self):
        cb = CircuitBreaker(name="test")
        cb.record_success()
        d = cb.get_stats().to_dict()
        assert "total_requests" in d
        assert "successful_requests" in d


class TestCircuitBreakerError:
    """Tests for CircuitBreakerError."""

    def test_error_message(self):
        err = CircuitBreakerError(CircuitState.OPEN, retry_after=5.0)
        assert "open" in str(err).lower()
        assert "5.0" in str(err)
        assert err.retry_after == 5.0


class TestCircuitBreakerRegistry:
    """Tests for CircuitBreakerRegistry."""

    def test_creates_breaker_on_demand(self):
        reg = CircuitBreakerRegistry()
        cb = reg.get_or_create("test-api")
        assert cb is not None
        assert cb.name == "test-api"

    def test_returns_same_breaker(self):
        reg = CircuitBreakerRegistry()
        cb1 = reg.get_or_create("test-api")
        cb2 = reg.get_or_create("test-api")
        assert cb1 is cb2

    def test_get_nonexistent_returns_none(self):
        reg = CircuitBreakerRegistry()
        assert reg.get("nonexistent") is None

    def test_get_all_stats(self):
        reg = CircuitBreakerRegistry()
        reg.get_or_create("api-1").record_success()
        reg.get_or_create("api-2").record_failure()
        stats = reg.get_all_stats()
        assert "api-1" in stats
        assert "api-2" in stats

    def test_reset_all(self):
        reg = CircuitBreakerRegistry()
        cb = reg.get_or_create("api-1", failure_threshold=1)
        cb.record_failure()
        reg.reset_all()
        assert cb.state == CircuitState.CLOSED