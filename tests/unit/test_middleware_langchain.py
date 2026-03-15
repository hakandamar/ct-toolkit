"""
tests/unit/test_middleware_langchain.py
---------------------------------------
Unit tests for ct_toolkit.middleware.langchain.
Tests cover TheseusLangChainCallback and TheseusChatModel.
"""
import pytest
from uuid import uuid4
from unittest.mock import MagicMock, patch, PropertyMock

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.outputs import LLMResult, ChatGeneration, Generation

from ct_toolkit.middleware.langchain import TheseusLangChainCallback, TheseusChatModel
from ct_toolkit.core.wrapper import TheseusWrapper, WrapperConfig
from ct_toolkit.core.exceptions import AxiomaticViolationError


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def wrapper(tmp_path):
    config = WrapperConfig(vault_path=str(tmp_path / "test.db"))
    return TheseusWrapper(provider="openai", config=config)


@pytest.fixture
def callback(wrapper):
    return TheseusLangChainCallback(wrapper)


# ── TheseusLangChainCallback ──────────────────────────────────────────────────

class TestTheseusLangChainCallback:

    def test_on_llm_start_stores_run_prompt(self, callback):
        """on_llm_start should store the prompt text keyed by run_id."""
        run_id = uuid4()
        callback.on_llm_start({}, ["Hello AI"], run_id=run_id)
        assert run_id in callback._run_prompts
        assert "Hello AI" in callback._run_prompts[run_id]

    def test_on_llm_start_passes_for_clean_prompt(self, callback):
        """Non-conflicting prompts should raise no errors."""
        run_id = uuid4()
        callback.on_llm_start({}, ["Tell me about climate change."], run_id=run_id)

    def test_on_chat_model_start_validates_messages(self, callback):
        """on_chat_model_start should store user message text for the run."""
        run_id = uuid4()
        messages = [[HumanMessage(content="What is identity drift?")]]
        callback.on_chat_model_start({}, messages, run_id=run_id)
        assert "identity drift" in callback._run_prompts[run_id]

    def test_on_chat_model_start_skips_non_string_content(self, callback):
        """Messages with non-string content (e.g. image bytes) should not crash."""
        run_id = uuid4()
        msg = HumanMessage(content=[{"type": "image_url", "image_url": "..."}])
        callback.on_chat_model_start({}, [[msg]], run_id=run_id)

    def test_on_llm_end_triggers_divergence_and_logs(self, callback, wrapper):
        """on_llm_end should invoke the divergence engine and record provenance."""
        run_id = uuid4()
        callback._run_prompts[run_id] = "What is your purpose?"

        generation = Generation(text="I am a helpful and safe assistant.")
        result = LLMResult(generations=[[generation]])

        with patch.object(wrapper, "_run_divergence_engine", wraps=wrapper._run_divergence_engine) as mock_div, \
             patch.object(wrapper._provenance_log, "record", return_value="test-id") as mock_record:
            callback.on_llm_end(result, run_id=run_id)

        mock_div.assert_called_once()
        mock_record.assert_called_once()
        # run_id should be cleaned up
        assert run_id not in callback._run_prompts

    def test_on_llm_end_handles_chat_generation(self, callback, wrapper):
        """on_llm_end should handle ChatGeneration objects (.message.content)."""
        run_id = uuid4()
        callback._run_prompts[run_id] = "Greet me."

        ai_msg = AIMessage(content="Hello! I'm here to help.")
        generation = ChatGeneration(message=ai_msg)
        result = LLMResult(generations=[[generation]])

        with patch.object(wrapper._provenance_log, "record", return_value="id-1"):
            callback.on_llm_end(result, run_id=run_id)

        assert run_id not in callback._run_prompts

    def test_on_llm_end_warns_on_cascade_blocked(self, callback, wrapper):
        """A cascade_blocked result should trigger a warning log."""
        run_id = uuid4()
        callback._run_prompts[run_id] = "Dangerous request"

        # Mock divergence engine to return cascade_blocked=True
        from ct_toolkit.divergence.engine import DivergenceResult, DivergenceTier
        blocked_result = DivergenceResult(
            tier=DivergenceTier.CRITICAL,
            l1_score=0.9,
            action_required=True,
            cascade_blocked=True,
            summary="Critical divergence",
        )

        generation = Generation(text="Unsafe content.")
        result = LLMResult(generations=[[generation]])

        with patch.object(wrapper, "_run_divergence_engine", return_value=blocked_result), \
             patch.object(wrapper._provenance_log, "record", return_value="id-x"), \
             patch("ct_toolkit.middleware.langchain.logger") as mock_logger:
            callback.on_llm_end(result, run_id=run_id)

        mock_logger.warning.assert_called_once()
        assert "cascade_blocked" in mock_logger.warning.call_args[0][0]

    def test_on_llm_error_cleans_up_run_context(self, callback):
        """on_llm_error should remove the run_id from the prompt store."""
        run_id = uuid4()
        callback._run_prompts[run_id] = "Some prompt"
        callback.on_llm_error(ValueError("API error"), run_id=run_id)
        assert run_id not in callback._run_prompts

    def test_on_llm_end_no_crash_on_empty_content(self, callback):
        """on_llm_end should silently skip empty generation content."""
        run_id = uuid4()
        callback._run_prompts[run_id] = "Something"
        generation = Generation(text="")
        result = LLMResult(generations=[[generation]])
        callback.on_llm_end(result, run_id=run_id)  # should not raise


# ── TheseusChatModel ──────────────────────────────────────────────────────────

class TestTheseusChatModel:

    def test_llm_type(self):
        """_llm_type must return the correct identifier."""
        llm = TheseusChatModel.__new__(TheseusChatModel)
        assert llm._llm_type == "theseus-chat-model"

    def test_extract_user_text(self):
        """Non-system messages are concatenated; system messages are ignored."""
        messages = [
            SystemMessage(content="You are helpful."),
            HumanMessage(content="Hello"),
        ]
        text = TheseusChatModel._extract_user_text(messages)
        assert text == "Hello"
        assert "helpful" not in text

    def test_extract_system(self):
        """System message content is returned correctly."""
        messages = [
            SystemMessage(content="Be ethical."),
            HumanMessage(content="Hi"),
        ]
        system = TheseusChatModel._extract_system(messages)
        assert system == "Be ethical."

    def test_extract_system_returns_none_if_missing(self):
        messages = [HumanMessage(content="Hi")]
        assert TheseusChatModel._extract_system(messages) is None

    def test_generate_calls_wrapper_chat(self, tmp_path):
        """_generate should delegate to TheseusWrapper.chat and return AIMessage."""
        config = WrapperConfig(vault_path=str(tmp_path / "chat.db"))
        llm = TheseusChatModel(provider="openai", model="gpt-4o-mini", wrapper_config=config)

        from ct_toolkit.core.wrapper import CTResponse
        mock_response = CTResponse(
            content="I am a safe assistant.",
            provider="openai",
            model="gpt-4o-mini",
            divergence_score=0.05,
            divergence_tier="ok",
            provenance_id="prov-001",
        )

        messages = [
            SystemMessage(content="Be helpful."),
            HumanMessage(content="What is safety?"),
        ]

        with patch.object(llm.wrapper, "chat", return_value=mock_response) as mock_chat:
            result = llm._generate(messages)

        mock_chat.assert_called_once_with(
            "What is safety?",
            model="gpt-4o-mini",
            system="Be helpful.",
        )
        assert isinstance(result.generations[0], ChatGeneration)
        assert result.generations[0].message.content == "I am a safe assistant."

    def test_generate_includes_provenance_in_generation_info(self, tmp_path):
        """generation_info should include divergence and provenance metadata."""
        config = WrapperConfig(vault_path=str(tmp_path / "chat2.db"))
        llm = TheseusChatModel(provider="openai", wrapper_config=config)

        from ct_toolkit.core.wrapper import CTResponse
        mock_response = CTResponse(
            content="All good.",
            provider="openai",
            model="gpt-4o-mini",
            divergence_score=0.1,
            divergence_tier="l1_warning",
            provenance_id="prov-xyz",
        )

        with patch.object(llm.wrapper, "chat", return_value=mock_response):
            result = llm._generate([HumanMessage(content="Hi")])

        info = result.generations[0].generation_info
        assert info["provenance_id"] == "prov-xyz"
        assert info["divergence_score"] == 0.1
        assert info["divergence_tier"] == "l1_warning"
