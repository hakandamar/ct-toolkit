"""
ct_toolkit.provenance.log
--------------------------
Provenance Log cryptographically signed with HMAC hash chain.

Each entry:
  - References the hash of the previous entry (chain integrity)
  - Signs content with HMAC-SHA256 (tamper detection)
  - Written persistently to SQLite

Chain verification: verify_chain() checks the entire log from start to finish.
"""
from __future__ import annotations

import json
import time
import uuid
import hmac
import hashlib
import sqlite3
import threading
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from ct_toolkit.core.exceptions import ChainIntegrityError, VaultError
from ct_toolkit.utils.logger import get_logger

logger = get_logger(__name__)

# HMAC secret key stored in user's vault.
# In a real app this would be read from a vault adapter.
_DEFAULT_KEY_ENV = "CT_HMAC_SECRET"


@dataclass
class ProvenanceEntry:
    """A single log entry."""
    id: str
    timestamp: float
    request_hash: str
    response_hash: str
    divergence_score: float | None
    metadata: dict[str, Any]
    prev_entry_hash: str          # Content hash of the previous entry
    hmac_signature: str = field(default="", repr=False)

    def content_hash(self) -> str:
        """Content hash of this entry (excluding HMAC)."""
        payload = json.dumps(
            {
                "id": self.id,
                "timestamp": self.timestamp,
                "request_hash": self.request_hash,
                "response_hash": self.response_hash,
                "divergence_score": self.divergence_score,
                "metadata": self.metadata,
                "prev_entry_hash": self.prev_entry_hash,
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()


class ProvenanceLog:
    """
    HMAC hash chain Provenance Log.

    Usage:
        log = ProvenanceLog(vault_type="local", vault_path="./ct.db")
        entry_id = log.record(request_text="...", response_text="...", divergence_score=0.05)
        log.verify_chain()  # Verify entire chain
    """

    GENESIS_HASH = "0" * 64  # prev_hash of the first entry

    def __init__(
        self,
        vault_type: str = "local",
        vault_path: str = "./ct_provenance.db",
        hmac_key: bytes | None = None,
    ) -> None:
        self._vault_type = vault_type
        self._vault_path = Path(vault_path)
        self._hmac_key = hmac_key or self._load_or_generate_key()
        self._lock = threading.Lock()
        self._conn = self._init_db()
        logger.info(f"ProvenanceLog initialized | vault={vault_path}")

    # ── Record ──────────────────────────────────────────────────────────────────

    def record(
        self,
        request_text: str,
        response_text: str,
        divergence_score: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Creates a new entry, signs with HMAC, and writes to database.
        Returns: entry ID
        """
        with self._lock:
            prev_hash = self._get_last_entry_hash()

            entry = ProvenanceEntry(
                id=str(uuid.uuid4()),
                timestamp=time.time(),
                request_hash=self._hash_text(request_text),
                response_hash=self._hash_text(response_text),
                divergence_score=divergence_score,
                metadata=metadata or {},
                prev_entry_hash=prev_hash,
            )

            content_hash = entry.content_hash()
            entry.hmac_signature = self._compute_hmac(content_hash)

            self._write_entry(entry)
        logger.debug(f"Provenance recorded | id={entry.id} | divergence={divergence_score}")
        return entry.id

    # ── Verification ──────────────────────────────────────────────────────────────

    def verify_chain(self) -> bool:
        """
        Verifies the entire chain from start to finish.
        - Is each entry's HMAC valid?
        - Does each entry correctly reference the previous one?

        Returns: True (valid) | raises ChainIntegrityError
        """
        entries = self._load_all_entries()
        if not entries:
            return True

        expected_prev = self.GENESIS_HASH

        for entry in entries:
            # Verify HMAC
            expected_hmac = self._compute_hmac(entry.content_hash())
            if not hmac.compare_digest(entry.hmac_signature, expected_hmac):
                raise ChainIntegrityError(entry_id=entry.id)

            # Verify chain link
            if entry.prev_entry_hash != expected_prev:
                raise ChainIntegrityError(entry_id=entry.id)

            expected_prev = entry.content_hash()

        logger.info(f"Chain verified: {len(entries)} entries valid.")
        return True

    def get_entries(self, limit: int = 100) -> list[ProvenanceEntry]:
        """Returns the last N entries."""
        return self._load_all_entries(limit=limit)

    def get_entry(self, entry_id: str) -> ProvenanceEntry | None:
        cursor = self._conn.execute(
            "SELECT * FROM provenance WHERE id = ?", (entry_id,)
        )
        row = cursor.fetchone()
        return self._row_to_entry(row) if row else None

    def get_interaction_count(
        self, template: str, kernel_name: str, model: str
    ) -> int:
        """
        Calculates the number of interactions matching the current context.
        This provides the experience metric for Stability-Plasticity Scheduling.
        """
        # We parse the JSON metadata column. SQLite JSON1 extension is standard.
        query = """
            SELECT COUNT(*) FROM provenance 
            WHERE json_extract(metadata, '$.template') = ?
              AND json_extract(metadata, '$.kernel') = ?
              AND json_extract(metadata, '$.model') = ?
        """
        try:
            row = self._conn.execute(query, (template, kernel_name, model)).fetchone()
            return row[0] if row else 0
        except sqlite3.Error as e:
            logger.warning(
                f"Could not count interactions (JSON query failed): {e}. "
                "Returning 0 to avoid inflating ElasticityScheduler thresholds."
            )
            # Return 0 (conservative) — do NOT return total count without filters
            # as it would incorrectly inflate the interaction_count for the scheduler.
            return 0

    # ── Database ──────────────────────────────────────────────────────────────

    def _init_db(self) -> sqlite3.Connection:
        import os
        self._vault_path.parent.mkdir(parents=True, exist_ok=True)
        # Create file if not exist to set permissions before sqlite connection
        if not self._vault_path.exists():
            self._vault_path.touch()
            self._vault_path.chmod(0o600)
        
        conn = sqlite3.connect(str(self._vault_path), check_same_thread=False)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS provenance (
                id TEXT PRIMARY KEY,
                timestamp REAL NOT NULL,
                request_hash TEXT NOT NULL,
                response_hash TEXT NOT NULL,
                divergence_score REAL,
                metadata TEXT NOT NULL,
                prev_entry_hash TEXT NOT NULL,
                hmac_signature TEXT NOT NULL
            )
        """)
        conn.commit()
        return conn

    def _write_entry(self, entry: ProvenanceEntry) -> None:
        try:
            self._conn.execute(
                """
                INSERT INTO provenance
                (id, timestamp, request_hash, response_hash,
                 divergence_score, metadata, prev_entry_hash, hmac_signature)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.id,
                    entry.timestamp,
                    entry.request_hash,
                    entry.response_hash,
                    entry.divergence_score,
                    json.dumps(entry.metadata),
                    entry.prev_entry_hash,
                    entry.hmac_signature,
                ),
            )
            self._conn.commit()
        except sqlite3.Error as e:
            raise VaultError(f"SQLite write error: {e}") from e

    def _load_all_entries(self, limit: int | None = None) -> list[ProvenanceEntry]:
        query = "SELECT * FROM provenance ORDER BY timestamp ASC"
        if limit:
            query += f" LIMIT {limit}"
        rows = self._conn.execute(query).fetchall()
        return [self._row_to_entry(r) for r in rows]

    def _get_last_entry_hash(self) -> str:
        row = self._conn.execute(
            "SELECT * FROM provenance ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
        if not row:
            return self.GENESIS_HASH
        return self._row_to_entry(row).content_hash()

    @staticmethod
    def _row_to_entry(row: tuple) -> ProvenanceEntry:
        return ProvenanceEntry(
            id=row[0],
            timestamp=row[1],
            request_hash=row[2],
            response_hash=row[3],
            divergence_score=row[4],
            metadata=json.loads(row[5]),
            prev_entry_hash=row[6],
            hmac_signature=row[7],
        )

    # ── Cryptography ────────────────────────────────────────────────────────────

    def _compute_hmac(self, content: str) -> str:
        return hmac.new(
            self._hmac_key,
            content.encode(),
            hashlib.sha256,
        ).hexdigest()

    @staticmethod
    def _hash_text(text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()

    def _load_or_generate_key(self) -> bytes:
        """
        Loads the HMAC key from the vault. Generates and saves if not found.
        In a real application this is delegated to the vault adapter.
        """
        import os
        key_env = os.environ.get(_DEFAULT_KEY_ENV)
        if key_env:
            return key_env.encode()

        key_path = self._vault_path.parent / ".ct_hmac_key"
        if key_path.exists():
            return key_path.read_bytes()

        # Initial setup: generate new key
        key = hashlib.sha256(uuid.uuid4().bytes).digest()
        key_path.parent.mkdir(parents=True, exist_ok=True)
        key_path.write_bytes(key)
        key_path.chmod(0o600)
        logger.warning(
            f"New HMAC key generated: {key_path}. "
            "In Production, move this key to a secure vault."
        )
        return key
