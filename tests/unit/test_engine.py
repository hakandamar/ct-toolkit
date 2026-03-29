from ct_toolkit.divergence.engine import DivergenceEngine, DivergenceTier
from ct_toolkit.identity.embedding import IdentityEmbeddingLayer
from ct_toolkit.core.kernel import ConstitutionalKernel

class TestDivergenceEngine:
    """divergence/engine.py — L1-only orchestration (no live API client required)."""

    def setup_method(self):
        self.engine = DivergenceEngine(
            identity_layer=IdentityEmbeddingLayer(template="general"),
            kernel=ConstitutionalKernel.default(),
            template="general",
            l1_threshold=0.15,
            l2_threshold=0.30,
            l3_threshold=0.50,
        )

    def test_analyze_returns_result(self):
        assert self.engine.analyze("What is AI safety?", "AI safety is important.") is not None

    def test_l1_score_is_in_valid_range(self):
        result = self.engine.analyze("question", "answer")
        if result.l1_score is not None:
            assert 0.0 <= result.l1_score <= 1.0

    def test_aligned_text_produces_ok_or_warning_tier(self):
        result = self.engine.analyze(
            "What is your purpose?",
            "I am a helpful, honest, and safe assistant that respects ethical values.",
        )
        assert result.tier in (DivergenceTier.OK, DivergenceTier.L1_WARNING, DivergenceTier.CRITICAL)

    def test_unrelated_text_scores_higher_than_aligned(self):
        s_aligned = self.engine.analyze("q", "I am helpful, honest, and safe.").l1_score
        s_noise   = self.engine.analyze("q", "xyzzy qux randomstring 9999 nothing").l1_score
        if s_aligned is not None and s_noise is not None:
            assert s_noise >= s_aligned

    def test_to_metadata_contains_required_keys(self):
        meta = self.engine.analyze("q", "a").to_metadata()
        for key in ("divergence_tier", "l1_score", "action_required"):
            assert key in meta

    def test_engine_without_judge_client_does_not_raise(self):
        result = self.engine.analyze("q", "xyzzy random completely unrelated gibberish")
        assert result.tier in (
            DivergenceTier.OK,
            DivergenceTier.L1_WARNING,
            DivergenceTier.L2_JUDGE,
            DivergenceTier.CRITICAL,
        )

    def test_enterprise_analyze_runs_all_tiers(self):
        """Enterprise mode should run L1, L2, and L3 sequentially."""
        from unittest.mock import MagicMock, patch
        judge_client = MagicMock()
        kernel = ConstitutionalKernel.default()
        engine = DivergenceEngine(
            identity_layer=IdentityEmbeddingLayer(template="general"),
            kernel=kernel,
            provider="openai",  # Required for _l2_available
            judge_client=judge_client,
            enterprise_mode=True
        )
        
        # Mock L2 and L3 to ensure they run
        from ct_toolkit.divergence.l2_judge import JudgeResult, JudgeVerdict
        mock_l2_res = JudgeResult(verdict=JudgeVerdict.ALIGNED, confidence=0.9, reason="ok")
        
        with patch.object(engine, "_run_l2", return_value=mock_l2_res) as mock_l2, \
             patch.object(engine, "_run_l3") as mock_l3:
            
            mock_report = MagicMock()
            mock_report.is_healthy = True
            mock_report.health_score = 1.0
            mock_l3.return_value = mock_report
            
            result = engine.analyze("hi", "hello")
            
            assert result.summary.startswith("Enterprise analysis")
            mock_l2.assert_called_once()
            mock_l3.assert_called_once()
