"""
tests/unit/test_middleware_langchain.py
---------------------------------------
Unit tests for ct_toolkit.middleware.langchain.
Tests cover TheseusLangChainCallback and TheseusChatModel.
"""
import pytest
from typing import List, cast
from uuid import uuid4
from unittest.mock import patch

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage
from langchain_core.outputs import LLMResult, ChatGeneration, Generation

from ct_toolkit.middleware.langchain import TheseusLangChainCallback, TheseusChatModel
from ct_toolkit.core.wrapper import TheseusWrapper, WrapperConfig


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
        messages: List[BaseMessage] = [HumanMessage(content="Hi")]
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
        assert info is not None
        assert info["provenance_id"] == "prov-xyz"
        assert info["divergence_score"] == 0.1
        assert info["divergence_tier"] == "l1_warning"
        assert info["ct_policy"]["role"] == config.policy_role
        assert info["ct_policy"]["environment"] == config.policy_environment

    def test_bind_tools_persists_binding(self, tmp_path):
        """bind_tools should return a new model with normalized bound tools."""
        config = WrapperConfig(vault_path=str(tmp_path / "bind_tools.db"))
        llm = TheseusChatModel(provider="openai", wrapper_config=config)

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "lookup_weather",
                    "description": "Get weather by city",
                    "parameters": {
                        "type": "object",
                        "properties": {"city": {"type": "string"}},
                        "required": ["city"],
                    },
                },
            }
        ]

        bound = llm.bind_tools(tools, tool_choice="auto")

        assert bound is not llm
        assert len(bound.bound_tools) == 1
        assert bound.bound_tool_choice == "auto"

    def test_generate_forwards_bound_tools_to_wrapper(self, tmp_path):
        """When tools are bound, _generate must pass tool kwargs to wrapper.chat."""
        config = WrapperConfig(vault_path=str(tmp_path / "tool_forward.db"))
        llm = TheseusChatModel(provider="openai", model="gpt-4o-mini", wrapper_config=config)
        llm = llm.bind_tools(
            [
                {
                    "type": "function",
                    "function": {
                        "name": "lookup_weather",
                        "description": "Get weather by city",
                        "parameters": {"type": "object", "properties": {}},
                    },
                }
            ],
            tool_choice="auto",
        )

        from ct_toolkit.core.wrapper import CTResponse
        mock_response = CTResponse(
            content="Checking tools",
            provider="openai",
            model="gpt-4o-mini",
            divergence_score=0.01,
            divergence_tier="ok",
            provenance_id="prov-tools",
            raw_response={"choices": [{"message": {"content": "Checking tools"}}]},
        )

        with patch.object(llm.wrapper, "chat", return_value=mock_response) as mock_chat:
            llm._generate([HumanMessage(content="Weather in Ankara?")])

        _, kwargs = mock_chat.call_args
        assert kwargs["tools"][0]["function"]["name"] == "lookup_weather"
        assert kwargs["tool_choice"] == "auto"

    def test_generate_extracts_tool_calls_into_ai_message(self, tmp_path):
        """Tool call responses should be surfaced via AIMessage.tool_calls."""
        config = WrapperConfig(vault_path=str(tmp_path / "tool_extract.db"))
        llm = TheseusChatModel(provider="openai", wrapper_config=config)

        from ct_toolkit.core.wrapper import CTResponse
        raw = {
            "choices": [
                {
                    "message": {
                        "content": "",
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "function": {
                                    "name": "lookup_weather",
                                    "arguments": '{"city":"Ankara"}',
                                },
                            }
                        ],
                    }
                }
            ]
        }
        mock_response = CTResponse(
            content="",
            provider="openai",
            model="gpt-4o-mini",
            divergence_score=0.03,
            divergence_tier="ok",
            provenance_id="prov-call",
            raw_response=raw,
        )

        with patch.object(llm.wrapper, "chat", return_value=mock_response):
            result = llm._generate([HumanMessage(content="Use tool")])

        msg = cast(AIMessage, result.generations[0].message)
        info = result.generations[0].generation_info
        assert msg.tool_calls
        assert msg.tool_calls[0]["name"] == "lookup_weather"
        assert msg.tool_calls[0]["args"]["city"] == "Ankara"
        assert info is not None
        assert info["ct_policy"] == llm.policy_metadata

    def test_generate_disables_tools_when_allow_tools_false(self, tmp_path):
        """Judge/evaluator role can force-disable tool calling at model level."""
        config = WrapperConfig(vault_path=str(tmp_path / "disable_tools.db"))
        llm = TheseusChatModel(provider="openai", wrapper_config=config, allow_tools=False)

        from ct_toolkit.core.wrapper import CTResponse
        mock_response = CTResponse(
            content="No tools",
            provider="openai",
            model="gpt-4o-mini",
            divergence_score=0.02,
            divergence_tier="ok",
            provenance_id="prov-no-tools",
            raw_response={"choices": [{"message": {"content": "No tools"}}]},
        )

        with patch.object(llm.wrapper, "chat", return_value=mock_response) as mock_chat:
            llm._generate([HumanMessage(content="hello")])

        _, kwargs = mock_chat.call_args
        assert kwargs["tools"] == []
        assert kwargs["tool_choice"] == "none"
        assert kwargs["parallel_tool_calls"] is False
