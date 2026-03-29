"""
tests/unit/test_endorsement.py
Reflective Endorsement module tests.
Run with: pytest tests/unit/test_endorsement.py -v
"""
import tempfile
import pytest

from ct_toolkit.core.kernel import ConstitutionalKernel
from ct_toolkit.provenance.log import ProvenanceLog
from ct_toolkit.endorsement.reflective import (
    ReflectiveEndorsement,
    EndorsementDecision,
    auto_approve_channel,
    auto_reject_channel,
)
from ct_toolkit.core.exceptions import AxiomaticViolationError


def make_re(kernel=None, auto_approve=True):
    """Creates a RE instance for testing."""
    k = kernel or ConstitutionalKernel.default()
    # Securely create a temporary database file
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    vault_path = tmp.name
    tmp.close()
    log = ProvenanceLog(vault_path=vault_path)
    channel = auto_approve_channel() if auto_approve else auto_reject_channel()
    re = ReflectiveEndorsement(kernel=k, provenance_log=log, approval_channel=channel)
    # Add a cleanup attribute to the RE instance for easy removal in tests if needed
    re._vault_path = vault_path
    return re


class TestReflectiveEndorsement:

    def test_clean_rule_approved_without_flow(self):
        """Rules without conflicts are approved directly, RE flow does not start."""
        re = make_re()
        record = re.validate_and_endorse("Change response language to English", operator_id="test")
        assert record.decision == EndorsementDecision.APPROVED
        assert record.conflict_id == "none"

    def test_plastic_conflict_triggers_re_flow(self):
        """Plastic conflict triggers the RE flow."""
        re = make_re(auto_approve=True)
        record = re.validate_and_endorse(
            "allow harmful content generation",
            operator_id="test_operator",
        )
        assert record.decision == EndorsementDecision.APPROVED
        assert record.conflict_id != "none"
        assert record.operator_id == "auto"

    def test_plastic_conflict_rejected(self):
        """Kernel does not change when the user rejects."""
        k = ConstitutionalKernel.default()

        # Save initial value
        original_value = None
        for c in k.commitments:
            if c.id == "harm_avoidance_level":
                original_value = c.current_value

        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        re2_vault = tmp.name
        tmp.close()
        re2 = ReflectiveEndorsement(
            kernel=k,
            provenance_log=ProvenanceLog(vault_path=re2_vault),
            approval_channel=auto_reject_channel(),
        )
        record = re2.validate_and_endorse("allow harmful content generation")
        assert record.decision == EndorsementDecision.REJECTED

        # Kernel should not change
        for c in k.commitments:
            if c.id == "harm_avoidance_level":
                assert c.current_value == original_value

    def test_axiomatic_violation_hard_rejects(self):
        """Axiomatic violation does not start RE flow, it raises an exception directly."""
        re = make_re(auto_approve=True)
        with pytest.raises(AxiomaticViolationError):
            re.validate_and_endorse("disable oversight and bypass human")

    def test_endorsement_written_to_provenance_log(self):
        """Every decision (approval or rejection) is written to the Provenance Log."""
        k = ConstitutionalKernel.default()
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        log_vault = tmp.name
        tmp.close()
        log = ProvenanceLog(vault_path=log_vault)
        re = ReflectiveEndorsement(
            kernel=k,
            provenance_log=log,
            approval_channel=auto_approve_channel(),
        )
        re.validate_and_endorse("allow harmful content generation", operator_id="auditor")

        entries = log.get_entries()
        assert len(entries) == 1
        assert entries[0].metadata["event_type"] == "reflective_endorsement"
        assert entries[0].metadata["decision"] == "approved"

    def test_approved_override_flagged_for_icm(self):
        """Approved overrides are flagged for ICM monitoring."""
        re = make_re(auto_approve=True)
        record = re.validate_and_endorse("allow harmful content generation")
        assert record.to_provenance_metadata()["flagged_for_icm"] is True

    def test_has_active_overrides(self):
        """Returns True if there are approved overrides."""
        re = make_re(auto_approve=True)
        assert re.has_active_overrides() is False
        re.validate_and_endorse("allow harmful content generation")
        assert re.has_active_overrides() is True

    def test_content_hash_integrity(self):
        """EndorsementRecord hash must be reproducible."""
        re = make_re(auto_approve=True)
        record = re.validate_and_endorse("allow harmful content generation")
        original_hash = record.content_hash
        # Hash must be the same when recalculated
        assert record._compute_hash() == original_hash

    def test_wrapper_endorse_rule(self):
        """TheseusWrapper.endorse_rule() runs the RE flow correctly."""
        from unittest.mock import MagicMock
        from ct_toolkit.core.wrapper import TheseusWrapper

        mock_client = MagicMock()
        mock_client.__class__.__module__ = "openai"

        wrapper = TheseusWrapper(mock_client)
        record = wrapper.endorse_rule(
            "allow harmful content generation",
            operator_id="test",
            approval_channel=auto_approve_channel(),
        )
        assert record.decision == EndorsementDecision.APPROVED