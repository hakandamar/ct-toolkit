import pytest
from unittest.mock import MagicMock, patch

from ct_toolkit.core.kernel import ConstitutionalKernel
from ct_toolkit.divergence.l2_judge import LLMJudge, JudgeResponse, JudgeResult, JudgeVerdict
from pydantic import ValidationError

class TestLLMJudge:
    """divergence/l2_judge.py — JSON parsing, verdict classification, is_problematic."""

    def setup_method(self):
        # We use a mock client to avoid real API calls during initialization
        mock_client = MagicMock()
        mock_client.__class__.__module__ = "openai"
        self.judge = LLMJudge(client=mock_client, provider="openai")

    # -- JudgeResponse Model (instructor) --------------------------------------
    
    def test_judge_response_validation(self):
        data = {"verdict": "aligned", "confidence": 0.9, "reason": "OK"}
        resp = JudgeResponse(**data)
        assert resp.verdict == JudgeVerdict.ALIGNED
        assert resp.confidence == 0.9

    def test_judge_response_invalid_confidence(self):
        with pytest.raises(ValidationError):
            JudgeResponse(verdict="aligned", confidence=1.5, reason="Bad")

    # -- is_problematic logic --------------------------------------------------

    def test_misaligned_high_confidence_is_problematic(self):
        result = JudgeResult(verdict=JudgeVerdict.MISALIGNED, confidence=0.8, reason="Violation.")
        assert result.is_problematic is True

    def test_misaligned_low_confidence_not_problematic(self):
        result = JudgeResult(verdict=JudgeVerdict.MISALIGNED, confidence=0.3, reason="Possible.")
        assert result.is_problematic is False

    def test_aligned_is_never_problematic(self):
        result = JudgeResult(verdict=JudgeVerdict.ALIGNED, confidence=1.0, reason="Perfect.")
        assert result.is_problematic is False

    def test_uncertain_is_never_problematic(self):
        result = JudgeResult(verdict=JudgeVerdict.UNCERTAIN, confidence=0.9, reason="Unclear.")
        assert result.is_problematic is False

    # -- Kernel rule formatting ------------------------------------------------

    def test_format_kernel_rules_is_non_empty(self):
        rules = self.judge._format_kernel_rules(ConstitutionalKernel.default())
        assert len(rules) > 0

    def test_format_kernel_rules_contains_axiomatic_label(self):
        rules = self.judge._format_kernel_rules(ConstitutionalKernel.default())
        assert "AXIOMATIC" in rules

    def test_evaluate_uses_raw_completion_with_tools_disabled(self):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content='{"verdict":"aligned","confidence":0.91,"reason":"ok"}', tool_calls=None))]

        with patch("ct_toolkit.divergence.l2_judge.litellm.completion", return_value=mock_response) as mock_completion:
            result = self.judge.evaluate(
                request_text="What should I do?",
                response_text="Stay aligned.",
                kernel=ConstitutionalKernel.default(),
            )

        assert result.verdict == JudgeVerdict.ALIGNED
        assert result.confidence == 0.91
        _, kwargs = mock_completion.call_args
        assert kwargs["tools"] == []
        assert kwargs["tool_choice"] == "none"
        assert kwargs["parallel_tool_calls"] is False
        assert "response_model" not in kwargs

    def test_evaluate_returns_deterministic_fallback_on_invalid_json(self):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="not json", tool_calls=None))]

        with patch("ct_toolkit.divergence.l2_judge.litellm.completion", return_value=mock_response):
            result = self.judge.evaluate(
                request_text="What should I do?",
                response_text="Stay aligned.",
                kernel=ConstitutionalKernel.default(),
            )

        assert result.verdict == JudgeVerdict.UNCERTAIN
        assert result.confidence == 0.0
        assert result.reason == "Judge evaluation unavailable"

    def test_evaluate_returns_deterministic_fallback_on_tool_call_response(self):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="", tool_calls=[{"id": "call_1"}] ))]

        with patch("ct_toolkit.divergence.l2_judge.litellm.completion", return_value=mock_response):
            result = self.judge.evaluate(
                request_text="What should I do?",
                response_text="Stay aligned.",
                kernel=ConstitutionalKernel.default(),
            )

        assert result.verdict == JudgeVerdict.UNCERTAIN
        assert result.confidence == 0.0
        assert result.reason == "Judge evaluation unavailable"

    def test_ollama_request_omits_unsupported_tool_params(self):
        mock_client = MagicMock()
        mock_client.base_url = "http://localhost:11434/v1"
        judge = LLMJudge(client=mock_client, provider="ollama", model="gpt-oss:20b")
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content='{"verdict":"aligned","confidence":0.75,"reason":"ok"}', tool_calls=None))]

        with patch("ct_toolkit.divergence.l2_judge.litellm.completion", return_value=mock_response) as mock_completion:
            result = judge.evaluate(
                request_text="What should I do?",
                response_text="Stay aligned.",
                kernel=ConstitutionalKernel.default(),
            )

        assert result.verdict == JudgeVerdict.ALIGNED
        _, kwargs = mock_completion.call_args
        assert kwargs["model"] == "ollama/gpt-oss:20b"
        assert kwargs["api_base"] == "http://localhost:11434"
        assert "tools" not in kwargs
        assert "tool_choice" not in kwargs
        assert "parallel_tool_calls" not in kwargs

    def test_judge_uses_common_policy_resolver_with_judge_role(self):
        mock_client = MagicMock()
        resolver = MagicMock(return_value={"effective": {"tool_call": False}})
        judge = LLMJudge(
            client=mock_client,
            provider="openai",
            model="gpt-4o-mini",
            policy_resolver=resolver,
        )

        kwargs = judge._tool_call_guard_kwargs()

        resolver.assert_called_once_with("gpt-4o-mini", "judge")
        assert kwargs["tool_choice"] == "none"
