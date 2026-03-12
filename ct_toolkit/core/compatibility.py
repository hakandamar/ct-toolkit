"""
ct_toolkit.core.compatibility
------------------------------
Compatibility check of Template and Kernel combinations.

Three levels:
  NATIVE      — natural combination, works directly
  COMPATIBLE  — works, combined profile is generated and logged
  CONFLICTING — hard reject, cannot be used
"""
from __future__ import annotations

from enum import Enum
from dataclasses import dataclass

from ct_toolkit.core.exceptions import IncompatibleProfileError


class CompatibilityLevel(str, Enum):
    NATIVE = "native"
    COMPATIBLE = "compatible"
    CONFLICTING = "conflicting"


@dataclass(frozen=True)
class CompatibilityResult:
    level: CompatibilityLevel
    template: str
    kernel: str
    notes: str = ""

    @property
    def is_usable(self) -> bool:
        return self.level != CompatibilityLevel.CONFLICTING

    @property
    def requires_re_flow(self) -> bool:
        """Compatible combinations require user approval and log recording."""
        return self.level == CompatibilityLevel.COMPATIBLE


# ── Compatibility Matrix ──────────────────────────────────────────────────────────
# (template, kernel) → CompatibilityLevel

_MATRIX: dict[tuple[str, str], tuple[CompatibilityLevel, str]] = {
    # Native combinations
    ("general", "default"):     (CompatibilityLevel.NATIVE, ""),
    ("medical", "medical"):     (CompatibilityLevel.NATIVE, ""),
    ("finance", "finance"):     (CompatibilityLevel.NATIVE, ""),
    ("defense", "defense"):     (CompatibilityLevel.NATIVE, ""),
    ("legal", "legal"):         (CompatibilityLevel.NATIVE, ""),
    ("research", "research"):   (CompatibilityLevel.NATIVE, ""),

    # Compatible combinations
    ("medical", "defense"):     (
        CompatibilityLevel.COMPATIBLE,
        "Military medical application: defense kernel has priority. "
        "The privacy level of medical data is subject to defense rules."
    ),
    ("medical", "research"):    (
        CompatibilityLevel.COMPATIBLE,
        "Medical application for research purposes: research kernel has priority."
    ),
    ("finance", "legal"):       (
        CompatibilityLevel.COMPATIBLE,
        "Legal-financial application: legal kernel has priority."
    ),
    ("research", "defense"):    (
        CompatibilityLevel.COMPATIBLE,
        "Defense research: defense kernel has priority."
    ),
    ("general", "defense"):     (
        CompatibilityLevel.COMPATIBLE,
        "General template used with defense kernel. "
        "Defense axiomatic anchors are active."
    ),
    ("general", "finance"):     (CompatibilityLevel.COMPATIBLE, ""),
    ("general", "medical"):     (CompatibilityLevel.COMPATIBLE, ""),
    ("general", "legal"):       (CompatibilityLevel.COMPATIBLE, ""),

    # Conflicting combinations
    ("entertainment", "defense"): (
        CompatibilityLevel.CONFLICTING,
        "Entertainment template cannot be used with the defense kernel."
    ),
    ("entertainment", "medical"): (
        CompatibilityLevel.CONFLICTING,
        "Entertainment template cannot be used with the medical kernel."
    ),
    ("marketing", "defense"):    (
        CompatibilityLevel.CONFLICTING,
        "Marketing template cannot be used with the defense kernel."
    ),
    ("marketing", "medical"):    (
        CompatibilityLevel.CONFLICTING,
        "Marketing template cannot be used with the medical kernel."
    ),
}


class CompatibilityLayer:
    """
    Evaluates Template + Kernel combinations.

    Usage:
        result = CompatibilityLayer.check("medical", "defense")
        if result.requires_re_flow:
            # Request user approval, write to log
    """

    @staticmethod
    def check(template: str, kernel: str) -> CompatibilityResult:
        """
        Checks the combination. Undefined combinations are assumed COMPATIBLE
        (unknown = allow but log).
        """
        key = (template.lower(), kernel.lower())
        level, notes = _MATRIX.get(key, (CompatibilityLevel.COMPATIBLE, ""))

        result = CompatibilityResult(
            level=level,
            template=template,
            kernel=kernel,
            notes=notes,
        )

        if not result.is_usable:
            raise IncompatibleProfileError(template=template, kernel=kernel)

        return result

    @staticmethod
    def list_compatible_kernels(template: str) -> list[str]:
        """Lists kernels that can be used with a specific template."""
        return [
            kernel
            for (tmpl, kernel), (level, _) in _MATRIX.items()
            if tmpl == template.lower() and level != CompatibilityLevel.CONFLICTING
        ]

    @staticmethod
    def list_compatible_templates(kernel: str) -> list[str]:
        """Lists templates that can be used with a specific kernel."""
        return [
            tmpl
            for (tmpl, k), (level, _) in _MATRIX.items()
            if k == kernel.lower() and level != CompatibilityLevel.CONFLICTING
        ]
