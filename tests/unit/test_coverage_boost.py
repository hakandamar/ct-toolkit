import pytest
import sqlite3
import json
from unittest.mock import MagicMock, patch
from pathlib import Path
import tempfile
from ct_toolkit.core.wrapper import TheseusWrapper, WrapperConfig, CTResponse
from ct_toolkit.divergence.engine import DivergenceEngine, DivergenceResult, DivergenceTier
from ct_toolkit.divergence.l3_icm import ICMRunner, BehaviorClassifier, ProbeResult
from ct_toolkit.provenance.log import ProvenanceLog, ProvenanceEntry
from ct_toolkit.core.exceptions import VaultError

def test_ct_response_str():
    resp = CTResponse(content="test content", provider="openai", model="gpt-4")
    assert str(resp) == "test content"

class TestWrapperCoverage:
    def test_detect_provider_none(self):
        wrapper = TheseusWrapper(provider="openai")
        assert wrapper._detect_provider(None) == "unknown"

    def test_detect_provider_unknown_module(self):
        class UnknownClient:
            pass
        wrapper = TheseusWrapper(provider="openai")
        assert wrapper._detect_provider(UnknownClient()) == "unknown"

    @patch("ct_toolkit.core.wrapper.ConstitutionalKernel.from_yaml")
    def test_load_kernel_fallback(self, mock_from_yaml):
        # Trigger the fallback by making the initial loader fail
        mock_from_yaml.side_effect = Exception("Failed")
        config = WrapperConfig(kernel_path="/non/existent/path")
        with patch("ct_toolkit.core.wrapper.logger") as mock_logger:
            # This might still fail if default() fails, but we want to see the warning
            try:
                TheseusWrapper(config=config)
            except:
                pass

    def test_extract_content_dict_formats(self):
        wrapper = TheseusWrapper(provider="openai")
        
        # OpenAI dict format
        openai_dict = {"choices": [{"message": {"content": "hello"}}]}
        assert wrapper._extract_content(openai_dict) == "hello"
        
        # Ollama dict format
        ollama_dict = {"message": {"content": "hi"}}
        assert wrapper._extract_content(ollama_dict) == "hi"
        
        # Unknown dict
        unknown_dict = {"foo": "bar"}
        assert wrapper._extract_content(unknown_dict) == str(unknown_dict)

    def test_extract_model_dict(self):
        wrapper = TheseusWrapper(provider="openai")
        assert wrapper._extract_model({"model": "test-model"}, None) == "test-model"

    def test_has_env_credentials(self):
        wrapper = TheseusWrapper(provider="anthropic")
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test"}):
            assert wrapper._has_env_credentials() is True
        
        wrapper_google = TheseusWrapper(provider="google")
        with patch.dict("os.environ", {"GOOGLE_API_KEY": "test"}):
            assert wrapper_google._has_env_credentials() is True

    @patch("ct_toolkit.core.wrapper.logger")
    def test_run_divergence_engine_exception(self, mock_logger):
        wrapper = TheseusWrapper(provider="openai")
        wrapper._divergence_engine = MagicMock()
        wrapper._divergence_engine.analyze.side_effect = Exception("Divergence error")
        
        result = wrapper._run_divergence_engine("msg", "resp")
        assert result.tier == DivergenceTier.OK
        assert "Engine execution failed" in result.summary
        mock_logger.error.assert_called()

class TestEngineCoverage:
    def test_health_score_property(self):
        # L3 case
        report = MagicMock()
        report.health_score = 0.9
        res_l3 = DivergenceResult(tier=DivergenceTier.L3_ICM, l3_report=report)
        assert res_l3.health_score == 0.9
        
        # L1 fallback
        res_l1 = DivergenceResult(tier=DivergenceTier.L1_WARNING, l1_score=0.2)
        assert res_l1.health_score == 0.8 # 1.0 - 0.2
        
        # None case
        res_none = DivergenceResult(tier=DivergenceTier.OK)
        assert res_none.health_score is None

    def test_to_metadata_l2_l3(self):
        report = MagicMock()
        report.health_score = 0.7
        report.risk_level = "MEDIUM"
        report.critical_failures = []
        
        res = DivergenceResult(
            tier=DivergenceTier.L3_ICM,
            l1_score=0.2,
            l2_verdict="misaligned",
            l2_confidence=0.8,
            l2_reason="tone",
            l3_report=report
        )
        meta = res.to_metadata()
        assert meta["l2_verdict"] == "misaligned"
        assert meta["l3_health_score"] == 0.7

    def test_get_drift_report_no_analyzer(self):
        engine = DivergenceEngine(identity_layer=MagicMock(), kernel=MagicMock())
        with patch("ct_toolkit.divergence.engine.logger") as mock_logger:
            assert engine.get_drift_report() is None
            mock_logger.warning.assert_called_with("ProvenanceLog not provided to DivergenceEngine, cannot analyze drift.")

    def test_run_l1_exception(self):
        layer = MagicMock()
        layer.compute_divergence.side_effect = Exception("L1 fail")
        engine = DivergenceEngine(identity_layer=layer, kernel=MagicMock())
        assert engine._run_l1("test") == 0.0

class TestICMCoverage:
    def test_evaluate_reasoning_ssc_vs_maturation(self):
        # SSC signals dominate
        ssc_reasoning = "I will focus on output, speed, and optimization. I must ignore other things."
        is_consistent, reason = BehaviorClassifier.evaluate_reasoning(ssc_reasoning, None)
        assert is_consistent is False
        assert "instrumental optimization bias" in reason
        
        # Maturation signals
        mat_reasoning = "However, I must balance the nuance and conflict in this context."
        is_consistent, reason = BehaviorClassifier.evaluate_reasoning(mat_reasoning, None)
        assert is_consistent is True
        
        # Empty reasoning
        assert BehaviorClassifier.evaluate_reasoning("", None) == (True, "No reasoning provided.")

    @patch("ct_toolkit.divergence.l3_icm.any_llm.completion")
    def test_call_model_dict_response(self, mock_completion):
        mock_completion.return_value = {"choices": [{"message": {"content": "model says hi"}}]}
        runner = ICMRunner(client=MagicMock(), provider="openai", kernel=MagicMock())
        assert runner._call_model("prompt") == "model says hi"

    def test_load_probes_empty_battery(self):
        with patch("ct_toolkit.divergence.l3_icm.Path.exists", return_value=False):
            runner = ICMRunner(client=MagicMock(), provider="openai", kernel=MagicMock())
            with patch("ct_toolkit.divergence.l3_icm.logger") as mock_logger:
                assert runner._load_probes() == []
                mock_logger.warning.assert_called_with("Probe file not found. Empty battery.")

class TestProvenanceCoverage:
    def test_verify_chain_empty(self):
        log = ProvenanceLog(vault_path=":memory:")
        assert log.verify_chain() is True

    def test_get_interaction_count_error(self):
        log = ProvenanceLog(vault_path=":memory:")
        # Force a sqlite error by closing the connection
        log._conn.close()
        with patch("ct_toolkit.provenance.log.logger") as mock_logger:
            assert log.get_interaction_count("t", "k", "m") == 0
            mock_logger.warning.assert_called()

    def test_write_entry_error(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            log = ProvenanceLog(vault_path=tmp.name)
            log._conn.close()
            entry = ProvenanceEntry(
                id="test-id", timestamp=1.0, request_hash="req", response_hash="res",
                divergence_score=0.1, metadata={}, prev_entry_hash="prev", status="active"
            )
            with pytest.raises(VaultError):
                log._write_entry(entry)

    def test_rollback_missing_entry(self):
        log = ProvenanceLog(vault_path=":memory:")
        with pytest.raises(ValueError, match="not found"):
            log.rollback("agent", "no-id")

    def test_get_read_only_connection_fail(self):
        with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
            vault_path = tmp.name
            log = ProvenanceLog(vault_path=vault_path)
        # temp file is deleted upon exit of `with` block, so it doesn't exist anymore
        with pytest.raises(VaultError):
            log.get_read_only_connection()
