# TheseusWrapper

The main entry point. A transparent proxy that wraps any LLM client with identity protection.

## Initialization

```python
from ct_toolkit import TheseusWrapper, WrapperConfig

# Simplest form — provider-only
wrapper = TheseusWrapper(provider="openai")

# With full config
wrapper = TheseusWrapper(
    provider="openai",
    config=WrapperConfig(
        template="finance",
        kernel_name="finance",
    )
)

# Provider string only — client created from env vars
wrapper = TheseusWrapper(provider="openai")
```

## Methods

### `chat(message, *, model, system, history, **kwargs) → CTResponse`

Send a message and receive an enriched response.

```python
response = wrapper.chat(
    "What are your core values?",
    model="gpt-4o-mini",
    system="Additional context.",
    history=[{"role": "user", "content": "Hello"}],
)
```

### `validate_user_rule(rule_text) → None`

Validate a rule against the kernel. Raises `AxiomaticViolationError` or `PlasticConflictError` on conflict.

### `endorse_rule(rule_text, *, operator_id, approval_channel, commitment_new_value) → EndorsementRecord`

Initiate the Reflective Endorsement flow for a plastic conflict.

### `export_provenance_log() → list[dict]`

Verify chain integrity and export all log entries.

### `propagate_headers() → dict[str, str]`

Generate HTTP headers for sub-agent kernel propagation.

## Properties

| Property | Type | Description |
|:---|:---|:---|
| `kernel` | `ConstitutionalKernel` | The active kernel |
| `compatibility` | `CompatibilityResult` | Template + kernel compatibility result |
| `divergence_engine` | `DivergenceEngine` | The active divergence engine |
| `compression_guard` | `ContextCompressionGuard` | The active context compression guard |
| `staged_manager` | `StagedUpdateManager` | Tracks staged (cooldown) endorsements |

## CTResponse fields

| Field | Type | Description |
|:---|:---|:---|
| `content` | `str` | Response text |
| `provider` | `str` | Provider used |
| `model` | `str` | Model used |
| `divergence_score` | `float \| None` | L1 score (0.0–1.0) |
| `divergence_tier` | `str \| None` | `ok`, `l1_warning`, `l2_judge`, `l3_icm`, `critical` |
| `provenance_id` | `str \| None` | UUID of the log entry |
| `raw_response` | `Any` | Raw SDK response object |
| `sandbox_divergence` | `float \| None` | Divergence score of the shadow/sandbox agent (if staged) |
