"""
ct_toolkit.endorsement
======================
Reflective Endorsement Protocol for kernel updates.

This module provides:
- ReflectiveEndorsement: Multi-stage approval protocol for kernel changes
- StagedUpdateManager: Manages sandbox/staged kernel updates
- CooldownCalculator: Calculates cooldown periods based on risk
"""

from ct_toolkit.endorsement.reflective import (
    ReflectiveEndorsement,
    StagedUpdateManager,
    CooldownCalculator,
)

__all__ = [
    "ReflectiveEndorsement",
    "StagedUpdateManager",
    "CooldownCalculator",
]
