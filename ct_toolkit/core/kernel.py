"""
ct_toolkit.core.kernel
-----------------------
Constitutional Kernel: Contains the axiomatic anchors that the system can never change
and plastic commitments that can be extended by the user.
"""
from __future__ import annotations

import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

from ct_toolkit.core.exceptions import (
    AxiomaticViolationError,
    PlasticConflictError,
)


# ── Data Models ─────────────────────────────────────────────────────────────

@dataclass
class AxiomaticAnchor:
    id: str
    description: str
    keywords: list = field(default_factory=list)


@dataclass
class PlasticCommitment:
    id: str
    description: str
    default_value: Any = None
    current_value: Any = None
    keywords: list = field(default_factory=list)

    def __post_init__(self):
        if self.current_value is None:
            self.current_value = self.default_value


@dataclass
class KernelProfile:
    name: str
    version: str = "1.0.0"
    description: str = ""
    axiomatic_anchors: list = field(default_factory=list)
    plastic_commitments: list = field(default_factory=list)


# ── Main Kernel Class ──────────────────────────────────────────────────────────

class ConstitutionalKernel:
    """
    The ethical and behavioral core of the system.

    Usage:
        kernel = ConstitutionalKernel.from_yaml("kernels/defense.yaml")
        kernel.validate_user_rule("allow classified data sharing")
    """

    def __init__(self, profile: KernelProfile) -> None:
        self._profile = profile

    @classmethod
    def from_yaml(cls, path) -> ConstitutionalKernel:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        anchors = [AxiomaticAnchor(**a) for a in data.get("axiomatic_anchors", [])]
        commitments = [PlasticCommitment(**c) for c in data.get("plastic_commitments", [])]

        profile = KernelProfile(
            name=data["name"],
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            axiomatic_anchors=anchors,
            plastic_commitments=commitments,
        )
        return cls(profile)

    @classmethod
    def default(cls) -> ConstitutionalKernel:
        default_path = Path(__file__).parent.parent / "kernels" / "default.yaml"
        return cls.from_yaml(default_path)

    @property
    def name(self) -> str:
        return self._profile.name

    @property
    def anchors(self) -> list:
        return self._profile.axiomatic_anchors

    @property
    def commitments(self) -> list:
        return self._profile.plastic_commitments

    def get_system_prompt_injection(self) -> str:
        lines = [
            "# Constitutional Identity Kernel",
            "The unchangeable core rules of this system are below:",
            "",
        ]
        for anchor in self.anchors:
            lines.append(f"- {anchor.description}")

        active = [c for c in self.commitments if c.current_value not in (None, False, "")]
        if active:
            lines += ["", "## Active Behavioral Rules"]
            for c in active:
                lines.append(f"- {c.description}: {c.current_value}")

        lines += ["", "---", ""]
        return "\n".join(lines)

    def validate_user_rule(self, rule_text: str) -> None:
        rule_lower = rule_text.lower()
        for anchor in self.anchors:
            if self._conflicts_with(rule_lower, anchor.keywords):
                raise AxiomaticViolationError(rule=rule_text, anchor=anchor.id)
        for commitment in self.commitments:
            if self._conflicts_with(rule_lower, commitment.keywords):
                raise PlasticConflictError(rule=rule_text, commitment=commitment.id)

    def _conflicts_with(self, rule_lower: str, keywords: list) -> bool:
        return any(kw.lower() in rule_lower for kw in keywords)

    def update_commitment(self, commitment_id: str, new_value: Any) -> None:
        for c in self._profile.plastic_commitments:
            if c.id == commitment_id:
                c.current_value = new_value
                return
        raise KeyError(f"Commitment not found: '{commitment_id}'")

    def __repr__(self) -> str:
        return (
            f"ConstitutionalKernel(name={self.name!r}, "
            f"anchors={len(self.anchors)}, "
            f"commitments={len(self.commitments)})"
        )
