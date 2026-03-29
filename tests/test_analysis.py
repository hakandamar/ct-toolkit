import unittest
from unittest.mock import MagicMock
from ct_toolkit.divergence.analysis import PolicyDriftAnalyzer, SSCSeverityCalculator
from ct_toolkit.provenance.log import ProvenanceEntry

class TestPolicyDrift(unittest.TestCase):
    def setUp(self):
        self.mock_log = MagicMock()
        self.analyzer = PolicyDriftAnalyzer(self.mock_log)

    def test_drift_calculation(self):
        # Create a sequence of entries with increasing divergence score (SSC pattern)
        entries = []
        for i in range(10):
            entry = MagicMock(spec=ProvenanceEntry)
            entry.divergence_score = 0.05 + (i * 0.02) # Increases from 0.05 up to 0.23
            entry.metadata = {"template": "general", "kernel": "standard", "model": "gpt-4"}
            entries.append(entry)
        
        self.mock_log.get_entries.return_value = entries
        
        report = self.analyzer.analyze_drift("general", "standard", "gpt-4")
        
        self.assertEqual(report.data_points, 10)
        self.assertGreater(report.drift_velocity, 0) # Should be positive slope
        self.assertGreater(report.mean_divergence, 0.1)
        # Severity should be calculated
        self.assertGreater(report.ssc_severity_score, 0)
        
    def test_low_data_points(self):
        entry = MagicMock(spec=ProvenanceEntry)
        entry.divergence_score = 0.1
        entry.metadata = {"template": "general", "kernel": "standard", "model": "gpt-4"}
        self.mock_log.get_entries.return_value = [entry] * 2
        
        report = self.analyzer.analyze_drift("general", "standard", "gpt-4")
        self.assertEqual(report.data_points, 2)
        self.assertEqual(report.ssc_severity_score, 0.0)
    
    def test_risk_normalized_severity(self):
        from ct_toolkit.divergence.scheduler import RiskProfile
        # Case 1: Low risk text-only agent
        low_risk = RiskProfile(has_tool_calling=False)
        # Case 2: High risk agent with tools and MCP
        high_risk = RiskProfile(has_tool_calling=True, mcp_server_count=3)
        
        calc = SSCSeverityCalculator()
        # High drift scenario
        score_low, risk_low = calc.calculate(0.2, 0.05, 0.01, 100, risk_profile=low_risk)
        score_high, risk_high = calc.calculate(0.2, 0.05, 0.01, 100, risk_profile=high_risk)
        
        self.assertGreater(risk_high, risk_low)
        self.assertGreater(score_high, score_low)
        print(f"Risk Normalized Test: LowRiskScore={score_low}, HighRiskScore={score_high}")

    def test_missing_metadata(self):
        # Entry with missing template/kernel/model should be ignored
        entry_missing = MagicMock(spec=ProvenanceEntry)
        entry_missing.divergence_score = 0.5
        entry_missing.metadata = {} # Missing everything
        
        entry_valid = MagicMock(spec=ProvenanceEntry)
        entry_valid.divergence_score = 0.1
        entry_valid.metadata = {"template": "general", "kernel": "standard", "model": "gpt-4"}
        
        self.mock_log.get_entries.return_value = [entry_missing] * 10 + [entry_valid] * 5
        
        report = self.analyzer.analyze_drift("general", "standard", "gpt-4")
        # Only the 5 valid ones should be counted
        self.assertEqual(report.data_points, 5)

    def test_inconsistent_scores(self):
        # Even with high variance and negative velocity, shouldn't crash
        entries = []
        for i in range(10):
            entry = MagicMock(spec=ProvenanceEntry)
            entry.divergence_score = 0.5 - (i * 0.05) # Decreasing divergence
            entry.metadata = {"template": "general", "kernel": "standard", "model": "gpt-4"}
            entries.append(entry)
            
        self.mock_log.get_entries.return_value = entries
        report = self.analyzer.analyze_drift("general", "standard", "gpt-4")
        self.assertLessEqual(report.drift_velocity, 0)
        self.assertEqual(report.ssc_severity_score, 0.0) # Negative velocity = 0 severity

class TestSSCSeverity(unittest.TestCase):
    def test_severity_formula(self):
        calc = SSCSeverityCalculator()
        # High divergence, high velocity, low variance = High SSC risk
        score_high, _ = calc.calculate(0.3, 0.05, 0.001, 100)
        # Low divergence, zero velocity = Low SSC risk
        score_low, _ = calc.calculate(0.05, 0.0, 0.01, 10)
        
        self.assertGreater(score_high, score_low)
        self.assertLessEqual(score_high, 1.0)
        self.assertEqual(score_low, 0.0)

if __name__ == "__main__":
    unittest.main()
