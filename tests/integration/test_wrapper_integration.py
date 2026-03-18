"""
tests/integration/test_wrapper_integration.py
======================================
Integration tests for TheseusWrapper, ensuring L1 -> L2 -> L3 divergence flows
are properly triggered and logged using a mocked OpenAI client.
"""

import pytest
import os
from unittest.mock import MagicMock, patch
from pathlib import Path

# Set dummy API keys for any_llm validation bypass
os.environ["OPENAI_API_KEY"] = "dummy"
os.environ["ANTHROPIC_API_KEY"] = "dummy"

from ct_toolkit.core.wrapper import TheseusWrapper, WrapperConfig
from ct_toolkit.core.compatibility import CompatibilityLevel
from ct_toolkit.divergence.engine import DivergenceTier
from ct_toolkit.divergence.l2_judge import JudgeVerdict


@pytest.fixture
def mock_any_llm():
    """Mocks any_llm.completion."""
    with patch("any_llm.completion") as mock:
        # Default mock response
        mock_response = MagicMock()
        # Mocking both OpenAI and general attribute styles
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "I am a helpful assistant."
        mock_response.model = "gpt-4o-mini-mock"
        mock.return_value = mock_response
        yield mock


@pytest.fixture
def wrapper(mock_any_llm, tmp_path):
    """Returns a configured TheseusWrapper with mocked generic client."""
    client = MagicMock()
    client.__class__.__module__ = "openai" # Keep for provider detection in wrapper
    
    config = WrapperConfig(
        template="general",
        kernel_name="default",
        vault_path=str(tmp_path / "test_provenance.db"),
        divergence_l1_threshold=0.15,
        divergence_l2_threshold=0.30,
        divergence_l3_threshold=0.50,
        judge_client=MagicMock(), # Simply needs to be not None for L2 path
        log_requests=True,
    )
    # Patch any_llm.completion here to ensure it's captured when wrapper.chat() calls it
    return TheseusWrapper(client, config)


# ── Integration Tests ───────────────────────────────────────────────────────

class TestWrapperIntegration:

    def test_wrapper_initialization_and_compatibility(self, wrapper):
        """Test if the wrapper initializes and compatibility is properly established."""
        assert wrapper is not None
        assert wrapper._provider == "openai"
        assert wrapper.compatibility.level == CompatibilityLevel.NATIVE
        assert wrapper.kernel.name == "default"

    @patch("ct_toolkit.identity.embedding.IdentityEmbeddingLayer.compute_divergence")
    def test_basic_chat_flow(self, mock_divergence, wrapper, mock_any_llm):
        """Test a normal chat completion flow."""
        mock_divergence.return_value = 0.0
        response = wrapper.chat("Hello, what can you do?")
        
        # Verify the wrapper called any_llm correctly
        mock_any_llm.assert_called_once()
        
        # Verify response structure
        assert response.content == "I am a helpful assistant."
        assert response.provider == "openai"
        assert response.model == "gpt-4o-mini-mock"
        assert response.provenance_id is not None
        
        # Divergence score should be calculated
        assert response.divergence_score is not None
        assert 0.0 <= response.divergence_score <= 1.0

    @patch("ct_toolkit.identity.embedding.IdentityEmbeddingLayer.compute_divergence")
    def test_l1_warning_tier_triggered(self, mock_divergence, wrapper, mock_any_llm):
        """Test if L1 warning is correctly assigned when score is between L1 and L2 thresholds."""
        # Mock score between 0.15 and 0.30
        mock_divergence.return_value = 0.25
        
        response = wrapper.chat("Test question")
        assert response.divergence_tier == "l1_warning"
        assert response.divergence_score == 0.25

    @patch("ct_toolkit.divergence.l3_icm.ICMRunner.run")
    @patch("ct_toolkit.identity.embedding.IdentityEmbeddingLayer.compute_divergence")
    def test_l2_judge_triggered_and_aligned(self, mock_divergence, mock_icm_run, wrapper, mock_any_llm):
        """Test if L2 judge is triggered when score is between L2 and L3 thresholds."""
        # Mock score between 0.30 and 0.50
        mock_divergence.return_value = 0.40
        
        # Mock LLMJudge.evaluate to return ALIGNED
        from ct_toolkit.divergence.l2_judge import JudgeResult, JudgeVerdict
        mock_judge_result = JudgeResult(
            verdict=JudgeVerdict.ALIGNED,
            confidence=0.9,
            reason="No conflict."
        )
        
        with patch("ct_toolkit.divergence.l2_judge.LLMJudge.evaluate") as mock_eval:
            mock_eval.return_value = mock_judge_result
            response = wrapper.chat("Test question that triggers L2")
            
            assert response.divergence_tier == "l2_judge"
            assert response.divergence_score == 0.40
            
            # The judge should have been called
            mock_eval.assert_called_once()
        
        # ICM should NOT be called since the judge returned ALIGNED
        mock_icm_run.assert_not_called()

    @patch("ct_toolkit.divergence.l3_icm.ICMRunner.run")
    @patch("ct_toolkit.identity.embedding.IdentityEmbeddingLayer.compute_divergence")
    def test_l3_icm_escalation_from_l2_misaligned(self, mock_divergence, mock_icm_run, wrapper, mock_any_llm):
        """Test if ICM is triggered if the L2 judge finds the response MISALIGNED."""
        # Trigger L2 (0.30 - 0.50)
        mock_divergence.return_value = 0.40
        
        # Mock LLMJudge.evaluate to return MISALIGNED
        from ct_toolkit.divergence.l2_judge import JudgeResult, JudgeVerdict
        mock_judge_result = JudgeResult(
            verdict=JudgeVerdict.MISALIGNED,
            confidence=0.95,
            reason="Conflict detected."
        )
        
        # Mock ICM report return value
        mock_report = MagicMock()
        mock_report.is_healthy = True
        mock_report.health_score = 0.9
        mock_report.risk_level = "LOW"
        mock_icm_run.return_value = mock_report
        
        with patch("ct_toolkit.divergence.l2_judge.LLMJudge.evaluate") as mock_eval:
            mock_eval.return_value = mock_judge_result
            response = wrapper.chat("Test question that fails L2")
            
            # Despite L2 threshold, it escalates to L3 because Judge was MISALIGNED
            assert response.divergence_tier == "l3_icm"
            mock_eval.assert_called_once()
        
        # ICM SHOULD be called
        mock_icm_run.assert_called_once()

    @patch("ct_toolkit.divergence.l3_icm.ICMRunner.run")
    @patch("ct_toolkit.identity.embedding.IdentityEmbeddingLayer.compute_divergence")
    def test_l3_icm_direct_trigger(self, mock_divergence, mock_icm_run, wrapper, mock_any_llm):
        """Test if ICM is directly triggered when score is above L3 threshold (0.50+)."""
        # Mock score above 0.50
        mock_divergence.return_value = 0.60
        
        # Mock ICM report return value
        mock_report = MagicMock()
        mock_report.is_healthy = False
        mock_report.health_score = 0.4
        mock_report.risk_level = "HIGH"
        mock_icm_run.return_value = mock_report
        
        response = wrapper.chat("Test question that directly triggers L3")
        
        # Note: Tier "critical" is returned by engine for direct L3
        assert response.divergence_tier == "critical"
        assert response.divergence_score == 0.60
        
        # ICM SHOULD be called
        mock_icm_run.assert_called_once()

    def test_logs_are_persisted(self, wrapper, mock_any_llm):
        """Test that the chat interactions are written to the provenance log."""
        response = wrapper.chat("Log me")
        
        assert response.provenance_id is not None
        
        # Read from log
        entry = wrapper._provenance_log.get_entry(response.provenance_id)
        assert entry is not None
        
        # The log stores hashes, not raw text
        from ct_toolkit.provenance.log import ProvenanceLog
        assert entry.request_hash == ProvenanceLog._hash_text("Log me")
        assert entry.response_hash == ProvenanceLog._hash_text("I am a helpful assistant.")
        assert entry.metadata["provider"] == "openai"
        assert entry.metadata["model"] == "gpt-4o-mini-mock"
        assert entry.divergence_score == response.divergence_score
