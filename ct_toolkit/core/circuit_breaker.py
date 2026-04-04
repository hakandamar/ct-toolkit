"""
ct_toolkit.core.circuit_breaker
===============================
Circuit breaker pattern implementation for LLM API calls.

Prevents cascading failures when LLM providers are down or rate-limited.

States:
- CLOSED: Normal operation, requests flow through
- OPEN: Failures exceeded threshold, requests fail fast
- HALF_OPEN: Testing if service has recovered

Usage:
    breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=30.0)
    with breaker:
        response = litellm.completion(...)
"""
from __future__ import annotations

import time
import threading
from enum import Enum
from typing import Callable, Any
from dataclasses import dataclass, field

from ct_toolkit.utils.logger import get_logger

logger = get_logger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Failing fast, no requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerStats:
    """Statistics for a circuit breaker."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rejected_requests: int = 0  # Rejected due to open circuit
    last_failure_time: float = 0.0
    last_success_time: float = 0.0
    state_changes: int = 0
    last_state_change: float = 0.0
    current_state: str = CircuitState.CLOSED.value
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as a percentage."""
        if self.total_requests == 0:
            return 100.0
        return (self.successful_requests / self.total_requests) * 100
    
    @property
    def failure_rate(self) -> float:
        """Calculate failure rate as a percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.failed_requests / self.total_requests) * 100
    
    def to_dict(self) -> dict[str, Any]:
        """Export stats as dictionary."""
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "rejected_requests": self.rejected_requests,
            "success_rate": round(self.success_rate, 2),
            "failure_rate": round(self.failure_rate, 2),
            "current_state": self.current_state,
            "last_failure_time": self.last_failure_time,
            "last_state_change": self.last_state_change,
        }


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open and request is rejected."""
    def __init__(self, state: CircuitState, retry_after: float = 0.0):
        self.state = state
        self.retry_after = retry_after
        super().__init__(
            f"Circuit breaker is {state.value}. Request rejected. "
            f"Retry after {retry_after:.1f}s."
        )


class CircuitBreaker:
    """
    Circuit breaker for external service calls.
    
    Prevents cascading failures by failing fast when a service is down,
    and automatically testing for recovery.
    
    Args:
        name: Human-readable name for logging.
        failure_threshold: Number of consecutive failures before opening circuit.
        recovery_timeout: Seconds to wait before testing recovery (half-open).
        half_open_max_calls: Max concurrent calls in half-open state.
    
    Usage:
        breaker = CircuitBreaker(
            name="openai-api",
            failure_threshold=5,
            recovery_timeout=30.0
        )
        
        try:
            with breaker:
                response = litellm.completion(...)
        except CircuitBreakerError:
            # Handle circuit open - use fallback or return error
            pass
    """
    
    def __init__(
        self,
        name: str = "default",
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 1,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._half_open_calls = 0
        self._lock = threading.RLock()
        
        # Stats
        self.stats = CircuitBreakerStats()
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit state, checking for recovery timeout."""
        with self._lock:
            if self._state == CircuitState.OPEN:
                if self._time_since_last_failure() >= self.recovery_timeout:
                    self._transition_to(CircuitState.HALF_OPEN)
            return self._state
    
    def _time_since_last_failure(self) -> float:
        """Time in seconds since the last failure."""
        if self.stats.last_failure_time == 0:
            return float('inf')
        return time.time() - self.stats.last_failure_time
    
    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition the circuit to a new state."""
        old_state = self._state
        self._state = new_state
        self.stats.state_changes += 1
        self.stats.last_state_change = time.time()
        self.stats.current_state = new_state.value
        
        if new_state == CircuitState.HALF_OPEN:
            self._half_open_calls = 0
            logger.info(
                f"CircuitBreaker '{self.name}: {old_state.value} -> {new_state.value} | "
                f"Testing recovery after {self._time_since_last_failure():.1f}s"
            )
        elif new_state == CircuitState.CLOSED:
            self._failure_count = 0
            logger.info(
                f"CircuitBreaker '{self.name}': {old_state.value} -> {new_state.value} | "
                f"Recovered after {self.stats.state_changes} state changes"
            )
        else:  # OPEN
            logger.warning(
                f"CircuitBreaker '{self.name}': {old_state.value} -> {new_state.value} | "
                f"Failure threshold ({self.failure_threshold}) reached. "
                f"Will retry in {self.recovery_timeout}s"
            )
    
    def record_success(self) -> None:
        """Record a successful call."""
        with self._lock:
            self.stats.total_requests += 1
            self.stats.successful_requests += 1
            self.stats.last_success_time = time.time()
            
            if self._state == CircuitState.HALF_OPEN:
                # Success in half-open means recovery
                self._transition_to(CircuitState.CLOSED)
    
    def record_failure(self) -> None:
        """Record a failed call."""
        with self._lock:
            self.stats.total_requests += 1
            self.stats.failed_requests += 1
            self.stats.last_failure_time = time.time()
            
            if self._state == CircuitState.HALF_OPEN:
                # Failure in half-open means back to open
                self._transition_to(CircuitState.OPEN)
            elif self._state == CircuitState.CLOSED:
                self._failure_count += 1
                if self._failure_count >= self.failure_threshold:
                    self._transition_to(CircuitState.OPEN)
    
    def allow_request(self) -> bool:
        """Check if a request should be allowed."""
        with self._lock:
            current_state = self.state  # This may trigger state transition
            
            if current_state == CircuitState.CLOSED:
                return True
            
            if current_state == CircuitState.HALF_OPEN:
                if self._half_open_calls < self.half_open_max_calls:
                    self._half_open_calls += 1
                    return True
                return False
            
            # OPEN - reject all requests
            self.stats.rejected_requests += 1
            return False
    
    def time_until_recovery(self) -> float:
        """Time in seconds until circuit may transition to half-open."""
        if self._state != CircuitState.OPEN:
            return 0.0
        elapsed = self._time_since_last_failure()
        return max(0.0, self.recovery_timeout - elapsed)
    
    def __enter__(self) -> CircuitBreaker:
        """Context manager entry - checks if request is allowed."""
        if not self.allow_request():
            retry_after = self.time_until_recovery()
            self.stats.rejected_requests += 1
            raise CircuitBreakerError(self.state, retry_after)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - records success or failure."""
        if exc_type is None:
            self.record_success()
        else:
            # Don't count business logic errors as circuit failures
            # Only count API/connection errors
            if self._is_infrastructure_error(exc_type):
                self.record_failure()
    
    @staticmethod
    def _is_infrastructure_error(exc_type: type | None) -> bool:
        """Check if error is an infrastructure error (API down, timeout, etc.)."""
        if exc_type is None:
            return False
        
        error_names = [
            "ConnectionError", "Timeout", "TimeoutError",
            "RateLimitError", "APISconnectionError",
            "ServiceUnavailable", "BadGateway",
            "RateLimit",
        ]
        
        exc_name = exc_type.__name__
        return any(name in exc_name for name in error_names)
    
    def reset(self) -> None:
        """Manually reset the circuit breaker to closed state."""
        with self._lock:
            self._failure_count = 0
            self._half_open_calls = 0
            self._transition_to(CircuitState.CLOSED)
    
    def get_stats(self) -> CircuitBreakerStats:
        """Get a copy of current stats."""
        with self._lock:
            self.stats.current_state = self.state.value
            return CircuitBreakerStats(**{
                k: v for k, v in self.stats.__dict__.items()
                if not k.startswith('_')
            })


# ── Global Circuit Breaker Registry ──────────────────────────────────────────

class CircuitBreakerRegistry:
    """
    Global registry for circuit breakers.
    
    Provides a centralized way to manage circuit breakers for different services.
    
    Usage:
        registry = CircuitBreakerRegistry()
        breaker = registry.get_or_create("openai", failure_threshold=5)
        with breaker:
            response = call_openai()
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __init__(self) -> None:
        self._breakers: dict[str, CircuitBreaker] = {}
        self._registry_lock = threading.Lock()
    
    @classmethod
    def global_instance(cls) -> "CircuitBreakerRegistry":
        """Get the global singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def get_or_create(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
    ) -> CircuitBreaker:
        """Get existing circuit breaker or create a new one."""
        with self._registry_lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(
                    name=name,
                    failure_threshold=failure_threshold,
                    recovery_timeout=recovery_timeout,
                )
                logger.info(f"CircuitBreaker '{name}' created")
            return self._breakers[name]
    
    def get(self, name: str) -> CircuitBreaker | None:
        """Get existing circuit breaker by name."""
        return self._breakers.get(name)
    
    def get_all_stats(self) -> dict[str, dict[str, Any]]:
        """Get stats for all registered breakers."""
        result = {}
        with self._registry_lock:
            for name, breaker in self._breakers.items():
                result[name] = breaker.get_stats().to_dict()
        return result
    
    def reset_all(self) -> None:
        """Reset all circuit breakers."""
        with self._registry_lock:
            for breaker in self._breakers.values():
                breaker.reset()