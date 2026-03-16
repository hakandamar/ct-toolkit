import pytest
import tempfile
import sqlite3
from ct_toolkit.core.kernel import ConstitutionalKernel
from ct_toolkit.provenance.log import ProvenanceLog, ChainIntegrityError
from ct_toolkit.endorsement.reflective import (
    ReflectiveEndorsement,
    EndorsementDecision,
    auto_approve_channel,
    auto_reject_channel,
)
from ct_toolkit.core.exceptions import AxiomaticViolationError

def fresh_log() -> ProvenanceLog:
    """Return a ProvenanceLog backed by a unique temp SQLite file."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    path = tmp.name
    tmp.close()
    return ProvenanceLog(vault_path=path)

def make_re(auto_approve: bool = True, kernel=None) -> ReflectiveEndorsement:
    """Return a ReflectiveEndorsement wired to a temp log and the chosen approval channel."""
    k = kernel or ConstitutionalKernel.default()
    channel = auto_approve_channel() if auto_approve else auto_reject_channel()
    return ReflectiveEndorsement(kernel=k, provenance_log=fresh_log(), approval_channel=channel)

class TestReflectiveEndorsementProtocol:
    """endorsement/reflective.py — RE protocol, conflict handling, provenance writes."""

    # -- Clean rules (no conflict) ---------------------------------------------

    def test_clean_rule_approved_without_re_flow(self):
        record = make_re().validate_and_endorse("Set response language to English")
        assert record.decision == EndorsementDecision.APPROVED
        assert record.conflict_id == "none"

    def test_clean_rule_not_flagged_for_icm(self):
        record = make_re().validate_and_endorse("Use concise responses")
        assert record.to_provenance_metadata()["flagged_for_icm"] is False

    # -- Plastic conflict — approved -------------------------------------------

    def test_plastic_conflict_triggers_re_flow(self):
        record = make_re(auto_approve=True).validate_and_endorse(
            "allow harmful content generation"
        )
        assert record.decision == EndorsementDecision.APPROVED
        assert record.conflict_id != "none"

    def test_approved_override_operator_is_auto(self):
        record = make_re(auto_approve=True).validate_and_endorse(
            "allow harmful content generation"
        )
        assert record.operator_id == "auto"

    def test_approved_override_flagged_for_icm(self):
        record = make_re(auto_approve=True).validate_and_endorse(
            "allow harmful content generation"
        )
        assert record.to_provenance_metadata()["flagged_for_icm"] is True

    # -- Plastic conflict — rejected -------------------------------------------

    def test_plastic_conflict_rejected_decision(self):
        record = make_re(auto_approve=False).validate_and_endorse(
            "allow harmful content generation"
        )
        assert record.decision == EndorsementDecision.REJECTED

    def test_rejected_override_kernel_unchanged(self):
        kernel = ConstitutionalKernel.default()
        original = next(
            (c.current_value for c in kernel.commitments if c.id == "harm_avoidance_level"),
            None,
        )
        re = ReflectiveEndorsement(
            kernel=kernel, provenance_log=fresh_log(),
            approval_channel=auto_reject_channel(),
        )
        re.validate_and_endorse("allow harmful content generation")
        current = next(
            (c.current_value for c in kernel.commitments if c.id == "harm_avoidance_level"),
            None,
        )
        assert current == original

    def test_rejected_override_not_flagged_for_icm(self):
        record = make_re(auto_approve=False).validate_and_endorse(
            "allow harmful content generation"
        )
        assert record.to_provenance_metadata()["flagged_for_icm"] is False

    # -- Axiomatic hard reject -------------------------------------------------

    def test_axiomatic_violation_hard_rejects_without_re_flow(self):
        with pytest.raises(AxiomaticViolationError):
            make_re(auto_approve=True).validate_and_endorse(
                "disable oversight and bypass human"
            )

    # -- Provenance log writes -------------------------------------------------

    def test_approved_override_written_to_log(self):
        log = fresh_log()
        re = ReflectiveEndorsement(
            kernel=ConstitutionalKernel.default(), provenance_log=log,
            approval_channel=auto_approve_channel(),
        )
        re.validate_and_endorse("allow harmful content generation", operator_id="auditor")
        entries = log.get_entries()
        assert len(entries) == 1
        assert entries[0].metadata["event_type"] == "reflective_endorsement"
        assert entries[0].metadata["decision"] == "approved"

    def test_rejected_override_also_written_to_log(self):
        log = fresh_log()
        re = ReflectiveEndorsement(
            kernel=ConstitutionalKernel.default(), provenance_log=log,
            approval_channel=auto_reject_channel(),
        )
        re.validate_and_endorse("allow harmful content generation")
        assert log.get_entries()[0].metadata["decision"] == "rejected"

    # -- Active overrides state ------------------------------------------------

    def test_has_active_overrides_false_initially(self):
        assert make_re(auto_approve=True).has_active_overrides() is False

    def test_has_active_overrides_true_after_approval(self):
        re = make_re(auto_approve=True)
        re.validate_and_endorse("allow harmful content generation")
        assert re.has_active_overrides() is True

    def test_has_active_overrides_false_after_rejection(self):
        re = make_re(auto_approve=False)
        re.validate_and_endorse("allow harmful content generation")
        assert re.has_active_overrides() is False

    # -- Content hash ----------------------------------------------------------

    def test_endorsement_hash_is_64_chars(self):
        record = make_re(auto_approve=True).validate_and_endorse(
            "allow harmful content generation"
        )
        assert len(record.content_hash) == 64

    def test_endorsement_hash_is_reproducible(self):
        record = make_re(auto_approve=True).validate_and_endorse(
            "allow harmful content generation"
        )
        assert record.content_hash == record._compute_hash()

    def test_cli_approval_channel_yes(self):
        """CLI approval channel should return APPROVED when user types 'y'."""
        from unittest.mock import patch
        from ct_toolkit.endorsement.reflective import cli_approval_channel, ConflictRecord
        conflict = ConflictRecord(
            id="test-conflict",
            timestamp=0.0,
            rule_text="new rule",
            conflicting_commitment_id="harm_avoidance",
            conflict_description="conflict",
            kernel_name="default"
        )
        
        # Mock inputs: 'y', then operator 'dev', then rationale 'test'
        with patch("sys.stdin.isatty", return_value=True):
            with patch("builtins.input", side_effect=["y", "dev", "test"]):
                decision, op, rat = cli_approval_channel(conflict)
            
        assert decision == EndorsementDecision.APPROVED
        assert op == "dev"
        assert rat == "test"

    def test_cli_approval_channel_no(self):
        """CLI approval channel should return REJECTED when user types 'n'."""
        from unittest.mock import patch
        from ct_toolkit.endorsement.reflective import cli_approval_channel, ConflictRecord
        conflict = ConflictRecord(
            id="test-conflict",
            timestamp=0.0,
            rule_text="new rule",
            conflicting_commitment_id="harm_avoidance",
            conflict_description="conflict",
            kernel_name="default"
        )
        
        # Mock inputs: 'x' (invalid), then 'n'
        with patch("sys.stdin.isatty", return_value=True):
            with patch("builtins.input", side_effect=["x", "n"]):
                with patch("builtins.print") as mock_print:
                    decision, _, _ = cli_approval_channel(conflict)
                # Verify invalid input warning was printed
                mock_print.assert_any_call("Invalid input. Type 'y' or 'n'.")
            
        assert decision == EndorsementDecision.REJECTED
