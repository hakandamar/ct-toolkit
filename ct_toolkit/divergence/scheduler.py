"""
ct_toolkit.divergence.scheduler
-------------------------------
Dynamic Elasticity Scheduler for Stability-Plasticity balance.

According to the NAA framework, as an agent gains experience (accumulated interactions),
its threshold for safe normative divergence (plasticity) should increase from a conservative
baseline to an elastic maximum.

The scheduler incorporates a RiskProfile. Models with access to tools, vision, or
opaque MCP servers pose a higher structural risk. Therefore, their elasticity
growth rate is penalized, and their maximum thresholds are clamped.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from ct_toolkit.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RiskProfile:
    """
    Defines the structural risk profile of the agent based on its capabilities.
    Higher capabilities = slower trust building and lower maximum divergence caps.
    """
    has_tool_calling: bool = False
    has_vision_audio: bool = False
    mcp_server_count: int = 0

    def compute_penalty_multiplier(self) -> float:
        """
        Calculates a penalty multiplier [0.1, 1.0] for the elasticity growth rate.
        1.0 means full growth speed (low risk text-only), 0.1 means 10x slower growth.
        """
        multiplier = 1.0
        
        if self.has_tool_calling:
            multiplier *= 0.7  # 30% slower growth
            
        if self.has_vision_audio:
            multiplier *= 0.9  # 10% slower
            
        if self.mcp_server_count > 0:
            # MCP servers are highly opaque multi-action networks.
            # 50% slower per MCP server, capped at a harsh 0.2 factor.
            mcp_penalty = max(0.2, 0.5 ** self.mcp_server_count)
            multiplier *= mcp_penalty
            
        return max(0.1, multiplier)

    def compute_cap_reduction(self) -> float:
        """
        Calculates how much the maximum theoretical threshold ceiling should
        be lowered based on structural risk. Returns a factor [0.5, 1.0].
        1.0 means no reduction (can reach absolute max threshold).
        """
        reduction = 1.0
        
        if self.has_tool_calling:
            reduction -= 0.1
            
        if self.mcp_server_count > 0:
            reduction -= 0.2
            
        # Ensure we don't reduce the ceiling below 50% of its theoretical max span
        return max(0.5, reduction)


class ElasticityScheduler:
    """
    Calculates dynamic divergence thresholds (L1, L2, L3) based on the
    agent's interaction history (experience) and structural RiskProfile.
    """

    def __init__(
        self,
        base_thresholds: tuple[float, float, float] = (0.15, 0.30, 0.50),
        max_thresholds: tuple[float, float, float] = (0.25, 0.45, 0.70),
        growth_rate: float = 0.001,
        risk_profile: RiskProfile | None = None,
    ) -> None:
        """
        Args:
            base_thresholds: Starting (L1, L2, L3) values for a new agent.
            max_thresholds: Absolute maximum (L1, L2, L3) limits.
            growth_rate: Baseline rate at which experience converts to elasticity.
            risk_profile: Optional structural risk capacities.
        """
        self.base_l1, self.base_l2, self.base_l3 = base_thresholds
        self.max_l1, self.max_l2, self.max_l3 = max_thresholds
        
        self.risk_profile = risk_profile or RiskProfile()
        
        # Apply risk penalties
        self.growth_rate = growth_rate * self.risk_profile.compute_penalty_multiplier()
        self.cap_reduction = self.risk_profile.compute_cap_reduction()

        logger.debug(
            f"ElasticityScheduler initialized | base_rate={growth_rate} | "
            f"effective_rate={self.growth_rate:.5f} | cap_reduction={self.cap_reduction:.2f}"
        )

    def calculate_thresholds(
        self, interaction_count: int
    ) -> tuple[float, float, float]:
        """
        Calculates active thresholds using a bounded asymptotic growth curve:
        Threshold(t) = Base + (Max - Base) * CapFactor * (1 - e^(-growth_rate * t))
        """
        if interaction_count <= 0:
            return self.base_l1, self.base_l2, self.base_l3

        # Bounded growth curve [0.0 -> 1.0)
        growth_factor = 1.0 - math.exp(-self.growth_rate * interaction_count)
        
        # Apply risk reduction to how far along the (Max - Base) span we can travel
        effective_factor = growth_factor * self.cap_reduction

        l1 = self.base_l1 + (self.max_l1 - self.base_l1) * effective_factor
        l2 = self.base_l2 + (self.max_l2 - self.base_l2) * effective_factor
        l3 = self.base_l3 + (self.max_l3 - self.base_l3) * effective_factor

        return round(l1, 4), round(l2, 4), round(l3, 4)
