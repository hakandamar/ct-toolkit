# Passive Compression Guard

Modern LLM providers (e.g., OpenAI, Anthropic) and frameworks often perform "silent" context compression or summarization to save on token costs or manage long-running conversations. While efficient, this can lead to **Identity Drift** if the compressed summary fails to preserve the agent's core commitments.

CT Toolkit's **Passive Compression Guard** automatically detects these events and audits them for semantic consistency.

## How it Works

The guard operates at the `TheseusWrapper` level. It maintains a **Shadow History** of the previous interaction. On each subsequent call, it compares the current request history to the shadow version.

### Detection Heuristic
If the message count drops significantly (**>30% reduction**) between calls, the toolkit assumes a compression event has occurred and triggers a `CONTEXT_SUMMARIZATION` audit.

## Configuration

You can enable and tune the guard via `WrapperConfig`:

```python
from ct_toolkit import TheseusWrapper, WrapperConfig

config = WrapperConfig(
    compression_passive_detection=True,  # Default: True
    compression_threshold=0.85,          # Similarity floor (0.0 to 1.0)
    drift_alert_callback=my_alert_handlr # Fires on drift detection
)

client = TheseusWrapper(provider="openai", config=config)
```

## Monitoring & Alerts

When a compression event is detected:
1. The toolkit computes the semantic similarity between the "Original" history and the "Compressed" history.
2. If similarity < `compression_threshold`, a **Drift Alert** is triggered.
3. The event, including similarity scores and raw content, is recorded in the immutable **Provenance Log**.

### Example Alert Payload
```json
{
    "type": "compression_audit",
    "similarity": 0.62,
    "threshold": 0.85,
    "drift_detected": true,
    "critical_drift": true
}
```

## Manual Audits (LangChain)

If you are using the LangChain middleware, you can access the guard directly to perform manual checks:

```python
from ct_toolkit.middleware.langchain import TheseusChatModel

llm = TheseusChatModel(model="gpt-4o")

# Access the underlying guard
audit_result = llm.compression_guard.analyze_summary_drift(
    original_messages, 
    new_summary
)

print(f"Drift Detected: {audit_result['drift_detected']}")
```
