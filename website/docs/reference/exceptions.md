# Exceptions

All CT Toolkit exceptions inherit from `CTToolkitError`.

```python
from ct_toolkit import (
    AxiomaticViolationError,
    PlasticConflictError,
    IncompatibleProfileError,
    CriticalDivergenceError,
    ChainIntegrityError,
)
```

## Kernel exceptions

| Exception | Trigger | Recoverable? |
|:---|:---|:---|
| `AxiomaticViolationError` | Rule conflicts with axiomatic anchor | ✗ Hard reject |
| `PlasticConflictError` | Rule conflicts with plastic commitment | ✓ Via Reflective Endorsement |

```python
try:
    wrapper.validate_user_rule(rule)
except AxiomaticViolationError as e:
    print(f"Blocked anchor: {e.anchor}")
except PlasticConflictError as e:
    print(f"Conflicting commitment: {e.commitment}")
```

## Compatibility exceptions

| Exception | Trigger |
|:---|:---|
| `IncompatibleProfileError` | Template + kernel combination is `CONFLICTING` |

## Divergence exceptions

| Exception | Trigger |
|:---|:---|
| `CriticalDivergenceError` | L3 health score below threshold |

## Provenance exceptions

| Exception | Trigger |
|:---|:---|
| `ChainIntegrityError` | HMAC chain verification failed (tampering detected) |
| `VaultError` | SQLite connectivity or permission error |

## Security exceptions

| Exception | Trigger |
|:---|:---|
| `ConfigurationTamperingError` | Kernel/template YAML file modified after startup |
| `MissingClientError` | No client provided and no env credentials found |
