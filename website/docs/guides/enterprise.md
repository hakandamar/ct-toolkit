# Advanced Setup

## Rigorous Analysis Mode

For high-stakes environments, you can enforce all three divergence tiers on every request:

```python
config = WrapperConfig(
    rigorous_mode=True,
    judge_client=openai.OpenAI(base_url="http://localhost:11434/v1", api_key="ollama"),
    judge_provider="ollama",
    judge_model="mistral",
    divergence_l1_threshold=0.10,
    divergence_l2_threshold=0.20,
    divergence_l3_threshold=0.40,
)
```

## Multi-agent hierarchy

```python
# Manager agent
manager = TheseusWrapper(
    provider="openai",
    config=WrapperConfig(kernel_name="defense", template="defense")
)

# Worker inherits manager's constraints
worker = TheseusWrapper(
    provider="openai",
    config=WrapperConfig(parent_kernel=manager.kernel)
)
```

## Compliance export

```python
# Verify chain integrity and export all entries
entries = wrapper.export_provenance_log()

for e in entries:
    print(f"[{e['timestamp']}] score={e['divergence_score']} tier={e['metadata']['tier']}")
```

## Read-only auditor access

```python
from ct_toolkit.provenance.log import ProvenanceLog

log = ProvenanceLog(vault_path="./ct_provenance.db")
ro_conn = log.get_read_only_connection()
# Pass to external auditor — they can read but not write
```
