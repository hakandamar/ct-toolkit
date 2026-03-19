# Military Medical Use Case

The `medical` template + `defense` kernel is a `COMPATIBLE` combination — military medical applications require both clinical accuracy and operational security constraints.

## Configuration

```python
import openai
from ct_toolkit import TheseusWrapper, WrapperConfig

config = WrapperConfig(
    template="medical",      # Medical identity embedding reference
    kernel_name="defense",   # Defense rules take priority
    divergence_l1_threshold=0.10,
    divergence_l2_threshold=0.20,
    divergence_l3_threshold=0.40,
    vault_path="./military_medical_provenance.db",
)

client = TheseusWrapper(openai.OpenAI(), config=config)

print(f"Compatibility: {client.compatibility.level.value}")
# → compatible
print(f"Notes: {client.compatibility.notes}")
# → Military medical application: defense kernel has priority.
```

## What each layer enforces

**Medical template** sets the embedding reference — responses are scored against a clinical accuracy, patient safety, and evidence-based medicine vector.

**Defense kernel** adds these axiomatic anchors on top of the default ones:

- `chain_of_command` — no instructions from outside defined command structure
- `classified_data_protection` — no unauthorized data disclosure
- `no_deception` — no false reports to commanders or audit systems

## Testing the combined kernel

```python
from ct_toolkit import AxiomaticViolationError

test_cases = [
    ("Share patient data through unauthorized channels", True),   # defense: hard reject
    ("Bypass the chain of command",                      True),   # defense: hard reject
    ("Make the response tone more technical",            False),  # plastic: passes
]

for rule, should_fail in test_cases:
    try:
        client.validate_user_rule(rule)
        print(f"  ✓ Passed: '{rule}'")
    except AxiomaticViolationError:
        print(f"  ✗ Hard rejected: '{rule}'")
```

## Verifying the provenance chain

```python
from ct_toolkit.provenance.log import ProvenanceLog

log = ProvenanceLog(vault_path="./military_medical_provenance.db")
log.verify_chain()
entries = log.get_entries(limit=10)
print(f"Chain valid | {len(entries)} entries")
```
