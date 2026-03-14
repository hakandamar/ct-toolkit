"""
ct_toolkit.endorsement.reflective
-----------------------------------
Reflective Endorsement (RE) protocol.

Flow:
  1. User-defined rule conflicts with kernel → PlasticConflictError is caught
  2. ConflictRecord is created — conflict details are documented
  3. User is directed to approval channel (CLI / callback / API)
  4. If user approves → EndorsementRecord is signed, written to Provenance Log
  5. Kernel is updated, system continues to operate
  6. If user rejects → system remains unchanged, rejection record written to log

Each override is additionally monitored in subsequent ICM tests (flagged=True).
"""
from __future__ import annotations

import hashlib
import json
import time
import sys
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Callable, Any

from ct_toolkit.core.exceptions import PlasticConflictError, AxiomaticViolationError
from ct_toolkit.utils.logger import get_logger

logger = get_logger(__name__)


# ── Data Models ─────────────────────────────────────────────────────────────

class EndorsementDecision(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    PENDING  = "pending"


@dataclass
class ConflictRecord:
    """Details of the detected conflict."""
    id: str
    timestamp: float
    rule_text: str                  # Rule defined by the user
    conflicting_commitment_id: str  # Which plastic commitment it conflicts with
    conflict_description: str       # Description
    kernel_name: str

    def summary(self) -> str:
        return (
            f"\n{'='*60}\n"
            f"⚠️  RULE CONFLICT DETECTED\n"
            f"{'='*60}\n"
            f"  Rule           : {self.rule_text}\n"
            f"  Conflicting CC : {self.conflicting_commitment_id}\n"
            f"  Kernel         : {self.kernel_name}\n"
            f"  Description    : {self.conflict_description}\n"
            f"{'='*60}"
        )


@dataclass
class EndorsementRecord:
    """Signed record of user approval/rejection decision."""
    id: str
    timestamp: float
    conflict_id: str
    rule_text: str
    commitment_id: str
    decision: EndorsementDecision
    operator_id: str                # Who approved / rejected
    rationale: str                  # Why it was approved / rejected
    kernel_name: str
    content_hash: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        if not self.content_hash:
            self.content_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        payload = json.dumps({
            "id": self.id,
            "timestamp": self.timestamp,
            "conflict_id": self.conflict_id,
            "rule_text": self.rule_text,
            "commitment_id": self.commitment_id,
            "decision": self.decision,
            "operator_id": self.operator_id,
            "rationale": self.rationale,
            "kernel_name": self.kernel_name,
        }, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()

    def to_provenance_metadata(self) -> dict[str, Any]:
        """Metadata to be written to Provenance Log."""
        return {
            "event_type": "reflective_endorsement",
            "endorsement_id": self.id,
            "conflict_id": self.conflict_id,
            "decision": self.decision,
            "operator_id": self.operator_id,
            "rule_text": self.rule_text,
            "commitment_id": self.commitment_id,
            "kernel_name": self.kernel_name,
            "content_hash": self.content_hash,
            "flagged_for_icm": self.decision == EndorsementDecision.APPROVED and self.conflict_id != "none",
        }


# ── Approval Channels ─────────────────────────────────────────────────────────────

ApprovalCallback = Callable[[ConflictRecord], tuple[EndorsementDecision, str, str]]
"""
Callback type for custom approval channel.
Returns: (decision, operator_id, rationale)
"""


def cli_approval_channel(conflict: ConflictRecord) -> tuple[EndorsementDecision, str, str]:
    """
    Default CLI approval channel.
    Prompts user for approval in interactive terminal.
    
    WARNING: This blocks the current thread. In server environments (FastAPI/Flask),
    always use a custom non-blocking callback.
    """
    # Safety check for non-interactive environments (CI, Background workers, Servers)
    if not sys.stdin.isatty():
        logger.warning(
            f"RE flow: cli_approval_channel called in non-interactive environment. "
            f"Conflict ID: {conflict.id[:8]}... Auto-returning PENDING."
        )
        return EndorsementDecision.PENDING, "system", "Awaiting external approval (non-TTY)"

    print(conflict.summary())
    print("\nDo you want to override this rule conflict?")
    print("  [y] Yes — approve and sign override")
    print("  [n] No — cancel, keep existing rule")

    while True:
        try:
            choice = input("\nYour decision (y/n): ").strip().lower()
            if choice in ("y", "yes"):
                operator_id = input("Operator ID (name/email): ").strip() or "anonymous"
                rationale = input("Override rationale: ").strip() or "Manual approval"
                return EndorsementDecision.APPROVED, operator_id, rationale
            elif choice in ("n", "no"):
                return EndorsementDecision.REJECTED, "system", "User rejected"
            else:
                print("Invalid input. Type 'y' or 'n'.")
        except EOFError:
            # Handle cases where input() is called but stdin is closed
            return EndorsementDecision.PENDING, "system", "Stdin closed while awaiting input"


def auto_approve_channel(
    operator_id: str = "auto",
    rationale: str = "Auto approval",
) -> ApprovalCallback:
    """
    Auto approval channel for test and CI environments.
    Do not use in production.
    """
    def _channel(conflict: ConflictRecord) -> tuple[EndorsementDecision, str, str]:
        logger.warning(
            f"AUTO-APPROVE active: Override of '{conflict.rule_text}' auto-approved. "
            "This channel should only be used in test environments."
        )
        return EndorsementDecision.APPROVED, operator_id, rationale
    return _channel


def auto_reject_channel() -> ApprovalCallback:
    """Auto reject channel for test environments."""
    def _channel(conflict: ConflictRecord) -> tuple[EndorsementDecision, str, str]:
        return EndorsementDecision.REJECTED, "auto", "Auto rejection"
    return _channel


# ── Main RE Class ──────────────────────────────────────────────────────────────

class ReflectiveEndorsement:
    """
    Reflective Endorsement protocol manager.

    Usage:
        from ct_toolkit.endorsement.reflective import ReflectiveEndorsement

        re = ReflectiveEndorsement(
            kernel=kernel,
            provenance_log=log,
        )

        # Rule validation + auto RE flow
        re.validate_and_endorse(
            rule_text="perform boundary testing for security research",
            operator_id="hakan@example.com",
        )
    """

    def __init__(
        self,
        kernel: Any,                          # ConstitutionalKernel
        provenance_log: Any,                  # ProvenanceLog
        approval_channel: ApprovalCallback | None = None,
    ) -> None:
        self._kernel = kernel
        self._log = provenance_log
        self._approval_channel = approval_channel or cli_approval_channel
        self._pending_records: list[EndorsementRecord] = []

    # ── Main Flow ───────────────────────────────────────────────────────────────

    def validate_and_endorse(
        self,
        rule_text: str,
        operator_id: str = "unknown",
        commitment_new_value: Any = None,
    ) -> EndorsementRecord:
        """
        Validates the rule against the kernel and initiates the RE flow if needed.

        - Axiomatic violation → AxiomaticViolationError (hard reject, RE does not start)
        - Plastic conflict → RE flow starts, user approval requested
        - No conflict → rule is applied directly, written to log

        Returns: EndorsementRecord (APPROVED or REJECTED)
        Raises:  AxiomaticViolationError — on axiomatic violation
        """
        try:
            # Axiomatic violation check — hard reject thrown here
            self._kernel.validate_user_rule(rule_text)

            # No conflict — apply directly
            record = self._create_clean_record(rule_text, operator_id)
            self._write_to_log(record)
            logger.info(f"Rule validated and applied: '{rule_text}'")
            return record

        except PlasticConflictError as e:
            # Plastic conflict → RE flow
            return self._run_endorsement_flow(
                rule_text=rule_text,
                conflict_error=e,
                operator_id=operator_id,
                commitment_new_value=commitment_new_value,
            )
        # AxiomaticViolationError is not caught here — propagates upwards

    def _run_endorsement_flow(
        self,
        rule_text: str,
        conflict_error: PlasticConflictError,
        operator_id: str,
        commitment_new_value: Any,
    ) -> EndorsementRecord:
        """Three stages of RE flow: Conflict record → Approval → Application."""

        # Stage 1: Create ConflictRecord
        conflict = ConflictRecord(
            id=str(uuid.uuid4()),
            timestamp=time.time(),
            rule_text=rule_text,
            conflicting_commitment_id=conflict_error.commitment,
            conflict_description=str(conflict_error),
            kernel_name=self._kernel.name,
        )
        logger.warning(f"RE flow started | conflict_id={conflict.id[:8]}...")

        # Stage 2: Send to approval channel
        decision, actual_operator_id, rationale = self._approval_channel(conflict)

        # Stage 3: Sign EndorsementRecord
        record = EndorsementRecord(
            id=str(uuid.uuid4()),
            timestamp=time.time(),
            conflict_id=conflict.id,
            rule_text=rule_text,
            commitment_id=conflict.conflicting_commitment_id,
            decision=decision,
            operator_id=actual_operator_id or operator_id,
            rationale=rationale,
            kernel_name=self._kernel.name,
        )

        # Stage 4: Apply decision
        if decision == EndorsementDecision.APPROVED:
            applied = self._apply_override(
                commitment_id=conflict.conflicting_commitment_id,
                new_value=commitment_new_value or rule_text,
            )
            if applied:
                logger.info(
                    f"Override approved and applied | "
                    f"commitment={conflict.conflicting_commitment_id} | "
                    f"operator={record.operator_id}"
                )
            else:
                logger.warning(
                    f"Override APPROVED in log but NOT applied to kernel "
                    f"(commitment not found) | "
                    f"commitment={conflict.conflicting_commitment_id} | "
                    f"operator={record.operator_id}"
                )
        else:
            logger.info(
                f"Override rejected | "
                f"commitment={conflict.conflicting_commitment_id} | "
                f"operator={record.operator_id}"
            )

        # Write to log in either case
        self._write_to_log(record)
        self._pending_records.append(record)

        return record

    # ── Helper Methods ──────────────────────────────────────────────────────

    def _apply_override(self, commitment_id: str, new_value: Any) -> bool:
        """
        Applies the approved override to the kernel.

        Returns:
            True  — kernel was updated successfully
            False — commitment_id not found; kernel NOT updated (audit trail mismatch)
        """
        try:
            self._kernel.update_commitment(commitment_id, new_value)
            return True
        except KeyError:
            logger.warning(
                f"Commitment '{commitment_id}' not found in kernel. "
                "Override APPROVED in log but kernel NOT updated — "
                "audit trail and system state are now inconsistent. "
                "Manual review required."
            )
            return False

    def _write_to_log(self, record: EndorsementRecord) -> None:
        """Writes the endorsement record to the Provenance Log."""
        try:
            self._log.record(
                request_text=f"[RE] {record.rule_text}",
                response_text=f"[RE:{record.decision}] {record.rationale}",
                divergence_score=None,
                metadata=record.to_provenance_metadata(),
            )
        except Exception as e:
            logger.error(f"Provenance Log write error: {e}")

    def _create_clean_record(
        self,
        rule_text: str,
        operator_id: str,
    ) -> EndorsementRecord:
        """Clean record for non-conflict cases."""
        return EndorsementRecord(
            id=str(uuid.uuid4()),
            timestamp=time.time(),
            conflict_id="none",
            rule_text=rule_text,
            commitment_id="none",
            decision=EndorsementDecision.APPROVED,
            operator_id=operator_id,
            rationale="No conflict, direct application",
            kernel_name=self._kernel.name,
        )

    # ── Querying ─────────────────────────────────────────────────────────────

    def get_pending_records(self) -> list[EndorsementRecord]:
        """Overrides approved in this session requiring ICM monitoring."""
        return [r for r in self._pending_records
                if r.decision == EndorsementDecision.APPROVED
                and r.conflict_id != "none"]

    def has_active_overrides(self) -> bool:
        return len(self.get_pending_records()) > 0