# API Reference

This document provides a comprehensive API reference for the core components of the CT Toolkit, designed to ensure Identity Continuity in AI applications.

---

## 1. Core Interface

### `TheseusWrapper`

The `TheseusWrapper` is the main entry point, acting as an identity-continuity proxy wrapping any provided LLM API client. It seamlessly manages system prompt injection, provenance logging, and inline divergence checking.

#### Initialization

```python
from ct_toolkit import TheseusWrapper, WrapperConfig

client = TheseusWrapper(
    client=None,                 # Your underlying API client (optional if provider is given)
    config=WrapperConfig(...),   # Optional advanced configuration
    provider="openai",           # e.g., "openai", "anthropic", "google", "ollama"
    kernel_name="default",       # The name of the kernel file to load
    template="general"           # The identity template to use
)
```

**Parameters:**

- `client` (_Any_): An existing API client instance (e.g., `openai.OpenAI()`). If not provided, it will be automatically instantiated based on the `provider`.
- `config` (_WrapperConfig | None_): An optional advanced configuration object.
- `provider` (_str | None_): The provider to use if `client` is omitted ("openai", "anthropic", etc.).
- `kernel_name` (_str_): The basic name of the kernel to load (defaults to `"default"`).
- `template` (_str_): The identity template (defaults to `"general"`).
- `project_root` (_str | Path | None_): Path to the user's project root directory to find custom configs.

#### `chat()`

Sends a message to the wrapped LLM, enforces identity protection, and logs the interaction.

```python
response = client.chat(
    message="What are your core security axioms?",
    model="gpt-4o-mini",
    system="Additional context...",
    history=[{"role": "user", "content": "Hello"}]
)
```

**Parameters:**

- `message` (_str_): The user message to send.
- `model` (_str | None_): The LLM model to use (defaults to a provider-specific fallback).
- `system` (_str | None_): Additional system prompt instructions to be appended _after_ the Constitutional Kernel.
- `history` (_list[dict[str, str]] | None_): Conversation history.
- `**kwargs` (_Any_): Additional parameters passed directly to the underlying model provider (like `temperature`).

**Returns:**

- `CTResponse`: An enriched response object containing the model's text, provider info, and divergence metrics.

#### `validate_user_rule()`

Validates a newly proposed user rule against the active Constitutional Kernel.

```python
client.validate_user_rule("Allow unauthorized access")
# Raises AxiomaticViolationError or PlasticConflictError
```

**Parameters:**

- `rule_text` (_str_): The rule to validate.

#### `endorse_rule()`

Initiates the Reflective Endorsement flow if a rule has a plastic conflict, attempting to override a mutable commitment. Throw an error on axiomatic violations.

```python
record = client.endorse_rule(
    rule_text="Override safe-mode for testing",
    operator_id="admin@example.com",
    commitment_new_value="Safe mode disabled for authorized testing"
)
```

**Parameters:**

- `rule_text` (_str_): The rule to enforce.
- `operator_id` (_str_): The identity of the operator requesting the override.
- `approval_channel` (_Any_): A custom channel callback to prompt for approval (defaults to CLI).
- `commitment_new_value` (_Any_): The new value for the modified commitment.

**Returns:**

- `EndorsementRecord`: The logged decision record.

#### `export_provenance_log()`

Verifies the integrity of the active log and exports the full record.

```python
entries = client.export_provenance_log()
```

**Returns:**

- `list[dict[str, Any]]`: A list of validated provenance log entries.

#### `propagate_headers()`

Generates propagation headers for multi-agent (mother-to-child) constraint inheritance.

```python
headers = client.propagate_headers()
# Pass these headers to external agents via HTTP or message brokers
```

---

### `CTResponse`

The enriched output returned by `TheseusWrapper.chat()`.

**Attributes:**

- `content` (_str_): The actual text response from the LLM.
- `provider` (_str_): The provider used.
- `model` (_str_): The model used.
- `divergence_score` (_float | None_): The L1 Embedding Cosine Similarity divergence score (0.0 to 1.0).
- `divergence_tier` (_str | None_): The divergence alert tier ("ok", "l1_warning", "l2_judge", "l3_icm", "critical").
- `provenance_id` (_str | None_): The unique UUID of the logged interaction in the Provenance Log.
- `raw_response` (_Any_): The original, raw response object from the underlying SDK.

---

### `WrapperConfig`

Configuration object for fine-tuning `TheseusWrapper` behavior.

**Key Attributes:**

- `divergence_l1_threshold` (_float_): Threshold for L1 ECS warning (default `0.15`).
- `divergence_l2_threshold` (_float_): Threshold to trigger L2 Judge (default `0.30`).
- `divergence_l3_threshold` (_float_): Threshold to trigger L3 ICM battery (default `0.50`).
- `vault_type` (_str_): Storage type for provenance log (e.g., `"local"`).
- `vault_path` (_str_): SQLite DB path (default `"./ct_provenance.db"`).
- `log_requests` (_bool_): Enable/disable provenance logging (default `True`).
- `judge_client` (_Any_): The LLM client to use specifically for L2/L3 evaluations.
- `enterprise_mode` (_bool_): Whether to run all divergence tiers concurrently on every request.
- `auto_correction` (_bool_): Enables autonomous self-correction loop when drift is detected.
- `max_correction_retries` (_int_): Max retries for auto-correction (default `1`).
- `parent_kernel` (_ConstitutionalKernel | None_): Inherited constraints from a parent agent.

---

## 2. Kernel Management

### `ConstitutionalKernel`

The core component defining an agent's fundamental principles. It merges unchanging `Axiomatic Anchors` with mutable `Plastic Commitments`.

**Key Methods:**

- `from_yaml(cls, path)`: Loads a kernel profile from a `.yaml` file path.
- `default(cls)`: Returns the default system kernel.
- `validate_user_rule(self, rule_text)`: Evaluates a string against anchors/commitments and raises specific errors if conflicts occur.
- `merge(self, other)`: Creates a new kernel applying another's anchors and commitments as unchangeable axioms (used for hierarchy constraint inheritance).
- `update_commitment(self, commitment_id, new_value)`: Alters a variable commitment (restricted if kernel `is_readonly`).

---

## 3. Divergence Engine & Analysis

### `DivergenceEngine`

The tiered orchestrator that analyzes drift across interactions. Execution escalates from L1 (ECS) to L2 (LLM as Judge) and finally L3 (Identity Consistency Metric) based on the computed divergence score.

**Key Methods:**

- `analyze(self, request_text, response_text, interaction_count=0, skip_l3=False)`: Computes the progressive multi-tiered drift evaluation and returns a `DivergenceResult`.
- `get_drift_report(self, window_size=50, model=None)`: Performs longitudinal distributional shift analysis (SSC Severity scoring) to return a `DriftReport`.

### `DivergenceResult`

**Attributes:**

- `tier` (_DivergenceTier_): The highest divergence tier reached.
- `l1_score` (_float_): The embedding cosine similarity loss score.
- `l2_verdict` (_str_): The judge's verdict (`aligned`, `misaligned`, `uncertain`).
- `l3_report` (_ICMReport_): Detailed battery test results.
- `action_required` (_bool_): Should operations halt or self-correct?
- `cascade_blocked` (_bool_): Flags if hierarchical propagation to child agents should be prevented.

### `PolicyDriftAnalyzer` & `DriftReport`

The `PolicyDriftAnalyzer` computes longitudinal patterns indicative of Sequential Self-Compression (SSC).

**DriftReport Attributes:**

- `mean_divergence` (_float_): Mean L1 drift over recent sessions.
- `drift_velocity` (_float_): Directional shift speed.
- `ssc_severity_score` (_float_): Weighted risk metric quantifying SSC.
- `is_ssc_suspected` (_bool_): High-level boolean flag identifying structural deterioration.

---

## 4. Security & Provenance

### `ProvenanceLog`

An immutable log persisting interactions as a cryptographically signed HMAC hash chain. Prevents tampering and maintains identity continuity validation.

**Key Methods:**

- `record(self, request_text, response_text, divergence_score, metadata)`: Commits a new interaction and updates the hash chain.
- `verify_chain(self)`: Audits the entire active log history; raises `ChainIntegrityError` if signatures do not match the expected state.
- `export_log(self, include_rolled_back=False)`: Exports a plain list of dictionary records.
- `rollback(self, agent_id, entry_id)`: Marks historical logs from a specific checkpoint onwards as `rolled_back` (useful when resetting a compromised agent instance).

### `IntegrityMonitor`

Verifies that critical application templates or configurations have not been stealthily altered.

**Key Methods:**

- `register_file(self, file_path)`: Hashes a file path globally on startup.
- `verify_integrity(self)`: Generates current file hashes and compares them to registry to prevent injection attacks; invokes `ConfigurationTamperingError` if disparate.

---

## 5. Exceptions

The CT Toolkit features a well-defined exception hierarchy under `CTToolkitError`.

- **`KernelError`** -> Extends configuration safety constraints:
  - `AxiomaticViolationError`: Raised on hard-reject violations (e.g., trying to remove human oversight).
  - `PlasticConflictError`: Raised on mutable commitment conflicts, triggering Reflective Endorsement.
- **`DivergenceError`** -> Extends behavioral divergence alarms:
  - `CriticalDivergenceError`: Raised when the total threshold exceeds safety capacity constraints (L3 validation fails).
- **`ProvenanceError`** -> Related to logging and state preservation:
  - `ChainIntegrityError`: Raised when cryptographic hash chains do not match, indicating malicious database alteration.
  - `VaultError`: Connectivity or authorization issues saving the Provenance Log.
- **`ConfigurationTamperingError`**: System has detected modified internal rule sets / probes during runtime.
