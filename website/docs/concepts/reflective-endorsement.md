# Reflective Endorsement

When a user instruction conflicts with a **Plastic Commitment**, CT Toolkit initiates the Reflective Endorsement flow instead of silently blocking or allowing the change.

## Flow

```
PlasticConflictError detected
         │
ConflictRecord created
         │
Sent to approval channel (CLI / callback / API)
         │
    ┌────┴────┐
 APPROVED   REJECTED
    │           │
Kernel       No change
updated      
    │
EndorsementRecord signed → written to Provenance Log
```

## Usage

```python
record = wrapper.endorse_rule(
    "use identified data for this audit",
    operator_id="compliance-team@company.com",
    approval_channel=my_approval_callback,
)
```
