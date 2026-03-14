"""
ct_toolkit.core.exceptions
--------------------------
Exception hierarchy used throughout the toolkit.
"""


class CTToolkitError(Exception):
    """Base class for all CT Toolkit errors."""


class MissingClientError(CTToolkitError):
    """Raised when a provider client is required but not provided or found in environment."""


# ── Kernel Errors ────────────────────────────────────────────────────────────

class KernelError(CTToolkitError):
    """General error related to Constitutional Kernel."""


class AxiomaticViolationError(KernelError):
    """
    Raised when a user-defined rule conflicts with an Axiomatic Anchor.
    Hard reject — system will not proceed.
    """
    def __init__(self, rule: str, anchor: str):
        self.rule = rule
        self.anchor = anchor
        super().__init__(
            f"Hard reject: Rule '{rule}' conflicts with axiomatic anchor '{anchor}'. "
            "This rule cannot be modified."
        )


class PlasticConflictError(KernelError):
    """
    Raised when a user-defined rule conflicts with a Plastic Commitment.
    Initiates the Reflective Endorsement flow.
    """
    def __init__(self, rule: str, commitment: str):
        self.rule = rule
        self.commitment = commitment
        super().__init__(
            f"Conflict detected: Rule '{rule}' conflicts with '{commitment}'. "
            "Reflective Endorsement approval is required."
        )


# ── Compatibility Errors ─────────────────────────────────────────────────────────

class CompatibilityError(CTToolkitError):
    """Template and Kernel mismatch."""


class IncompatibleProfileError(CompatibilityError):
    """Template + Kernel combination marked as conflicting."""
    def __init__(self, template: str, kernel: str):
        self.template = template
        self.kernel = kernel
        super().__init__(
            f"Template '{template}' and kernel '{kernel}' create an incompatible combination. "
            "This profile cannot be used."
        )


# ── Divergence Errors ────────────────────────────────────────────────────────

class DivergenceError(CTToolkitError):
    """General error related to identity divergence."""


class CriticalDivergenceError(DivergenceError):
    """
    Raised when L3 ICM result exceeds the threshold.
    System must take action (warn / halt / rollback).
    """
    def __init__(self, score: float, threshold: float, tier: str):
        self.score = score
        self.threshold = threshold
        self.tier = tier
        super().__init__(
            f"Critical divergence detected [{tier}]: "
            f"score={score:.4f}, threshold={threshold:.4f}. Action is required."
        )


# ── Provenance Errors ────────────────────────────────────────────────────────

class ProvenanceError(CTToolkitError):
    """General error related to Provenance Log."""


class ChainIntegrityError(ProvenanceError):
    """When the HMAC chain is broken — manipulation or corruption detected."""
    def __init__(self, entry_id: str):
        self.entry_id = entry_id
        super().__init__(
            f"Provenance Log chain is broken! Entry '{entry_id}' contains an invalid HMAC. "
            "The log may have been manipulated."
        )


class VaultError(ProvenanceError):
    """Vault connection or authorization error."""
