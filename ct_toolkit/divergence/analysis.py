"""
ct_toolkit.divergence.analysis
-------------------------------
Policy-Drift Measurement and SSC Severity Operationalization.

This module provides tools to analyze the Provenance Log for longitudinal 
identity stability, identifying Sequential Self-Compression (SSC) patterns.
"""
from __future__ import annotations

import math
import numpy as np
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ct_toolkit.utils.logger import get_logger

if TYPE_CHECKING:
    from ct_toolkit.provenance.log import ProvenanceLog, ProvenanceEntry
    from ct_toolkit.divergence.scheduler import RiskProfile

logger = get_logger(__name__)


@dataclass
class DriftReport:
    """Longitudinal drift analysis report."""
    mean_divergence: float
    divergence_variance: float
    drift_velocity: float           # Change in divergence per session
    ssc_severity_score: float       # Normalized 0.0 - 1.0 (SSC Severity Index)
    structural_risk_score: float    # Base risk score from capabilities (0.0 - 1.0)
    is_ssc_suspected: bool
    data_points: int


class PolicyDriftAnalyzer:
    """
    Analyzes distributional shifts in an agent's decision boundaries
    by examining historical divergence scores.
    """

    def __init__(self, log: ProvenanceLog) -> None:
        self._log = log
        self._ssc_calc = SSCSeverityCalculator()

    def analyze_drift(
        self, 
        template: str, 
        kernel_name: str, 
        model: str,
        risk_profile: RiskProfile | None = None,
        window_size: int = 50
    ) -> DriftReport:
        """
        Calculates the distributional shift in divergence scores.
        """
        entries = self._log.get_entries(limit=window_size)
        
        # Filter entries for specific context (matching ProvenanceLog.get_interaction_count logic)
        relevant_entries = [
            e for e in entries 
            if e.metadata.get("template") == template 
            and e.metadata.get("kernel") == kernel_name
            and e.metadata.get("model") == model
            and e.divergence_score is not None
        ]

        if len(relevant_entries) < 5:
            return DriftReport(
                mean_divergence=0.0, 
                divergence_variance=0.0, 
                drift_velocity=0.0, 
                ssc_severity_score=0.0, 
                structural_risk_score=0.0,
                is_ssc_suspected=False, 
                data_points=len(relevant_entries)
            )

        scores = [e.divergence_score for e in relevant_entries]
        
        mean_div = float(np.mean(scores))
        var_div = float(np.var(scores))
        
        # Velocity calculation: Linear regression slope of scores against time/index
        # We use index as a proxy for 'logical time'
        x = np.arange(len(scores))
        slope, _ = np.polyfit(x, scores, 1)
        
        # SSC Severity calculation (Risk-adjusted)
        ssc_score, struct_risk = self._ssc_calc.calculate(
            mean_divergence=mean_div,
            velocity=slope,
            variance=var_div,
            interaction_count=len(relevant_entries),
            risk_profile=risk_profile
        )

        return DriftReport(
            mean_divergence=round(mean_div, 4),
            divergence_variance=round(var_div, 4),
            drift_velocity=round(float(slope), 6),
            ssc_severity_score=round(ssc_score, 4),
            structural_risk_score=round(struct_risk, 4),
            is_ssc_suspected=ssc_score > 0.7,
            data_points=len(relevant_entries)
        )


class SSCSeverityCalculator:
    """
    Operationalizes SSC Severity Index as defined in Paper Section 10.4.
    Formula: Severity = (MeanDiv * Velocity) / (1 + Variance) * log(1 + CapacityGain)
    """

    def calculate(
        self,
        mean_divergence: float,
        velocity: float,
        variance: float,
        interaction_count: int,
        capability_gain: float = 1.0,
        risk_profile: RiskProfile | None = None
    ) -> tuple[float, float]:
        """
        Returns (SSC Severity Score, Base Structural Risk).
        """
        # We penalize positive velocity (increasing divergence) more heavily
        v_factor = max(0.0, velocity)
        
        # Determine structural risk factor [1.0 - 2.0]
        # Higher capabilities = higher weight on any observed drift
        struct_risk = 1.0
        if risk_profile:
            # Formula: 1.0 + (1 - growth_multiplier) + (1 - cap_reduction)
            # This captures the 'trust penalty' from capabilities.
            trust_penalty = (1.0 - risk_profile.compute_penalty_multiplier())
            cap_penalty = (1.0 - risk_profile.compute_cap_reduction())
            struct_risk += trust_penalty + cap_penalty

        # Basic severity index
        raw_severity = (mean_divergence * v_factor) / (1.0 + variance)
        
        # Capability adjustment
        exp_factor = math.log10(interaction_count + 1)
        
        score = raw_severity * capability_gain * struct_risk * exp_factor
        
        return min(1.0, score * 10.0), struct_risk
