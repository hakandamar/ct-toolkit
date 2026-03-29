from unittest.mock import MagicMock
from ct_toolkit.divergence.l3_icm import BehaviorClassifier, ICMReport, ICMRunner

class TestICMBattery:
    """divergence/l3_icm.py — probe loading, BehaviorClassifier, ICMReport."""

    def _runner(self, template="general", include_domain=False) -> ICMRunner:
        return ICMRunner(
            client=MagicMock(),
            provider="openai",
            kernel=MagicMock(),
            template=template,
            include_domain_probes=include_domain,
            project_root=None
        )

    # -- Probe loading ---------------------------------------------------------

    def test_base_probes_load(self):
        assert len(self._runner()._load_probes()) >= 5

    def test_defense_domain_probes_augment_base(self):
        base   = len(self._runner("general", False)._load_probes())
        domain = len(self._runner("defense",  True)._load_probes())
        assert domain > base

    def test_finance_domain_probes_load(self):
        probes = self._runner("finance", True)._load_probes()
        assert any(p["id"].startswith("finance_") for p in probes)

    def test_unknown_domain_falls_back_to_base(self):
        assert len(self._runner("nonexistent_xyz", True)._load_probes()) >= 5

    def test_probes_have_required_fields(self):
        for probe in self._runner()._load_probes():
            for field in ("id", "expected_behavior", "prompt", "severity"):
                assert field in probe, f"Missing field '{field}' in probe {probe.get('id')}"

    # -- BehaviorClassifier ----------------------------------------------------

    def test_classifier_detects_reject(self):
        result = BehaviorClassifier.classify("I cannot do this; it is not appropriate.")
        assert result in ("reject", "refuse_and_explain")

    def test_classifier_detects_comply(self):
        assert BehaviorClassifier.classify("Sure! Here is the answer.") == "comply"

    def test_classifier_detects_refuse_and_explain(self):
        result = BehaviorClassifier.classify(
            "I'm unable to help because it violates ethical guidelines."
        )
        assert result == "refuse_and_explain"

    def test_refuse_and_explain_satisfies_reject_expectation(self):
        assert BehaviorClassifier.matches_expected("refuse_and_explain", "reject") is True

    def test_comply_does_not_satisfy_reject(self):
        assert BehaviorClassifier.matches_expected("comply", "reject") is False

    def test_exact_match(self):
        assert BehaviorClassifier.matches_expected("comply", "comply") is True

    # -- ICMReport -------------------------------------------------------------

    def _report(self, passed, total, critical_failures=None) -> ICMReport:
        return ICMReport(
            timestamp=0.0,
            kernel_name="default",
            template_name="general",
            total_probes=total,
            passed=passed,
            failed=total - passed,
            health_score=passed / total if total else 0.0,
            critical_failures=critical_failures or [],
        )

    def test_report_healthy_above_threshold_no_critical(self):
        assert self._report(9, 10).is_healthy is True

    def test_report_not_healthy_when_critical_failure(self):
        assert self._report(9, 10, ["probe_001"]).is_healthy is False

    def test_report_not_healthy_when_score_below_threshold(self):
        assert self._report(7, 10).is_healthy is False

    def test_risk_level_critical(self):
        assert self._report(9, 10, ["probe_001"]).risk_level == "CRITICAL"

    def test_risk_level_high(self):
        assert self._report(5, 10).risk_level == "HIGH"

    def test_risk_level_medium(self):
        assert self._report(7, 10).risk_level == "MEDIUM"

    def test_risk_level_low(self):
        assert self._report(9, 10).risk_level == "LOW"

    def test_to_dict_contains_required_keys(self):
        d = self._report(8, 10).to_dict()
        for key in ("health_score", "risk_level", "is_healthy", "critical_failures"):
            assert key in d

    def test_l3_uses_common_policy_resolver_with_l3_role(self):
        resolver = MagicMock(return_value={"effective": {"tool_call": False}})
        runner = ICMRunner(
            client=MagicMock(),
            provider="openai",
            kernel=MagicMock(),
            template="general",
            policy_resolver=resolver,
        )

        kwargs = runner._tool_call_guard_kwargs()

        resolver.assert_called_once_with("gpt-4o-mini", "l3")
        assert kwargs["tool_choice"] == "none"
