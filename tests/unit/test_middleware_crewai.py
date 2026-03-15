"""
tests/unit/test_middleware_crewai.py
--------------------------------------
Unit tests for ct_toolkit.middleware.crewai.TheseusCrewMiddleware.
Uses mocks — does NOT require crewai to be installed.
"""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from ct_toolkit.middleware.crewai import TheseusCrewMiddleware, _extract_model_name
from ct_toolkit.core.wrapper import TheseusWrapper, WrapperConfig


# ── fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def manager_wrapper(tmp_path):
    config = WrapperConfig(vault_path=str(tmp_path / "mgr.db"))
    return TheseusWrapper(provider="openai", config=config)


def _make_agent(role: str, model: str = "gpt-4o-mini") -> MagicMock:
    """Return a mock CrewAI Agent."""
    agent = MagicMock()
    agent.role = role
    agent.llm = MagicMock()
    agent.llm.model = model
    return agent


def _make_crew(*agents) -> MagicMock:
    """Return a mock CrewAI Crew."""
    crew = MagicMock()
    crew.agents = list(agents)
    return crew


# ── TheseusCrewMiddleware.apply_to_crew ────────────────────────────────────────

class TestApplyToCrew:

    def test_wraps_all_agents_with_theseus_chat_model(self, manager_wrapper):
        """Every agent in the crew should have its llm replaced."""
        from ct_toolkit.middleware.langchain import TheseusChatModel

        researcher = _make_agent("Researcher")
        writer     = _make_agent("Writer")
        crew       = _make_crew(researcher, writer)

        TheseusCrewMiddleware.apply_to_crew(crew, manager_wrapper)

        assert isinstance(researcher.llm, TheseusChatModel)
        assert isinstance(writer.llm, TheseusChatModel)

    def test_parent_kernel_propagated_to_sub_agents(self, manager_wrapper):
        """Each wrapped agent's TheseusChatModel should carry the parent kernel."""
        agent = _make_agent("Analyst")
        crew  = _make_crew(agent)

        TheseusCrewMiddleware.apply_to_crew(crew, manager_wrapper)

        sub_kernel = agent.llm.wrapper._config.parent_kernel
        assert sub_kernel is not None
        assert sub_kernel.name == manager_wrapper.kernel.name

    def test_agent_without_llm_attribute_is_skipped(self, manager_wrapper):
        """Agents that have no llm attribute should not crash the middleware."""
        agent_no_llm = MagicMock(spec=["role"])     # no llm attribute  
        agent_no_llm.role = "NoLLM"
        crew = _make_crew(agent_no_llm)

        # Should complete without raising
        TheseusCrewMiddleware.apply_to_crew(crew, manager_wrapper)

    def test_empty_crew_does_not_crash(self, manager_wrapper):
        crew = _make_crew()
        TheseusCrewMiddleware.apply_to_crew(crew, manager_wrapper)

    def test_model_name_preserved_from_existing_llm(self, manager_wrapper):
        """Model name should be extracted from the original llm."""
        agent = _make_agent("Analyst", model="claude-3-5-haiku-latest")
        crew  = _make_crew(agent)

        TheseusCrewMiddleware.apply_to_crew(crew, manager_wrapper)

        assert agent.llm.model == "claude-3-5-haiku-latest"


# ── TheseusCrewMiddleware.wrap_agent ───────────────────────────────────────────

class TestWrapAgent:

    def test_wrap_single_agent(self, manager_wrapper):
        """wrap_agent should replace a single agent's llm."""
        from ct_toolkit.middleware.langchain import TheseusChatModel

        agent = _make_agent("Coder")
        TheseusCrewMiddleware.wrap_agent(agent, manager_wrapper)

        assert isinstance(agent.llm, TheseusChatModel)

    def test_wrap_agent_parent_kernel_set(self, manager_wrapper):
        agent = _make_agent("Reviewer")
        TheseusCrewMiddleware.wrap_agent(agent, manager_wrapper)

        assert agent.llm.wrapper._config.parent_kernel is not None


# ── _extract_model_name helper ─────────────────────────────────────────────────

class TestExtractModelName:

    def test_returns_string_llm_directly(self):
        assert _extract_model_name("gpt-4o") == "gpt-4o"

    def test_reads_model_attribute(self):
        llm = MagicMock()
        llm.model = "gpt-4o-mini"
        assert _extract_model_name(llm) == "gpt-4o-mini"

    def test_reads_model_name_attribute(self):
        llm = MagicMock(spec=["model_name"])
        llm.model_name = "claude-haiku"
        assert _extract_model_name(llm) == "claude-haiku"

    def test_returns_none_for_none(self):
        assert _extract_model_name(None) is None

    def test_returns_none_for_unknown_object(self):
        llm = MagicMock(spec=[])  # no model / model_name
        assert _extract_model_name(llm) is None
