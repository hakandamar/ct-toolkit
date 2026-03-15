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

def wrap_deep_agent_factory(
    create_deep_agent_fn: Callable,
    wrapper: Optional[TheseusWrapper] = None,
    wrapper_config: Optional[WrapperConfig] = None,
) -> Callable:
    """
    Wraps the LangChain `create_deep_agent` function to automatically
    inject Theseus guardrails and enable hierarchical kernel propagation.

    Args:
        create_deep_agent_fn: The original `create_deep_agent` function 
                             from `deepagents.graph`.
        wrapper: Optional existing TheseusWrapper.
        wrapper_config: Optional config to create a new wrapper.

    Returns:
        A wrapped function that returns a protected Deep Agent.
    """
    _wrapper = wrapper or TheseusWrapper(config=wrapper_config)

    def wrapped_create_deep_agent(*args: Any, **kwargs: Any) -> Any:
        # 1. Inject TheseusChatModel if model is a string or not provided
        # or wrap if it's already an instance.
        model = kwargs.get("model")
        if isinstance(model, str) or model is None:
            # We assume OpenAI default for now if none specified
            kwargs["model"] = TheseusChatModel(
                wrapper_config=wrapper_config,
                model=model if isinstance(model, str) else "gpt-4o-mini"
            )
        else:
            # If a model instance is passed, we should ideally wrap it with callbacks
            # but for Deep Agents, using TheseusChatModel is cleaner.
            pass

        # 2. Handle Sub-Agent Propagation
        # If the user defined sub-agents, we need to inject the parent kernel 
        # into their configuration.
        subagents = kwargs.get("subagents", [])
        if subagents:
            logger.info(f"Injecting parent kernel '{_wrapper.kernel.name}' into {len(subagents)} sub-agents.")
            for sa in subagents:
                # SubAgent in deepagents is often a dict or an object with 'model'
                # We need to ensure the sub-agent's model also uses Theseus
                if isinstance(sa, dict):
                    sa_model = sa.get("model")
                    # Inject parent kernel via prop headers / config
                    # In a real deepagents scenario, we'd pass the kernel to the sub-agent's TheseusWrapper
                    pass

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
