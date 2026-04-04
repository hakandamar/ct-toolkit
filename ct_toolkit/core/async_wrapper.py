"""
ct_toolkit.core.async_wrapper
==============================
Async support for TheseusWrapper LLM calls.

Provides:
- AsyncTheseusWrapper: Async-compatible wrapper around TheseusWrapper
- Async compatible circuit breaker integration

Usage:
    async with AsyncTheseusWrapper(client) as wrapper:
        response = await wrapper.chat("Hello!")
"""
from __future__ import annotations

import asyncio
import time
from typing import Any, Optional
from pathlib import Path

from ct_toolkit.core.wrapper import TheseusWrapper, CTResponse, WrapperConfig
from ct_toolkit.core.circuit_breaker import CircuitBreaker, CircuitBreakerError, CircuitBreakerRegistry
from ct_toolkit.utils.metrics import get_metrics_collector, MetricsCollector
from ct_toolkit.utils.logger import get_logger

logger = get_logger(__name__)


class AsyncTheseusWrapper:
    """
    Async-compatible TheseusWrapper.
    
    Provides async-compatible LLM calls with circuit breaker and metrics integration.
    
    Usage:
        wrapper = AsyncTheseusWrapper(provider="openai")
        response = await wrapper.chat("Hello!")
        
        # With circuit breaker
        wrapper = AsyncTheseusWrapper(provider="openai", enable_circuit_breaker=True)
    """
    
    def __init__(
        self,
        client: Any = None,
        config: Optional[WrapperConfig] = None,
        *,
        provider: Optional[str] = None,
        enable_circuit_breaker: bool = True,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_recovery: float = 30.0,
        metrics_enabled: bool = True,
    ) -> None:
        self._sync_wrapper = TheseusWrapper(
            client=client,
            config=config,
            provider=provider,
        )
        self._metrics_enabled = metrics_enabled
        self._metrics = get_metrics_collector() if metrics_enabled else None
        
        # Circuit breaker
        self._circuit_breaker: Optional[CircuitBreaker] = None
        if enable_circuit_breaker:
            provider_name = self._sync_wrapper._provider or "unknown"
            self._circuit_breaker = CircuitBreakerRegistry.global_instance().get_or_create(
                name=f"llm-{provider_name}",
                failure_threshold=circuit_breaker_threshold,
                recovery_timeout=circuit_breaker_recovery,
            )
            logger.info(f"AsyncTheseusWrapper: Circuit breaker enabled for '{provider_name}'")
    
    @property
    def sync_wrapper(self) -> TheseusWrapper:
        """Get the underlying sync wrapper."""
        return self._sync_wrapper
    
    async def chat(
        self,
        message: str,
        *,
        model: Optional[str] = None,
        system: Optional[str] = None,
        history: Optional[list[dict[str, str]]] = None,
        **kwargs: Any,
    ) -> CTResponse:
        """
        Send a message asynchronously and get response with identity protection.
        
        Uses run_in_executor to make sync LLM calls non-blocking.
        """
        if self._metrics:
            self._metrics.increment("llm.requests.async.total", tags={
                "provider": self._sync_wrapper._provider or "unknown",
            })
        
        start_time = time.monotonic()
        
        try:
            # Run sync wrapper in executor to not block event loop
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._sync_wrapper.chat(
                    message,
                    model=model,
                    system=system,
                    history=history,
                    **kwargs,
                )
            )
            
            # Record metrics
            latency = time.monotonic() - start_time
            if self._metrics:
                self._metrics.record("llm.latency.async.seconds", latency, tags={
                    "provider": self._sync_wrapper._provider or "unknown",
                    "model": response.model,
                })
                self._metrics.increment("llm.requests.async.success", tags={
                    "provider": self._sync_wrapper._provider or "unknown",
                    "success": "true",
                })
            
            return response
            
        except CircuitBreakerError as e:
            # Circuit breaker is already tracking this
            if self._metrics:
                self._metrics.increment("llm.requests.async.circuit_breaker", tags={
                    "provider": self._sync_wrapper._provider or "unknown",
                    "state": e.state.value,
                })
            logger.warning(f"Circuit breaker open for LLM call: {e}")
            raise
        
        except Exception as e:
            # Record failure
            latency = time.monotonic() - start_time
            if self._metrics:
                self._metrics.record("llm.latency.async.seconds", latency, tags={
                    "provider": self._sync_wrapper._provider or "unknown",
                })
                self._metrics.increment("llm.requests.async.failure", tags={
                    "provider": self._sync_wrapper._provider or "unknown",
                    "success": "false",
                    "error": type(e).__name__,
                })
            
            # Record circuit breaker failure if applicable
            if self._circuit_breaker:
                try:
                    self._circuit_breaker.record_failure()
                except Exception:
                    pass
            
            logger.error(f"Async LLM call failed: {type(e).__name__}: {e}")
            raise
    
    async def health_check(self) -> dict[str, Any]:
        """
        Check health of the LLM connection.
        
        Returns status of circuit breaker and basic connectivity.
        """
        result: dict[str, Any] = {
            "provider": self._sync_wrapper._provider or "unknown",
            "status": "healthy",
            "circuit_breaker": None,
        }
        
        if self._circuit_breaker:
            cb_state = self._circuit_breaker.state
            cb_stats = self._circuit_breaker.get_stats().to_dict()
            result["circuit_breaker"] = {
                "state": cb_state.value,
                "stats": cb_stats,
                "time_until_recovery": self._circuit_breaker.time_until_recovery(),
            }
            if cb_state.value == "open":
                result["status"] = "degraded"
        
        return result
    
    def get_metrics(self) -> Optional[dict[str, Any]]:
        """Get current metrics."""
        if not self._metrics:
            return None
        return self._metrics.get_all()
    
    def get_circuit_breaker_stats(self) -> Optional[dict[str, Any]]:
        """Get circuit breaker statistics."""
        if not self._circuit_breaker:
            return None
        return self._circuit_breaker.get_stats().to_dict()
    
    def reset_circuit_breaker(self) -> None:
        """Manually reset the circuit breaker."""
        if self._circuit_breaker:
            self._circuit_breaker.reset()
            logger.info("Circuit breaker manually reset")


def create_async_wrapper(
    provider: str = "openai",
    model: Optional[str] = None,
    enable_circuit_breaker: bool = True,
    metrics_enabled: bool = True,
) -> AsyncTheseusWrapper:
    """
    Factory function to create an AsyncTheseusWrapper.
    
    Args:
        provider: LLM provider name.
        model: Optional model override.
        enable_circuit_breaker: Enable circuit breaker protection.
        metrics_enabled: Enable metrics collection.
    
    Returns:
        Configured AsyncTheseusWrapper instance.
    """
    return AsyncTheseusWrapper(
        provider=provider,
        enable_circuit_breaker=enable_circuit_breaker,
        metrics_enabled=metrics_enabled,
    )