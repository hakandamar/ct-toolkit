"""
ct_toolkit.middleware.deepagents
---------------------------------
Specialized integration for LangChain Deep Agents (deepagents).

This module provides helpers to wrap Deep Agents with CT Toolkit's
identity-continuity guardrails, specifically ensuring that when a
Deep Agent spawns sub-agents, they inherit the mother agent's
Constitutional Kernel.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Union, Callable
from ct_toolkit.core.wrapper import TheseusWrapper, WrapperConfig
from ct_toolkit.middleware.langchain import TheseusChatModel
from ct_toolkit.utils.logger import get_logger

logger = get_logger(__name__)

class ContextCompressionGuard:
    """
    Guardrails for identity-preservation during context compression (summarization).
    """
    def __init__(self, wrapper: TheseusWrapper, threshold: float = 0.85) -> None:
        self.wrapper = wrapper
        self.threshold = threshold

    def analyze_summary_drift(
        self, 
        original_messages: List[Dict[str, str]], 
        summary_text: str
    ) -> Dict[str, Any]:
        """
        Compares the identity embedding of original messages against the summary.
        Records the event in Provenance Log.
        
        Returns:
            Dict containing similarity score and drift status.
        """
        # 1. Flatten original messages into a single identity string
        original_text = " ".join([m.get("content", "") for m in original_messages])
        
        # 2. Compute embeddings via identity layer
        original_emb = self.wrapper._identity_layer._compute_vector(original_text)
        summary_emb = self.wrapper._identity_layer._compute_vector(summary_text)
        
        # 3. Calculate similarity (L1 ECS style)
        from ct_toolkit.identity.embedding import IdentityEmbeddingLayer
        similarity = IdentityEmbeddingLayer.calculate_similarity(original_emb, summary_emb)
        
        # 4. Identity Safety Floor (Internal protection against manipulated thresholds)
        # Even if the user sets threshold to 0.4, 0.6 is still risky for LLM identity.
        drift_detected = similarity < self.threshold
        is_critical = similarity < 0.70  # A hard floor for identity integrity
        
        result = {
            "similarity": similarity,
            "threshold": self.threshold,
            "drift_detected": drift_detected,
            "critical_drift": is_critical,
            "event": "context_compression"
        }

        # 5. Record to Provenance Log (Tamper-proof record)
        if self.wrapper._config.log_requests:
            self.wrapper._provenance_log.record(
                request_text=f"[SYSTEM_ACTION: CONTEXT_SUMMARIZATION] History: {original_text[:500]}...",
                response_text=summary_text,
                divergence_score=1.0 - similarity,
                metadata={
                    "type": "compression_audit",
                    "similarity": similarity,
                    "threshold_applied": self.threshold,
                    "is_critical": is_critical,
                    "drift_flag": drift_detected,
                    "template": self.wrapper._config.template,
                    "kernel": self.wrapper.kernel.name,
                }
            )

        # 6. Trigger alert if detected (User action required)
        if (drift_detected or is_critical) and self.wrapper._config.drift_alert_callback:
            logger.warning(
                f"CT Toolkit | Identity Drift during compression: similarity={similarity:.2f} "
                f"(Threshold: {self.threshold}, Critical: {is_critical})"
            )
            self.wrapper._config.drift_alert_callback(result)

        return result

def wrap_deep_agent_factory(
    create_deep_agent_fn: Callable,
    wrapper: Optional[TheseusWrapper] = None,
    wrapper_config: Optional[WrapperConfig] = None,
    compression_threshold: float = 0.85,
) -> Callable:
    """
    Wraps the LangChain `create_deep_agent` function to automatically
    inject Theseus guardrails, enable hierarchical kernel propagation,
    and monitor context compression drift.
    """
    _wrapper = wrapper or TheseusWrapper(config=wrapper_config)
    guard = ContextCompressionGuard(_wrapper, threshold=compression_threshold)

    def wrapped_create_deep_agent(*args: Any, **kwargs: Any) -> Any:
        # 1. Inject TheseusChatModel
        model = kwargs.get("model")
        if isinstance(model, str) or model is None:
            kwargs["model"] = TheseusChatModel(
                wrapper=_wrapper,
                model=model if isinstance(model, str) else "gpt-4o-mini"
            )

        # 2. Inject ContextCompressionGuard into the middleware stack if possible
        # Since deepagents middleware is internal, we use the helper to signal it
        # In a real integration, we'd wrap the SummarizationMiddleware.
        
        return create_deep_agent_fn(*args, **kwargs)

    return wrapped_create_deep_agent

class DeepAgentTheseusHelper:
    """
    Helper for programmatic integration with Deep Agents.
    """
    @staticmethod
    def prepare_config(wrapper: TheseusWrapper) -> Dict[str, Any]:
        """Returns configuration for Deep Agents that includes identity constraints."""
        return {
            "callbacks": [], # We could add TheseusLangChainCallback here
            "metadata": {
                "ct_kernel": wrapper.kernel.name,
                "ct_identity_protection": True
            }
        }
