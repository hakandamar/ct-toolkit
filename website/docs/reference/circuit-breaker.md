# Circuit Breaker

Prevents cascading failures when LLM providers are down or rate-limited.

The Circuit Breaker pattern monitors LLM API calls and automatically fails fast when a service is experiencing issues, protecting your application from cascading failures.

## Overview

The circuit breaker has three states:

| State | Description |
|-------|-------------|
| **CLOSED** | Normal operation. Requests flow through to the LLM provider. |
| **OPEN** | Failures exceeded threshold. Requests fail fast without calling the API. |
| **HALF_OPEN** | Testing recovery. A limited number of requests are allowed through to test if the service has recovered. |

## Basic Usage

```python
from ct_toolkit.core import CircuitBreaker, CircuitBreakerError

# Create a circuit breaker
breaker = CircuitBreaker(
    name="openai-api",
    failure_threshold=5,        # Open circuit after 5 consecutive failures
    recovery_timeout=30.0,      # Test recovery after 30 seconds
)

# Use with context manager
try:
    with breaker:
        response = litellm.completion(model="gpt-4", messages=[...])
except CircuitBreakerError as e:
    # Circuit is open - use fallback or return error
    print(f"Circuit breaker is {e.state.value}. Retry after {e.retry_after:.1f}s")
```

## CircuitBreaker Class

### Constructor

```python
CircuitBreaker(
    name: str = "default",
    failure_threshold: int = 5,
    recovery_timeout: float = 30.0,
    half_open_max_calls: int = 1,
)
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | `"default"` | Human-readable name for logging |
| `failure_threshold` | `int` | `5` | Consecutive failures before opening circuit |
| `recovery_timeout` | `float` | `30.0` | Seconds to wait before testing recovery |
| `half_open_max_calls` | `int` | `1` | Max concurrent calls in half-open state |

### Methods

| Method | Description |
|--------|-------------|
| `record_success()` | Record a successful call |
| `record_failure()` | Record a failed call |
| `allow_request() -> bool` | Check if request should be allowed |
| `time_until_recovery() -> float` | Seconds until circuit may transition to half-open |
| `reset()` | Manually reset to closed state |
| `get_stats() -> CircuitBreakerStats` | Get current statistics |

### State Transitions

```
CLOSED ──[failures ≥ threshold]──→ OPEN
OPEN ──[recovery_timeout elapsed]─→ HALF_OPEN
HALF_OPEN ──[success]─────────────→ CLOSED
HALF_OPEN ──[failure]─────────────→ OPEN
```

## CircuitBreakerRegistry

Global registry for managing multiple circuit breakers:

```python
from ct_toolkit.core import CircuitBreakerRegistry

# Get or create breaker for a provider
breaker = CircuitBreakerRegistry.global_instance().get_or_create(
    name="openai-api",
    failure_threshold=5,
    recovery_timeout=30.0,
)

# Get all stats
stats = CircuitBreakerRegistry.global_instance().get_all_stats()

# Reset all breakers
CircuitBreakerRegistry.global_instance().reset_all()
```

## CircuitBreakerStats

Statistics for monitoring:

```python
stats = breaker.get_stats()
print(f"Total requests: {stats.total_requests}")
print(f"Success rate: {stats.success_rate:.1f}%")
print(f"Failure rate: {stats.failure_rate:.1f}%")
print(f"Current state: {stats.current_state}")
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `total_requests` | `int` | Total requests through this breaker |
| `successful_requests` | `int` | Successful requests |
| `failed_requests` | `int` | Failed requests |
| `rejected_requests` | `int` | Requests rejected due to open circuit |
| `success_rate` | `float` | Success percentage |
| `failure_rate` | `float` | Failure percentage |
| `current_state` | `str` | Current circuit state |
| `last_failure_time` | `float` | Timestamp of last failure |

## Infrastructure Error Detection

The circuit breaker only counts infrastructure errors, not business logic errors:

- **Counted as failures:** `ConnectionError`, `Timeout`, `RateLimitError`, `APIConnectionError`
- **Not counted:** Validation errors, prompt errors, content policy violations