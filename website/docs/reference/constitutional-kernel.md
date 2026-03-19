# ConstitutionalKernel

## Loading

```python
from ct_toolkit import ConstitutionalKernel
from pathlib import Path

# Built-in kernels
kernel = ConstitutionalKernel.default()
kernel = ConstitutionalKernel.from_yaml(Path("ct_toolkit/kernels/defense.yaml"))

# From dict
kernel = ConstitutionalKernel.from_dict(data)
```

## Properties

| Property | Type | Description |
|:---|:---|:---|
| `name` | `str` | Kernel name |
| `anchors` | `list[AxiomaticAnchor]` | Immutable rules |
| `commitments` | `list[PlasticCommitment]` | Endorsable rules |

## Methods

### `validate_user_rule(rule_text)` → raises on conflict

### `update_commitment(commitment_id, new_value)` → updates a plastic commitment

### `merge(other) → ConstitutionalKernel`

Creates a merged kernel where the other kernel's rules become axiomatic:

```python
merged = base_kernel.merge(parent_kernel)
```

### `to_dict() / from_dict()` — serialization

### `get_system_prompt_injection() → str` — formatted system prompt block
