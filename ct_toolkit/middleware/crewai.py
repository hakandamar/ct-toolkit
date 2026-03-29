"""
ct_toolkit.middleware.crewai
-----------------------------
CrewAI v1.10+ integration for hierarchical kernel propagation.

Provides ``TheseusCrewMiddleware`` which wraps each agent's LLM inside a
``TheseusChatModel`` so that the manager's Constitutional Kernel is
propagated as a read-only constraint to every sub-agent automatically.

Optional dependency — requires ``pip install 'ct-toolkit[crewai]'``.
CrewAI does NOT need to be installed for the rest of ct-toolkit to work;
imports are guarded by a try/except block.

Compatible with crewai >= 1.10.

Usage::

    from ct_toolkit import TheseusWrapper
    from ct_toolkit.middleware.crewai import TheseusCrewMiddleware
    from crewai import Agent, Crew, Task, Process

    manager_wrapper = TheseusWrapper(provider="openai", kernel_name="defense")

    researcher = Agent(role="Researcher", goal="...", backstory="...", llm=your_llm)
    writer     = Agent(role="Writer",     goal="...", backstory="...", llm=your_llm)
    crew = Crew(agents=[researcher, writer], tasks=[...], process=Process.hierarchical)

    # Apply CT Toolkit guardrails — wraps every agent's LLM with parent kernel
    TheseusCrewMiddleware.apply_to_crew(crew, manager_wrapper)
    crew.kickoff()
"""
from __future__ import annotations

from typing import Any, List, Optional

from ct_toolkit.core.wrapper import TheseusWrapper, WrapperConfig
from ct_toolkit.utils.logger import get_logger

logger = get_logger(__name__)


def _attach_policy_metadata(target: Any, metadata: dict[str, Any]) -> None:
    """Attach standardized CT policy metadata to CrewAI objects."""
    setattr(target, "ct_policy", metadata)
    existing_metadata = getattr(target, "metadata", None)
    merged_metadata = dict(existing_metadata) if isinstance(existing_metadata, dict) else {}
    merged_metadata["ct_policy"] = metadata
    setattr(target, "metadata", merged_metadata)


class TheseusCrewMiddleware:
    """
    Middleware that propagates the manager agent's Constitutional Kernel
    to all sub-agents in a CrewAI Crew.

    CrewAI agents expose an ``llm`` attribute (a LangChain-compatible
    BaseChatModel or a model string).  This middleware replaces that llm
    with a ``TheseusChatModel`` that carries the parent kernel as read-only
    constraints.
    """

    @staticmethod
    def apply_to_crew(
        crew: Any,
        manager_wrapper: TheseusWrapper,
        *,
        model: str = "gpt-4o-mini",
    ) -> None:
        """
        Wrap every agent in *crew* to enforce the manager's kernel.

        Args:
            crew:            A CrewAI ``Crew`` instance.
            manager_wrapper: The manager agent's ``TheseusWrapper``; its
                             kernel is propagated as read-only to sub-agents.
            model:           Default model string for the inner
                             ``TheseusChatModel`` (used when the agent's
                             original llm cannot be introspected).
        """
        # Lazy import so tests can run without crewai installed
        try:
            from ct_toolkit.middleware.langchain import TheseusChatModel
        except ImportError as exc:
            raise ImportError(
                "TheseusChatModel requires langchain-core. "
                "Install with: pip install 'ct-toolkit[langchain]'"
            ) from exc

        agents: List[Any] = getattr(crew, "agents", [])
        wrapped_count = 0

        _attach_policy_metadata(
            crew,
            manager_wrapper.propagate_policy_metadata(
                model=model,
                role=manager_wrapper._config.policy_role,
            ),
        )

        for agent in agents:
            if not hasattr(agent, "llm"):
                logger.debug(f"Agent '{getattr(agent, 'role', '?')}' has no llm attribute — skipping.")
                continue

            # Detect model name from existing llm if possible
            agent_model = _extract_model_name(agent.llm) or model

            sub_config = WrapperConfig(
                parent_kernel=manager_wrapper.kernel,
                vault_path=manager_wrapper._config.vault_path,
                template=manager_wrapper._config.template,
                policy_role="sub",
                compression_threshold=manager_wrapper._config.compression_threshold,
                compression_passive_detection=manager_wrapper._config.compression_passive_detection,
            )
            agent.llm = TheseusChatModel(
                provider=manager_wrapper._provider,
                model=agent_model,
                wrapper_config=sub_config,
            )
            _attach_policy_metadata(agent, agent.llm.policy_metadata)
            wrapped_count += 1
            logger.info(
                f"CT Toolkit | CrewAI agent '{getattr(agent, 'role', '?')}' "
                f"wrapped with TheseusChatModel (parent_kernel='{manager_wrapper.kernel.name}')"
            )

        logger.info(
            f"CT Toolkit | CrewAI crew wrapped: {wrapped_count}/{len(agents)} agents protected."
        )

    @staticmethod
    def wrap_agent(
        agent: Any,
        manager_wrapper: TheseusWrapper,
        *,
        model: str = "gpt-4o-mini",
    ) -> None:
        """
        Wrap a single CrewAI agent's LLM with the parent kernel.

        Useful for selectively protecting high-risk agents rather than the
        entire crew.
        """
        try:
            from ct_toolkit.middleware.langchain import TheseusChatModel
        except ImportError as exc:
            raise ImportError(
                "TheseusChatModel requires langchain-core. "
                "Install with: pip install 'ct-toolkit[langchain]'"
            ) from exc

        agent_model = _extract_model_name(getattr(agent, "llm", None)) or model
        sub_config = WrapperConfig(
            parent_kernel=manager_wrapper.kernel,
            vault_path=manager_wrapper._config.vault_path,
            template=manager_wrapper._config.template,
            policy_role="sub",
            compression_threshold=manager_wrapper._config.compression_threshold,
            compression_passive_detection=manager_wrapper._config.compression_passive_detection,
        )
        agent.llm = TheseusChatModel(
            provider=manager_wrapper._provider,
            model=agent_model,
            wrapper_config=sub_config,
        )
        _attach_policy_metadata(agent, agent.llm.policy_metadata)
        logger.info(
            f"CT Toolkit | CrewAI agent '{getattr(agent, 'role', '?')}' "
            f"individually wrapped with TheseusChatModel."
        )


# ── helpers ────────────────────────────────────────────────────────────────────

def _extract_model_name(llm: Any) -> Optional[str]:
    """Best-effort extraction of a model identifier from a CrewAI llm object."""
    if llm is None:
        return None
    if isinstance(llm, str):
        return llm
    # LangChain BaseChatModel-like objects
    for attr in ("model", "model_name", "model_id"):
        val = getattr(llm, attr, None)
        if isinstance(val, str):
            return val
    return None
