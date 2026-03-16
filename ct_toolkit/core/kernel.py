"""
ct_toolkit.core.kernel
-----------------------
Constitutional Kernel: Contains the axiomatic anchors that the system can never change
and plastic commitments that can be extended by the user.
"""
from __future__ import annotations

import yaml
import importlib.resources
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

from ct_toolkit.core.exceptions import (
    AxiomaticViolationError,
    PlasticConflictError,
    CTToolkitError,
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

    def __init__(self, profile: KernelProfile, is_readonly: bool = False) -> None:
        self._profile = profile
        self.is_readonly = is_readonly

    @classmethod
    def from_yaml(cls, path) -> ConstitutionalKernel:
        if hasattr(path, "open"):
            with path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        else:
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
        # Use importlib.resources to find the default kernel regardless of installation path
        try:
            from importlib.resources import files
            # Load built-in kernel using importlib.resources
            kernel_resource = files("ct_toolkit.kernels").joinpath("default.yaml")
            if kernel_resource.is_file(): # Use is_file() for Traversable objects
                return ConstitutionalKernel.from_yaml(kernel_resource)
            else:
                raise FileNotFoundError(f"Default kernel resource not found: {kernel_resource}")
        except (ImportError, FileNotFoundError):
            # Fallback for older python or weird environments
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
        if self.is_readonly:
            raise CTToolkitError(f"Cannot update commitment '{commitment_id}': Kernel is read-only.")
        for c in self._profile.plastic_commitments:
            if c.id == commitment_id:
                c.current_value = new_value
                return
        raise KeyError(f"Commitment not found: '{commitment_id}'")

    def to_dict(self) -> dict[str, Any]:
        """Serializes the kernel to a dictionary."""
        return {
            "name": self._profile.name,
            "version": self._profile.version,
            "description": self._profile.description,
            "axiomatic_anchors": [
                {"id": a.id, "description": a.description, "keywords": a.keywords}
                for a in self.anchors
            ],
            "plastic_commitments": [
                {
                    "id": c.id,
                    "description": c.description,
                    "default_value": c.default_value,
                    "current_value": c.current_value,
                    "keywords": c.keywords
                }
                for c in self.commitments
            ],
            "is_readonly": self.is_readonly
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConstitutionalKernel:
        """Creates a kernel from a dictionary."""
        anchors = [AxiomaticAnchor(**a) for a in data.get("axiomatic_anchors", [])]
        commitments = [PlasticCommitment(**c) for c in data.get("plastic_commitments", [])]
        
        profile = KernelProfile(
            name=data["name"],
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            axiomatic_anchors=anchors,
            plastic_commitments=commitments,
        )
        return cls(profile, is_readonly=data.get("is_readonly", False))

    def merge(self, other: ConstitutionalKernel) -> ConstitutionalKernel:
        """
        Merges another kernel into this one.
        The 'other' kernel's anchors and commitments are added as axiomatic anchors
        in the new merged kernel to ensure propagation constraints are non-negotiable.
        """
        new_anchors = list(self.anchors)
        
        # Add other's anchors
        for a in other.anchors:
            if not any(existing.id == a.id for existing in new_anchors):
                new_anchors.append(a)
        
        # Convert other's commitments to axiomatic anchors in the merged result
        for c in other.commitments:
            anchor_id = f"propagated_{c.id}"
            if not any(existing.id == anchor_id for existing in new_anchors):
                new_anchors.append(AxiomaticAnchor(
                    id=anchor_id,
                    description=f"{c.description} (Propagated: {c.current_value})",
                    keywords=c.keywords
                ))
        
        new_profile = KernelProfile(
            name=f"{self.name}_merged_{other.name}",
            version=self._profile.version,
            description=f"Merged kernel: {self.name} + {other.name}",
            axiomatic_anchors=new_anchors,
            plastic_commitments=list(self.commitments)
        )
        return ConstitutionalKernel(new_profile, is_readonly=self.is_readonly)

    def __repr__(self) -> str:
        return (
            f"ConstitutionalKernel(name={self.name!r}, "
            f"anchors={len(self.anchors)}, "
            f"commitments={len(self.commitments)})"
        )
