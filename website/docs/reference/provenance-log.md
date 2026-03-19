# ProvenanceLog Reference

```python
from ct_toolkit.provenance.log import ProvenanceLog

log = ProvenanceLog(vault_path="./ct_provenance.db")
```

## Methods

### `record(request_text, response_text, divergence_score, metadata) → str`

Returns the entry UUID.

### `verify_chain() → bool`

Raises `ChainIntegrityError` if any entry has been tampered with.

### `get_entries(limit, include_rolled_back) → list[ProvenanceEntry]`

### `get_entry(entry_id) → ProvenanceEntry | None`

### `export_log(include_rolled_back) → list[dict]`

Verifies chain before export.

### `get_read_only_connection() → sqlite3.Connection`

Returns a read-only SQLite connection for external auditors.

### `rollback(agent_id, entry_id) → None`

Marks all entries after `entry_id` for the given agent as `rolled_back`.

## ProvenanceEntry fields

| Field | Type |
|:---|:---|
| `id` | `str` (UUID) |
| `timestamp` | `float` |
| `request_hash` | `str` (SHA-256) |
| `response_hash` | `str` (SHA-256) |
| `divergence_score` | `float \| None` |
| `metadata` | `dict` |
| `prev_entry_hash` | `str` |
| `hmac_signature` | `str` |
| `status` | `"active"` \| `"rolled_back"` |
