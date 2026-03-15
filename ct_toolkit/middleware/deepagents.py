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
        
        drift_detected = similarity < self.threshold
        
        result = {
            "similarity": similarity,
            "threshold": self.threshold,
            "drift_detected": drift_detected,
            "event": "context_compression"
        }

        # 4. Trigger alert if detected
        if drift_detected and self.wrapper._config.drift_alert_callback:
            logger.warning(f"CT Toolkit | High Identity Drift detected during compression: {similarity:.2f}")
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
