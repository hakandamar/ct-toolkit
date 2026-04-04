"""
ct_toolkit.core
===============
Core components of the Computational Theseus Toolkit.

This module provides:
- ConstitutionalKernel: Ethical and behavioral core of the system
- TheseusWrapper: LLM wrapper with constitutional guard
- CompatibilityLayer: Template/kernel compatibility checking
- ContextCompressionGuard: Context window protection
- IntegrityMonitor: File integrity monitoring
- Core exceptions
"""

from ct_toolkit.core.wrapper import TheseusWrapper, CTResponse, WrapperConfig
from ct_toolkit.core.kernel import ConstitutionalKernel, KernelProfile, AxiomaticAnchor, PlasticCommitment
from ct_toolkit.core.compatibility import CompatibilityLayer, CompatibilityLevel, CompatibilityResult
from ct_toolkit.core.exceptions import (
    CTToolkitError,
    AxiomaticViolationError,
    PlasticConflictError,
    IncompatibleProfileError,
)
from ct_toolkit.core.compression_guard import ContextCompressionGuard
from ct_toolkit.core.integrity import IntegrityMonitor
from ct_toolkit.core.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerError,
    CircuitBreakerStats,
    CircuitBreakerRegistry,
    CircuitState,
)

__all__ = [
    # Wrapper
    "TheseusWrapper",
    "CTResponse",
    "WrapperConfig",
    # Kernel
    "ConstitutionalKernel",
    "KernelProfile",
    "AxiomaticAnchor",
    "PlasticCommitment",
    # Compatibility
    "CompatibilityLayer",
    "CompatibilityLevel",
    "CompatibilityResult",
    # Compression
    "ContextCompressionGuard",
    # Integrity
    "IntegrityMonitor",
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitBreakerError",
    "CircuitBreakerStats",
    "CircuitBreakerRegistry",
    "CircuitState",
    # Exceptions
    "CTToolkitError",
    "MissingClientError",
    "KernelError",
    "AxiomaticViolationError",
    "PlasticConflictError",
    "CompatibilityError",
    "IncompatibleProfileError",
    "DivergenceError",
    "CriticalDivergenceError",
    "CriticalSandboxDivergenceError",
    "ProvenanceError",
    "ChainIntegrityError",
    "VaultError",
    "ConfigurationTamperingError",
]
