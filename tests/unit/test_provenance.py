import sqlite3
import tempfile
import pytest
from ct_toolkit.provenance.log import ProvenanceLog
from ct_toolkit.core.exceptions import ChainIntegrityError

class TestProvenanceLog:
    """provenance/log.py — HMAC hash chain, tamper detection, metadata storage."""

    def setup_method(self):
        self._tmp_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp = self._tmp_file.name
        self._tmp_file.close()
        self.log = ProvenanceLog(vault_path=self.tmp)

    def teardown_method(self):
        import os
        if os.path.exists(self.tmp):
            os.remove(self.tmp)

    # -- Recording -------------------------------------------------------------

    def test_record_returns_string_id(self):
        entry_id = self.log.record("question", "answer", divergence_score=0.05)
        assert isinstance(entry_id, str) and len(entry_id) > 0

    def test_retrieve_recorded_entry(self):
        entry_id = self.log.record("question", "answer", divergence_score=0.07)
        entry = self.log.get_entry(entry_id)
        assert entry is not None and entry.divergence_score == pytest.approx(0.07)

    def test_metadata_is_persisted(self):
        entry_id = self.log.record("q", "a", metadata={"tier": "ok", "model": "gpt-4o"})
        entry = self.log.get_entry(entry_id)
        assert entry.metadata["tier"] == "ok"
        assert entry.metadata["model"] == "gpt-4o"

    def test_get_entries_returns_all(self):
        self.log.record("q1", "a1")
        self.log.record("q2", "a2")
        assert len(self.log.get_entries(limit=10)) == 2

    # -- Hash chain ------------------------------------------------------------

    def test_first_entry_has_genesis_prev_hash(self):
        entry_id = self.log.record("first question", "first answer")
        assert self.log.get_entry(entry_id).prev_entry_hash == "0" * 64

    def test_verify_chain_passes_for_valid_log(self):
        for i in range(3):
            self.log.record(f"q{i}", f"a{i}", divergence_score=i * 0.01)
        assert self.log.verify_chain() is True

    def test_verify_chain_on_empty_log(self):
        assert self.log.verify_chain() is True

    # -- Tamper detection ------------------------------------------------------

    def test_tampered_hmac_raises_chain_integrity_error(self):
        self.log.record("question", "answer")
        conn = sqlite3.connect(self.tmp)
        conn.execute("UPDATE provenance SET hmac_signature = 'tampered'")
        conn.commit()
        conn.close()
        with pytest.raises(ChainIntegrityError):
            self.log.verify_chain()

    def test_tampered_response_hash_raises_chain_integrity_error(self):
        self.log.record("question", "answer")
        conn = sqlite3.connect(self.tmp)
        conn.execute("UPDATE provenance SET response_hash = 'fake'")
        conn.commit()
        conn.close()
        with pytest.raises(ChainIntegrityError):
            self.log.verify_chain()
