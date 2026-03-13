import pytest
from ct_toolkit.divergence.scheduler import ElasticityScheduler, RiskProfile

class TestElasticityScheduler:
    
    def test_default_initialization(self):
        scheduler = ElasticityScheduler()
        assert scheduler.growth_rate == 0.001
        assert scheduler.base_l1 == 0.15
        assert scheduler.max_l1 == 0.25

    def test_risk_profile_multipliers(self):
        # Tools: 0.7x growth, -0.1 cap
        profile = RiskProfile(has_tool_calling=True)
        assert profile.compute_penalty_multiplier() == 0.7
        assert profile.compute_cap_reduction() == 0.9

        # MCP servers: 1 server = 0.5x growth, -0.2 cap
        profile_mcp = RiskProfile(mcp_server_count=1)
        assert profile_mcp.compute_penalty_multiplier() == 0.5
        assert profile_mcp.compute_cap_reduction() == 0.8

        # Combined (all traits):
        # 0.7 * 0.9 * max(0.2, 0.5^2) = 0.7 * 0.9 * 0.25 = 0.1575
        # 1.0 - 0.1 - 0.2 = 0.7 cap
        profile_heavy = RiskProfile(has_tool_calling=True, has_vision_audio=True, mcp_server_count=2)
        assert abs(profile_heavy.compute_penalty_multiplier() - 0.1575) < 0.0001
        assert profile_heavy.compute_cap_reduction() == 0.7

    def test_calculate_thresholds_zero_experience(self):
        scheduler = ElasticityScheduler()
        l1, l2, l3 = scheduler.calculate_thresholds(0)
        assert l1 == scheduler.base_l1
        assert l2 == scheduler.base_l2
        assert l3 == scheduler.base_l3

    def test_calculate_thresholds_growth_over_time(self):
        scheduler = ElasticityScheduler(
            base_thresholds=(0.10, 0.20, 0.30),
            max_thresholds=(0.20, 0.40, 0.60),
            growth_rate=0.01  # faster growth for testing
        )

        l1_start, _, _ = scheduler.calculate_thresholds(0)
        l1_mid, _, _ = scheduler.calculate_thresholds(50)
        l1_late, _, _ = scheduler.calculate_thresholds(1000)

        assert l1_start == 0.10
        assert l1_start < l1_mid < l1_late
        assert l1_late <= 0.20
        # After 1000 interactions with 0.01 rate, it should be very close to max
        assert abs(l1_late - 0.20) < 0.01

    def test_risk_profile_restricts_growth_and_caps(self):
        base = (0.10, 0.20, 0.30)
        upper = (0.30, 0.50, 0.70)
        
        # Safe text model
        scheduler_safe = ElasticityScheduler(base, upper, growth_rate=0.01, risk_profile=RiskProfile())
        l1_safe, _, _ = scheduler_safe.calculate_thresholds(500)
        
        # Risky multi-modal tool with MCP (slow growth, capped max)
        scheduler_risky = ElasticityScheduler(
            base, upper, growth_rate=0.01, 
            risk_profile=RiskProfile(has_tool_calling=True, mcp_server_count=1)
        )
        l1_risky, _, _ = scheduler_risky.calculate_thresholds(500)
        
        # Risky model should have lower permitted threshold than safe model
        # despite having same amount of interactions
        assert l1_risky < l1_safe
        
        # Test the cap on the risky model at infinity
        l1_risky_inf, _, _ = scheduler_risky.calculate_thresholds(999999)
        # risky cap reduction is 1.0 - 0.1(tools) - 0.2(mcp) = 0.7
        # theoretical max diff is (0.3 - 0.1) = 0.2
        # permitted max diff = 0.2 * 0.7 = 0.14
        # expected max l1 = 0.10 + 0.14 = 0.24
        assert abs(l1_risky_inf - 0.24) < 0.01
