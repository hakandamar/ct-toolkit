# API Reference

Detailed API documentation is generated from the source code.

## Core Modules

### `TheseusWrapper`
The main entry point for applying guardrails to any LLM interaction.

### `ConstitutionalKernel`
The data structure for managing agent rules and identities.

### `DivergenceEngine`
The engine responsible for multi-tiered drift analysis.

### `IntegrityMonitor`
A security component that prevents runtime tampering of critical configuration files. It calculates and verifies SHA-256 hashes of registered files, like Kernels or Identity Templates, to ensure they have not been altered.

**Key Methods:**

*   `register_file(file_path)`: Registers a file and stores its initial hash.
*   `verify_integrity()`: Checks all registered files against their initial hashes and raises an error if a mismatch is found.

### `ProvenanceLog`
The immutable log for tracking agent identity across time. It creates a verifiable, HMAC-signed hash chain of all interactions, stored in a local SQLite database. This provides a crucial audit trail for ensuring an agent's behavior has not deviated from its core principles.

**Key Methods:**

*   `record(request_text, response_text, ...)`: Records a new agent interaction and adds it to the hash chain.
*   `verify_chain()`: Verifies the integrity of the entire active log, raising an error if any tampering is detected.
*   `get_entries(include_rolled_back=False)`: Retrieves a list of log entries. By default, it only returns active entries.
*   `get_entry(entry_id)`: Retrieves a single log entry by its unique ID.
*   `export_log(include_rolled_back=False)`: Exports the entire log as a list of dictionaries, suitable for external analysis.
*   `get_read_only_connection()`: Returns a read-only SQLite connection, allowing for safe, external auditing of the raw database.
*   `rollback(agent_id, entry_id)`: Performs a safe, agent-specific rollback. Instead of deleting records, it marks all of an agent's entries after a specific point as `rolled_back`, preserving the log's integrity while reverting the agent's state.

---

*Note: Full automated API reference generation (via mkdocstrings) is planned for the next release.*
