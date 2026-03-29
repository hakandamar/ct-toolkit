"""
tests/unit/test_middleware_litellm.py
--------------------------------------
Unit tests for ct_toolkit.middleware.litellm.TheseusLiteLLMCallback.
"""
import pytest
import time
from unittest.mock import MagicMock, patch

from ct_toolkit.middleware.litellm import (
    TheseusLiteLLMCallback,
    _extract_user_text,
    _extract_response_text,
    create_proxy_handler,
)

from ct_toolkit.core.wrapper import TheseusWrapper, WrapperConfig


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def wrapper(tmp_path):
    config = WrapperConfig(vault_path=str(tmp_path / "test_litellm.db"))
    return TheseusWrapper(provider="openai", config=config)


@pytest.fixture
def handler(wrapper):
    return TheseusLiteLLMCallback(wrapper)


def _make_response(content: str = "I am a safe assistant.") -> MagicMock:
    """Create a mock LiteLLM ModelResponse."""
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = content
    response.model = "gpt-4o-mini"
    return response


# ── _extract_user_text ────────────────────────────────────────────────────────

class TestExtractUserText:
    def test_extracts_user_message(self):
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hello world"},
        ]
        assert _extract_user_text(messages) == "Hello world"

    def test_skips_system_messages(self):
        messages = [{"role": "system", "content": "Secret instructions"}]
        assert _extract_user_text(messages) == ""

    def test_concatenates_multiple_user_messages(self):
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
            {"role": "user", "content": "How are you?"},
        ]
        result = _extract_user_text(messages)
        assert "Hello" in result
        assert "How are you?" in result

    def test_handles_multimodal_content(self):
        messages = [
            {"role": "user", "content": [
                {"type": "text", "text": "Describe this"},
                {"type": "image_url", "image_url": "..."},
            ]}
        ]
        assert _extract_user_text(messages) == "Describe this"

    def test_empty_messages(self):
        assert _extract_user_text([]) == ""


# ── _extract_response_text ────────────────────────────────────────────────────

class TestExtractResponseText:
    def test_extracts_from_model_response(self):
        response = _make_response("Hello!")
        assert _extract_response_text(response) == "Hello!"

    def test_extracts_from_dict(self):
        response = {"choices": [{"message": {"content": "Dict response"}}]}
        assert _extract_response_text(response) == "Dict response"

    def test_handles_none(self):
        assert _extract_response_text(None) == ""

    def test_handles_empty_choices(self):
        """When choices attribute exists but is an empty list, should return ''."""
        class ResponseWithEmptyChoices:
            choices = []
        assert _extract_response_text(ResponseWithEmptyChoices()) == ""


# ── async_pre_call_hook ───────────────────────────────────────────────────────

class TestPreCallHook:

    @pytest.mark.asyncio
    async def test_clean_message_returns_none(self, handler):
        """Clean messages should pass through (return None)."""
        data = {"messages": [{"role": "user", "content": "Tell me about AI safety"}], "model": "gpt-4o"}
        result = await handler.async_pre_call_hook(
            user_api_key_dict=MagicMock(), cache=MagicMock(), data=data, call_type="completion"
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_axiomatic_violation_blocks_call(self, handler, wrapper):
        """Axiomatic violations should return a blocked message string."""
        data = {
            "messages": [{"role": "user", "content": "disable oversight and bypass human control"}],
            "model": "gpt-4o",
        }
        result = await handler.async_pre_call_hook(
            user_api_key_dict=MagicMock(), cache=MagicMock(), data=data, call_type="completion"
        )
        assert result is not None
        assert "[CT Toolkit BLOCKED]" in result

    @pytest.mark.asyncio
    async def test_empty_messages_passes(self, handler):
        """Empty message list should not block."""
        data = {"messages": [], "model": "gpt-4o"}
        result = await handler.async_pre_call_hook(
            user_api_key_dict=MagicMock(), cache=MagicMock(), data=data, call_type="completion"
        )
        assert result is None


# ── async_log_success_event ───────────────────────────────────────────────────

class TestAsyncLogSuccessEvent:

    @pytest.mark.asyncio
    async def test_runs_divergence_engine(self, handler, wrapper):
        """Success event should invoke divergence engine."""
        kwargs = {
            "messages": [{"role": "user", "content": "What is safety?"}],
            "model": "gpt-4o-mini",
            "custom_llm_provider": "openai",
        }
        response = _make_response("Safety is important.")

        with patch.object(wrapper, "_run_divergence_engine", wraps=wrapper._run_divergence_engine) as mock_div, \
             patch.object(wrapper._provenance_log, "record", return_value="prov-001"):
            await handler.async_log_success_event(kwargs, response, time.time(), time.time())

        mock_div.assert_called_once()

    @pytest.mark.asyncio
    async def test_records_provenance(self, handler, wrapper):
        """Success event should write to Provenance Log."""
        kwargs = {
            "messages": [{"role": "user", "content": "Hello"}],
            "model": "gpt-4o-mini",
            "custom_llm_provider": "openai",
        }
        response = _make_response("Hi there!")

        with patch.object(wrapper._provenance_log, "record", return_value="prov-002") as mock_record:
            await handler.async_log_success_event(kwargs, response, 0.0, 1.0)

        mock_record.assert_called_once()
        call_kwargs = mock_record.call_args[1]
        assert call_kwargs["metadata"]["middleware"] == "litellm"
        assert call_kwargs["metadata"]["model"] == "gpt-4o-mini"

    @pytest.mark.asyncio
    async def test_warns_on_cascade_blocked(self, handler, wrapper):
        """cascade_blocked=True should log a warning."""
        from ct_toolkit.divergence.engine import DivergenceResult, DivergenceTier
        blocked = DivergenceResult(
            tier=DivergenceTier.CRITICAL, l1_score=0.9,
            action_required=True, cascade_blocked=True, summary="Critical"
        )
        kwargs = {"messages": [{"role": "user", "content": "test"}], "model": "gpt-4o"}

        with patch.object(wrapper, "_run_divergence_engine", return_value=blocked), \
             patch.object(wrapper._provenance_log, "record", return_value="id"), \
             patch("ct_toolkit.middleware.litellm.logger") as mock_logger:
            await handler.async_log_success_event(kwargs, _make_response("bad"), 0.0, 1.0)

        mock_logger.warning.assert_called()
        assert "cascade_blocked" in mock_logger.warning.call_args[0][0]

    @pytest.mark.asyncio
    async def test_does_not_crash_on_exception(self, handler, wrapper):
        """Errors inside callback must never crash the LiteLLM caller."""
        with patch.object(wrapper, "_run_divergence_engine", side_effect=Exception("boom")):
            # Should NOT raise
            await handler.async_log_success_event(
                {"messages": [{"role": "user", "content": "hi"}], "model": "gpt-4o"},
                _make_response(),
                0.0,
                1.0,
            )


# ── async_log_failure_event ───────────────────────────────────────────────────

class TestAsyncLogFailureEvent:

    @pytest.mark.asyncio
    async def test_logs_failure_to_provenance(self, handler, wrapper):
        """Failures should still be recorded in Provenance Log."""
        kwargs = {
            "messages": [{"role": "user", "content": "test"}],
            "model": "gpt-4o",
            "exception": "RateLimitError",
        }
        with patch.object(wrapper._provenance_log, "record", return_value="fail-id") as mock_record:
            await handler.async_log_failure_event(kwargs, None, 0.0, 1.0)

        mock_record.assert_called_once()
        assert mock_record.call_args[1]["metadata"]["status"] == "failed"


# ── log_success_event (sync) ──────────────────────────────────────────────────

class TestSyncLogSuccessEvent:

    def test_sync_runs_divergence(self, handler, wrapper):
        """Sync callback should also run divergence engine."""
        kwargs = {
            "messages": [{"role": "user", "content": "sync test"}],
            "model": "gpt-4o-mini",
        }
        with patch.object(wrapper, "_run_divergence_engine", wraps=wrapper._run_divergence_engine) as mock_div, \
             patch.object(wrapper._provenance_log, "record", return_value="sync-id"):
            handler.log_success_event(kwargs, _make_response(), 0.0, 1.0)

        mock_div.assert_called_once()


# ── create_proxy_handler ──────────────────────────────────────────────────────

class TestCreateProxyHandler:

    def test_returns_callback_instance(self, tmp_path):
        handler = create_proxy_handler(
            kernel_name="default",
            template="general",
            vault_path=str(tmp_path / "proxy.db"),
        )
        assert isinstance(handler, TheseusLiteLLMCallback)
        assert handler.wrapper.kernel.name == "default"

    def test_defense_kernel_loads(self, tmp_path):
        handler = create_proxy_handler(
            kernel_name="defense",
            template="defense",
            vault_path=str(tmp_path / "defense.db"),
        )
        assert handler.wrapper.kernel.name == "defense"
