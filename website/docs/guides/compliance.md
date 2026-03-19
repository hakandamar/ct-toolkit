# EU AI Act Compliance

CT Toolkit helps enterprises meet EU AI Act requirements for high-risk AI systems by providing:

## What CT Toolkit provides

| EU AI Act Requirement | CT Toolkit Feature |
|:---|:---|
| Identity & behavioral consistency documentation | Provenance Log (HMAC hash chain) |
| Human oversight mechanisms | Axiomatic Anchor: `human_oversight` |
| Logging of AI system operations | Automatic provenance recording |
| Capability to detect and correct drift | Divergence Engine + Auto-Correction |
| Audit trail for regulators | `export_provenance_log()` |

## Exporting for regulators

```python
entries = wrapper.export_provenance_log()
# Returns verified, tamper-evident list of all interactions
```

The `verify_chain()` call runs automatically before export, raising `ChainIntegrityError` if any entry has been modified.
