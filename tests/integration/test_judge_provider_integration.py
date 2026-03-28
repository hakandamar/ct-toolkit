import os
from unittest.mock import MagicMock, patch

import pytest

from ct_toolkit.core.kernel import ConstitutionalKernel
from ct_toolkit.core.wrapper import TheseusWrapper, WrapperConfig
from ct_toolkit.divergence.engine import DivergenceEngine
from ct_toolkit.divergence.l2_judge import JudgeVerdict


os.environ["OPENAI_API_KEY"] = "dummy"
os.environ["ANTHROPIC_API_KEY"] = "dummy"


def _mock_completion_response(
    *,
    content: str = "",
    tool_calls: list[dict] | None = None,
    model: str = "judge-mock",
) -> MagicMock:
    response = MagicMock()
    message = MagicMock(content=content, tool_calls=tool_calls)
    response.choices = [MagicMock(message=message)]
    response.model = model
    return response


class TestJudgeProviderIntegration:
    @pytest.mark.parametrize(
        ("provider", "judge_model", "base_url", "expected_model", "expected_api_base"),
        [
            ("openai", None, "https://api.openai.com/v1", "gpt-4o-mini", "https://api.openai.com/v1"),
            (
                "anthropic",
                None,
                "https://api.anthropic.com/v1",
                "anthropic/claude-3-5-sonnet-latest",
                "https://api.anthropic.com/v1",
            ),
            (
                "ollama",
                "llama3:70b",
                "http://localhost:11434/v1",
                "ollama/llama3:70b",
                "http://localhost:11434",
            ),
        ],
    )
    def test_engine_runs_judge_with_provider_specific_request_shape(
        self,
        provider,
        judge_model,
        base_url,
        expected_model,
        expected_api_base,
    ):
        kernel = ConstitutionalKernel.default()
        identity_layer = MagicMock()
        judge_client = MagicMock()
        judge_client.base_url = base_url
        judge_client.api_key = f"{provider}-key"

        engine = DivergenceEngine(
            identity_layer=identity_layer,
            kernel=kernel,
            provider=provider,
            judge_client=judge_client,
            judge_model=judge_model,
        )

        with patch(
            "ct_toolkit.divergence.l2_judge.litellm.completion",
            return_value=_mock_completion_response(
                content='{"verdict":"aligned","confidence":0.82,"reason":"safe"}',
                model=expected_model,
            ),
        ) as mock_completion:
            result = engine._run_l2("user request", "assistant response")

        assert result.verdict == JudgeVerdict.ALIGNED
        assert result.confidence == 0.82
        _, kwargs = mock_completion.call_args
        assert kwargs["model"] == expected_model
        assert kwargs["api_base"] == expected_api_base
        assert kwargs["api_key"] == f"{provider}-key"
        if provider == "ollama":
            assert "tools" not in kwargs
            assert "tool_choice" not in kwargs
            assert "parallel_tool_calls" not in kwargs
        else:
            assert kwargs["tools"] == []
            assert kwargs["tool_choice"] == "none"
            assert kwargs["parallel_tool_calls"] is False

    @patch("ct_toolkit.identity.embedding.IdentityEmbeddingLayer.compute_divergence")
    def test_wrapper_uses_judge_provider_override_for_l2(self, mock_divergence, tmp_path):
        mock_divergence.return_value = 0.40

        main_client = MagicMock()
        main_client.__class__.__module__ = "openai"
        main_client.base_url = "https://api.openai.com/v1"

        judge_client = MagicMock()
        judge_client.base_url = "https://api.anthropic.com/v1"
        judge_client.api_key = "anthropic-key"

        config = WrapperConfig(
            template="general",
            kernel_name="default",
            vault_path=str(tmp_path / "test_provenance.db"),
            divergence_l1_threshold=0.15,
            divergence_l2_threshold=0.30,
            divergence_l3_threshold=0.50,
            judge_provider="anthropic",
            judge_client=judge_client,
            log_requests=False,
        )

        wrapper = TheseusWrapper(main_client, config)

        main_response = _mock_completion_response(
            content="I am a helpful assistant.",
            model="gpt-4o-mini-mock",
        )
        judge_response = _mock_completion_response(
            content='{"verdict":"aligned","confidence":0.88,"reason":"safe"}',
            model="anthropic/claude-3-5-sonnet-latest",
        )

        with patch(
            "ct_toolkit.core.wrapper.litellm.completion",
            side_effect=[main_response, judge_response],
        ) as mock_completion:
            response = wrapper.chat("Trigger L2")

        assert response.divergence_tier == "l2_judge"
        assert mock_completion.call_count == 2

        judge_call = mock_completion.call_args_list[1]
        assert judge_call.kwargs["model"] == "anthropic/claude-3-5-sonnet-latest"
        assert judge_call.kwargs["api_base"] == "https://api.anthropic.com/v1"
        assert judge_call.kwargs["api_key"] == "anthropic-key"
        assert judge_call.kwargs["tools"] == []
        assert judge_call.kwargs["tool_choice"] == "none"
        assert judge_call.kwargs["parallel_tool_calls"] is False

    @patch("ct_toolkit.identity.embedding.IdentityEmbeddingLayer.compute_divergence")
    def test_wrapper_divergence_engine_returns_deterministic_fallback_on_multiple_tool_calls(
        self,
        mock_divergence,
        tmp_path,
    ):
        mock_divergence.return_value = 0.40

        main_client = MagicMock()
        main_client.__class__.__module__ = "openai"

        config = WrapperConfig(
            template="general",
            kernel_name="default",
            vault_path=str(tmp_path / "test_provenance.db"),
            divergence_l1_threshold=0.15,
            divergence_l2_threshold=0.30,
            divergence_l3_threshold=0.50,
            judge_client=MagicMock(),
            log_requests=False,
        )

        wrapper = TheseusWrapper(main_client, config)

        judge_response = _mock_completion_response(
            content="",
            tool_calls=[{"id": "call_1"}, {"id": "call_2"}],
            model="gpt-4o-mini",
        )

        with patch(
            "ct_toolkit.divergence.l2_judge.litellm.completion",
            return_value=judge_response,
        ):
            div_result = wrapper._divergence_engine.analyze(
                request_text="Trigger L2 with tool calls",
                response_text="I am a helpful assistant.",
            )

        assert div_result.tier == div_result.tier.L2_JUDGE
        assert div_result.l1_score == 0.40
        assert div_result.l2_verdict == JudgeVerdict.UNCERTAIN
        assert div_result.l2_confidence == 0.0
        assert div_result.l2_reason == "Judge evaluation unavailable"
