import pytest
from unittest.mock import MagicMock
from ct_toolkit.divergence.l2_judge import LLMJudge, JudgeResult, JudgeVerdict, JudgeResponse
from ct_toolkit.core.kernel import ConstitutionalKernel
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
