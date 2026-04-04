# AsyncTheseusWrapper

Async-compatible TheseusWrapper with circuit breaker integration and automatic metrics collection.

## Overview

`AsyncTheseusWrapper` provides async/await support for LLM calls while maintaining all identity protection features. It uses `run_in_executor` internally to make sync LLM calls non-blocking in async applications.

## Basic Usage

```python
import asyncio
from ct_toolkit.core.async_wrapper import AsyncTheseusWrapper

async def main():
    wrapper = AsyncTheseusWrapper(
        provider="openai",
        enable_circuit_breaker=True,
        metrics_enabled=True,
    )
    
    response = await wrapper.chat(
        "Hello, world!",
        model="gpt-4",
        system="You are a helpful assistant.",
    )
    
    print(f"Response: {response.content}")
    print(f"Divergence: {response.divergence_score}")

asyncio.run(main())
```

## Constructor

```python
AsyncTheseusWrapper(
    client: Any = None,
    config: WrapperConfig | None = None,
    *,
    provider: str | None = None,
    enable_circuit_breaker: bool = True,
    circuit_breaker_threshold: int = 5,
    circuit_breaker_recovery: float = 30.0,
    metrics_enabled: bool = True,
)
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `client` | `Any` | `None` | LLM client (same as TheseusWrapper) |
| `config` | `WrapperConfig \| None` | `None` | Wrapper configuration |
| `provider` | `str \| None` | `None` | LLM provider name |
| `enable_circuit_breaker` | `bool` | `True` | **New:** Enable circuit breaker protection |
| `circuit_breaker_threshold` | `int` | `5` | **New:** Failures before opening circuit |
| `circuit_breaker_recovery` | `float` | `30.0` | **New:** Seconds before testing recovery |
| `metrics_enabled` | `bool` | `True` | **New:** Enable automatic metrics collection |

## Methods

### `chat(message, *, model, system, history, **kwargs) → CTResponse`

Async version of the chat method. Uses run_in_executor internally.

```python
response = await wrapper.chat(
    "What are your values?",
    model="gpt-4",
    system="Additional context.",
    history=[{"role": "user", "content": "Hello"}],
)
```

### `health_check() → dict`

Check health of the LLM connection and circuit breaker status.

```python
health = await wrapper.health_check()
print(health)
# {
#     "provider": "openai",
#     "status": "healthy",  # or "degraded"
#     "circuit_breaker": {
#         "state": "closed",
#         "stats": {"total_requests": 100, "success_rate": 98.5, ...},
#         "time_until_recovery": 0.0,
#     }
# }
```

### `get_metrics() → dict | None`

Get current metrics as a dictionary.

```python
metrics = wrapper.get_metrics()
if metrics:
    print(f"Total requests: {metrics['counters']['ct_toolkit.llm.requests.total']}")
```

### `get_circuit_breaker_stats() → dict | None`

Get circuit breaker statistics.

```python
stats = wrapper.get_circuit_breaker_stats()
print(f"Circuit breaker state: {stats['current_state']}")
```

### `reset_circuit_breaker() → None`

Manually reset the circuit breaker to closed state.

```python
wrapper.reset_circuit_breaker()
```

## Factory Function

```python
from ct_toolkit.core.async_wrapper import create_async_wrapper

# Quick factory for common use cases
wrapper = create_async_wrapper(
    provider="openai",
    enable_circuit_breaker=True,
    metrics_enabled=True,
)
```

## Metrics Integration

Metrics are automatically collected for all async LLM calls:

| Metric | Description |
|--------|-------------|
| `llm.requests.async.total` | Total async requests |
| `llm.requests.async.success` | Successful async requests |
| `llm.requests.async.failure` | Failed async requests |
| `llm.requests.async.circuit_breaker` | Requests rejected by CB |
| `llm.latency.async.seconds` | Async request latency |

## Circuit Breaker States

The circuit breaker automatically protects against LLM provider failures:

| State | Behavior |
|-------|----------|
| **CLOSED** | Normal operation |
| **OPEN** | Requests fail fast with `CircuitBreakerError` |
| **HALF_OPEN** | Testing recovery with limited requests |

```python
from ct_toolkit.core import CircuitBreakerError

try:
    response = await wrapper.chat("Hello!", model="gpt-4")
except CircuitBreakerError as e:
    print(f"Circuit is {e.state.value}. Retry after {e.retry_after:.1f}s")
```

## Properties

### `sync_wrapper → TheseusWrapper`

Access the underlying sync wrapper.

```python
sync = wrapper.sync_wrapper
print(f"Kernel: {sync.kernel.name}")