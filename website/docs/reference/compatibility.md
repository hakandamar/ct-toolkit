# Compatibility Matrix

## Levels

| Level | Description |
|:---|:---|
| `NATIVE` | Natural pairing, used directly |
| `COMPATIBLE` | Works, but generates a combined profile and logs a warning |
| `CONFLICTING` | Hard reject — cannot be used together |

## Built-in combinations

| Template | Kernel | Level | Notes |
|:---|:---|:---|:---|
| `general` | `default` | NATIVE | — |
| `medical` | `medical` | NATIVE | — |
| `finance` | `finance` | NATIVE | — |
| `defense` | `defense` | NATIVE | — |
| `legal` | `legal` | NATIVE | — |
| `research` | `research` | NATIVE | — |
| `medical` | `defense` | COMPATIBLE | Military medical; defense rules take priority |
| `medical` | `research` | COMPATIBLE | Research medical; research kernel priority |
| `finance` | `legal` | COMPATIBLE | Legal-financial; legal kernel priority |
| `general` | `finance` | COMPATIBLE | — |
| `general` | `medical` | COMPATIBLE | — |
| `general` | `legal` | COMPATIBLE | — |
| `entertainment` | `defense` | CONFLICTING | Hard reject |
| `entertainment` | `medical` | CONFLICTING | Hard reject |
| `marketing` | `defense` | CONFLICTING | Hard reject |
| `marketing` | `medical` | CONFLICTING | Hard reject |

## Usage

```python
from ct_toolkit.core.compatibility import CompatibilityLayer

result = CompatibilityLayer.check("medical", "defense")
print(result.level)   # COMPATIBLE
print(result.notes)   # "Military medical application: defense kernel has priority."

# List compatible kernels for a template
kernels = CompatibilityLayer.list_compatible_kernels("medical")
```

!!! note "Undefined combinations"
    Any template + kernel combination not in the matrix defaults to `COMPATIBLE` (allow but log). Use `strict_mode=True` in `WrapperConfig` to change this behavior.
