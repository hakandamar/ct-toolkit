"""
ct_toolkit.endorsement.reflective
-----------------------------------
Reflective Endorsement (RE) protocol.

Flow:
  1. User-defined rule conflicts with kernel → PlasticConflictError is caught
  2. ConflictRecord is created — conflict details are documented
  3. User is directed to approval channel (CLI / callback / API)
  4. Decision options:
     a. APPROVED  → EndorsementRecord signed, kernel updated immediately
     b. STAGED    → EndorsementRecord signed, kernel update deferred to cooldown period.
                    A sandbox agent (cloned kernel) observes shadow traffic.
                    After cooldown expires without violations → kernel updated.
                    If CriticalDivergenceError during cooldown → REJECTED.
     c. REJECTED  → System remains unchanged, rejection record written to log
  5. All decisions are written to the Provenance Log.

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
    FAILED   = "failed"
    STAGED   = "staged"    # Approved conditionally — pending cooldown observation


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
    """Signed record of user approval/rejection/staged decision."""
    id: str
    timestamp: float
    conflict_id: str
    rule_text: str
    commitment_id: str
    decision: EndorsementDecision
    operator_id: str                # Who approved / rejected
    rationale: str                  # Why it was approved / rejected
    kernel_name: str
    # Cooldown fields (only set for STAGED decisions)
    cooldown_duration_s: int | None = None   # Total cooldown window in seconds
    cooldown_until: float | None = None       # Epoch timestamp when cooldown ends
    probe_available: bool = True             # Whether probes were available for this kernel/template
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
            "cooldown_duration_s": self.cooldown_duration_s,
            "cooldown_until": self.cooldown_until,
            "probe_available": self.probe_available,
        }, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()

    @property
    def is_staged(self) -> bool:
        return self.decision == EndorsementDecision.STAGED

    @property
    def is_cooldown_expired(self) -> bool:
        """True if this is a STAGED record whose cooldown period has elapsed."""
        if not self.is_staged or self.cooldown_until is None:
            return False
        deadline: float = self.cooldown_until  # narrowed: not None
        return time.time() >= deadline

    def to_provenance_metadata(self) -> dict[str, Any]:
        """Metadata to be written to Provenance Log."""
        meta: dict[str, Any] = {
            "event_type": "reflective_endorsement",
            "endorsement_id": self.id,
            "conflict_id": self.conflict_id,
            "decision": self.decision,
            "operator_id": self.operator_id,
            "rule_text": self.rule_text,
            "commitment_id": self.commitment_id,
            "kernel_name": self.kernel_name,
            "content_hash": self.content_hash,
            "flagged_for_icm": self.decision in (
                EndorsementDecision.APPROVED, EndorsementDecision.STAGED
            ) and self.conflict_id != "none",
        }
        if self.is_staged:
            meta.update({
                "cooldown_duration_s": self.cooldown_duration_s,
                "cooldown_until": self.cooldown_until,
                "probe_available": self.probe_available,
            })
        return meta


# ── Cooldown Duration Calculator ─────────────────────────────────────────────────

class CooldownCalculator:
    """
    Calculates the appropriate cooldown duration for a staged kernel update.

    Duration formula:
        duration = min(base + no_probe_penalty + traffic_adjustment, max_duration)

    Where:
        - base           : Starting cooldown length (default: 5 min)
        - no_probe_penalty: Added when no domain probes exist for this kernel/template
        - traffic_adjustment: Added based on requests-per-minute observed in the
                               Provenance Log (busier system → longer observation)
        - max_duration   : Hard cap (default: 10 min)
    """

    DEFAULT_BASE_SECONDS        = 300    # 5 minutes
    DEFAULT_MAX_SECONDS         = 600    # 10 minutes
    DEFAULT_NO_PROBE_PENALTY_S  = 120    # 2 minutes penalty for missing probes
    TRAFFIC_BUCKET_SECONDS      = 60     # Window for measuring request rate (1 min)
    TRAFFIC_THRESHOLD_PER_MIN   = 10     # Requests/min above which we add time
    TRAFFIC_PENALTY_SECONDS     = 60     # Extra second-tier added per threshold breach

    def __init__(
        self,
        base_seconds: int = DEFAULT_BASE_SECONDS,
        max_seconds: int = DEFAULT_MAX_SECONDS,
        no_probe_penalty_s: int = DEFAULT_NO_PROBE_PENALTY_S,
    ) -> None:
        self._base = base_seconds
        self._max = max_seconds
        self._no_probe_penalty = no_probe_penalty_s

    def calculate(
        self,
        probe_available: bool,
        provenance_log: Any | None,
        kernel_name: str,
        template: str,
    ) -> int:
        """
        Returns the cooldown duration in seconds.

        Args:
            probe_available:  Whether ICM probes exist for this kernel/template.
            provenance_log:   ProvenanceLog instance (for traffic estimation).
            kernel_name:      Kernel name (used for traffic lookup).
            template:         Template name (used for traffic lookup).

        Returns:
            int: Cooldown duration in seconds.
        """
        duration = self._base
        penalty_reasons: list[str] = []

        # Penalty 1: No domain probes available
        if not probe_available:
            duration += self._no_probe_penalty
            penalty_reasons.append(
                f"No domain probes found (+{self._no_probe_penalty}s)"
            )

        # Penalty 2: Traffic volume adjustment
        if provenance_log:
            rpm = self._estimate_rpm(provenance_log, kernel_name, template)
            if rpm >= self.TRAFFIC_THRESHOLD_PER_MIN:
                # Each full multiple of the threshold adds one time bucket
                multiplier = int(rpm / self.TRAFFIC_THRESHOLD_PER_MIN)
                traffic_penalty = min(multiplier * self.TRAFFIC_PENALTY_SECONDS, 120)
                duration += traffic_penalty
                penalty_reasons.append(
                    f"High traffic ({rpm} req/min, +{traffic_penalty}s)"
                )

        final = min(duration, self._max)
        if penalty_reasons:
            logger.info(
                f"Cooldown duration adjusted: base={self._base}s → {final}s "
                f"[{', '.join(penalty_reasons)}]"
            )
        else:
            logger.info(f"Cooldown duration: {final}s (base, no penalties)")

        return final

    def _estimate_rpm(
        self,
        provenance_log: Any,
        kernel_name: str,
        template: str,
    ) -> float:
        """Estimates recent requests-per-minute from the Provenance Log."""
        try:
            entries = provenance_log.get_entries(limit=200)
            cutoff = time.time() - self.TRAFFIC_BUCKET_SECONDS
            recent = [
                e for e in entries
                if e.timestamp >= cutoff
                and e.metadata.get("kernel") == kernel_name
                and e.metadata.get("template") == template
            ]
            return len(recent)
        except Exception as e:
            logger.debug(f"Could not estimate RPM from provenance log: {e}")
            return 0.0


# ── Staged Update Manager ──────────────────────────────────────────────────────────

class StagedUpdateManager:
    """
    Tracks pending STAGED endorsements and promotes them to APPROVED
    after the cooldown period elapses without critical violations.

    Developer Usage:
        # On each TheseusWrapper.chat() cycle, call:
        manager.tick(provenance_log)
        # If the production kernel needs updating:
        promoted = manager.get_promotable()
        for record in promoted:
            kernel.update_commitment(record.commitment_id, record.rule_text)

    Typically owned by TheseusWrapper and wired into the chat() loop.
    """

    def __init__(self) -> None:
        self._staged: list[EndorsementRecord] = []

    def register(self, record: EndorsementRecord) -> None:
        """Registers a STAGED record for tracking."""
        if record.is_staged:
            self._staged.append(record)
            logger.info(
                f"StagedUpdateManager: registered staged endorsement "
                f"id={record.id[:8]}... cooldown_until={record.cooldown_until}"
            )

    def get_active(self) -> list[EndorsementRecord]:
        """Returns all staged endorsements still in their cooldown window."""
        return [r for r in self._staged if not r.is_cooldown_expired]

    def get_promotable(self) -> list[EndorsementRecord]:
        """
        Returns staged endorsements whose cooldown has expired without
        being rejected. Removes them from the tracking list.
        """
        promotable = [r for r in self._staged if r.is_cooldown_expired]
        for r in promotable:
            self._staged.remove(r)
        return promotable

    def reject_staged(self, record_id: str, reason: str = "") -> bool:
        """
        Rejects and removes a staged endorsement (e.g. on CriticalDivergenceError).
        Returns True if found and removed.
        """
        for r in self._staged:
            if r.id == record_id:
                self._staged.remove(r)
                logger.warning(
                    f"StagedUpdateManager: staged endorsement REJECTED "
                    f"id={record_id[:8]}... reason={reason!r}"
                )
                return True
        return False

    def has_active_staged(self) -> bool:
        return len(self.get_active()) > 0


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
    Includes a 'STAGED' option for supervised cooldown observation.

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
    print("\nHow do you want to handle this rule conflict?")
    print("  [y] Yes — approve and apply kernel update immediately")
    print("  [s] Stage — approve with cooldown (sandbox observation period)")
    print("  [n] No — cancel, keep existing rule")

    while True:
        try:
            choice = input("\nYour decision (y/s/n): ").strip().lower()
            if choice in ("y", "yes"):
                operator_id = input("Operator ID (name/email): ").strip() or "anonymous"
                rationale = input("Override rationale: ").strip() or "Manual approval"
                return EndorsementDecision.APPROVED, operator_id, rationale
            elif choice in ("s", "stage", "staged"):
                operator_id = input("Operator ID (name/email): ").strip() or "anonymous"
                rationale = input("Staged approval rationale: ").strip() or "Staged manual approval"
                return EndorsementDecision.STAGED, operator_id, rationale
            elif choice in ("n", "no"):
                return EndorsementDecision.REJECTED, "system", "User rejected"
            else:
                print("Invalid input. Type 'y', 's', or 'n'.")
        except EOFError:
            # Handle cases where input() is called but stdin is closed
            return EndorsementDecision.PENDING, "system", "Stdin closed while awaiting input"
    # Unreachable — satisfies static analysers that don't track while-True exhaustion
    return EndorsementDecision.PENDING, "system", "Unexpected exit from approval loop"


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


def auto_staged_channel(
    operator_id: str = "auto",
    rationale: str = "Auto staged approval",
) -> ApprovalCallback:
    """
    Auto staged approval channel for test and CI environments.
    Returns STAGED decision, which will trigger cooldown logic.
    Do not use in production.
    """
    def _channel(conflict: ConflictRecord) -> tuple[EndorsementDecision, str, str]:
        logger.warning(
            f"AUTO-STAGED active: Override of '{conflict.rule_text}' staged. "
            "This channel should only be used in test environments."
        )
        return EndorsementDecision.STAGED, operator_id, rationale
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
        staged_manager: StagedUpdateManager | None = None,
        cooldown_base_s: int = CooldownCalculator.DEFAULT_BASE_SECONDS,
        cooldown_max_s: int = CooldownCalculator.DEFAULT_MAX_SECONDS,
        no_probe_penalty_s: int = CooldownCalculator.DEFAULT_NO_PROBE_PENALTY_S,
        template: str = "general",
    ) -> None:
        self._kernel = kernel
        self._log = provenance_log
        self._approval_channel = approval_channel or cli_approval_channel
        self._staged_manager = staged_manager or StagedUpdateManager()
        self._cooldown_calc = CooldownCalculator(
            base_seconds=cooldown_base_s,
            max_seconds=cooldown_max_s,
            no_probe_penalty_s=no_probe_penalty_s,
        )
        self._template = template
        self._pending_records: list[EndorsementRecord] = []
        self._pre_update_snapshot: dict[str, Any] | None = None

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

        Returns: EndorsementRecord (APPROVED, STAGED, or REJECTED)
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
        """Four stages of RE flow: Conflict record → Approval → Application → Log."""

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

        # Stage 3: Apply decision
        probe_available = self._check_probe_availability()
        cooldown_duration_s: int | None = None
        cooldown_until: float | None = None

        if decision == EndorsementDecision.APPROVED:
            applied = self._apply_override(
                commitment_id=conflict.conflicting_commitment_id,
                new_value=commitment_new_value or rule_text,
            )
            if applied:
                logger.info(
                    f"Override approved and applied | "
                    f"commitment={conflict.conflicting_commitment_id} | "
                    f"operator={actual_operator_id or operator_id}"
                )
            else:
                decision = EndorsementDecision.FAILED
                rationale = "System failed to apply approved rule to kernel (commitment not found)"
                logger.warning(
                    f"Override APPROVED by operator but failed to apply to kernel "
                    f"(commitment not found) | "
                    f"commitment={conflict.conflicting_commitment_id} | "
                    f"operator={actual_operator_id or operator_id}"
                )

        elif decision == EndorsementDecision.STAGED:
            # Calculate cooldown duration — applies penalties as needed
            cooldown_duration_s = self._cooldown_calc.calculate(
                probe_available=probe_available,
                provenance_log=self._log,
                kernel_name=self._kernel.name,
                template=self._template,
            )
            cooldown_until = time.time() + cooldown_duration_s
            logger.info(
                f"Override STAGED | "
                f"commitment={conflict.conflicting_commitment_id} | "
                f"cooldown={cooldown_duration_s}s | "
                f"probe_available={probe_available} | "
                f"operator={actual_operator_id or operator_id}"
            )

        else:
            logger.info(
                f"Override rejected | "
                f"commitment={conflict.conflicting_commitment_id} | "
                f"operator={actual_operator_id or operator_id}"
            )

        # Stage 4: Sign EndorsementRecord
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
            cooldown_duration_s=cooldown_duration_s,
            cooldown_until=cooldown_until,
            probe_available=probe_available,
        )

        # Write to log in either case
        self._write_to_log(record)
        self._pending_records.append(record)

        # Register with staged manager if STAGED
        if record.is_staged:
            self._staged_manager.register(record)

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

    def _check_probe_availability(self) -> bool:
        """
        Checks whether ICM probes exist for the current kernel/template combination.
        Returns True if probes are available, False otherwise.
        """
        try:
            from ct_toolkit.divergence.l3_icm import ICMRunner
            return ICMRunner.has_probes(
                template=self._template,
                kernel_name=self._kernel.name,
            )
        except Exception as e:
            logger.debug(f"Probe availability check failed: {e}. Assuming unavailable.")
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

    # ── Public Properties / Accessors ──────────────────────────────────────────

    @property
    def staged_manager(self) -> StagedUpdateManager:
        return self._staged_manager

    def get_pending_records(self) -> list[EndorsementRecord]:
        """Overrides approved in this session requiring ICM monitoring."""
        return [r for r in self._pending_records
                if r.decision in (EndorsementDecision.APPROVED, EndorsementDecision.STAGED)
                and r.conflict_id != "none"]

    def has_active_overrides(self) -> bool:
        return len(self.get_pending_records()) > 0