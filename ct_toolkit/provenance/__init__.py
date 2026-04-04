"""
ct_toolkit.provenance
=====================
Provenance logging and vault management.

This module provides:
- ProvenanceLog: HMAC-chain tamper-evident logging
- Vault management for secure storage
"""

from ct_toolkit.provenance.log import ProvenanceLog

__all__ = [
    "ProvenanceLog",
]