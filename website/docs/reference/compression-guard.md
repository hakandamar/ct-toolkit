# ContextCompressionGuard Reference

The `ContextCompressionGuard` is responsible for detecting and auditing silent context compression/summarization events performed by LLM providers.

## Initialization

The guard is typically initialized automatically by `TheseusWrapper` based on the `WrapperConfig`.

```python
from ct_toolkit.core.compression_guard import ContextCompressionGuard

# Manual initialization
guard = ContextCompressionGuard(
    threshold=0.85,
    embedding_client=my_client
)
```

## Methods

### `analyze_summary_drift(original_messages, new_summary) → dict`

Compares the original message history with a new summary/compacted version to detect semantic drift.

**Parameters:**
- `original_messages`: List of message dictionaries representing the uncompressed history.
- `new_summary`: The new summary string or list of compressed messages.

**Returns:**
- `similarity`: Cosine similarity score (0.0–1.0).
- `drift_detected`: `True` if similarity < threshold.
- `critical_drift`: `True` if similarity is significantly below threshold (risk of identity loss).

### `record_audit(audit_data) → None`

Records the results of a compression audit in the provenance log.

## Integration with Middlewares

### LangChain
Exposed via the `compression_guard` property on `TheseusChatModel`.

### CrewAI
Settings are propagated to all agents; the guard handles internal audits for each agent's LLM calls.
