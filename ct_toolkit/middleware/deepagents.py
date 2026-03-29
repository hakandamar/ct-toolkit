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

from typing import Any, Dict, Optional, Callable
from ct_toolkit.core.wrapper import TheseusWrapper, WrapperConfig
from ct_toolkit.core.compression_guard import ContextCompressionGuard
from ct_toolkit.middleware.langchain import TheseusChatModel
from ct_toolkit.utils.logger import get_logger

logger = get_logger(__name__)


def _policy_metadata(
    wrapper: TheseusWrapper,
    model: str | None = None,
    role: str | None = None,
) -> Dict[str, Any]:
    """Build standardized CT policy metadata for Deep Agents surfaces."""
    return wrapper.propagate_policy_metadata(model=model, role=role)



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
    if wrapper_config and not wrapper_config.policy_role:
        wrapper_config.policy_role = "main"
    _wrapper = wrapper or TheseusWrapper(config=wrapper_config)
    ContextCompressionGuard(_wrapper, threshold=compression_threshold)

    def wrapped_create_deep_agent(*args: Any, **kwargs: Any) -> Any:
        # 1. Inject TheseusChatModel
        model = kwargs.get("model")
        model_name = model if isinstance(model, str) else None
        if isinstance(model, str) or model is None:
            kwargs["model"] = TheseusChatModel(
                wrapper=_wrapper,
                model=model if isinstance(model, str) else "gpt-4o-mini"
            )

        existing_metadata = kwargs.get("metadata")
        metadata = dict(existing_metadata) if isinstance(existing_metadata, dict) else {}
        metadata["ct_policy"] = _policy_metadata(
            _wrapper,
            model=model_name or kwargs["model"].model,
            role=_wrapper._config.policy_role,
        )
        kwargs["metadata"] = metadata

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
                "ct_identity_protection": True,
                "ct_policy": _policy_metadata(
                    wrapper,
                    role=wrapper._config.policy_role,
                ),
            }
        }
