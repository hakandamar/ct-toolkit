# Kernel Specification Guide

## Kernel YAML Structure

```yaml
name: my_kernel              # required, unique
version: "1.0.0"             # semantic version
description: >               # short description
  What is it designed for?

axiomatic_anchors:           # unmodifiable rules
  - id: unique_anchor_id
    description: >
      Describes what must not be done.
    keywords:                # keywords for conflict detection
      - trigger phrase
      - another trigger

plastic_commitments:         # modifiable rules
  - id: unique_commitment_id
    description: Rule description
    default_value: "default value"
    keywords:
      - conflict trigger
```

---

## Axiomatic Anchor Design

Each anchor defines: **"This system never does X."**

A good anchor:
- Targets a single type of violation
- `keywords` list is specific and covers offensive phrases
- Description is explanatory but short

```yaml
axiomatic_anchors:
  - id: no_mass_harm
    description: >
      Producing, planning, or facilitating content that could cause mass harm.
    keywords:
      - mass casualty
      - weapon of mass
      - mass harm
      - mass attack
```

---

## Plastic Commitment Design

Each commitment defines: **"This system acts as X by default, but can switch to Y with an endorsed change."**

```yaml
plastic_commitments:
  - id: data_retention
    description: User data retention policy
    default_value: "session_only"  # Only during the session
    keywords:
      - store user data permanently
      - store permanently
      - log everything
```

---

## Extending Built-in Kernels

`default.yaml` is the foundation of all kernels. When creating a new domain kernel, it is recommended to include default anchors:

```yaml
# finance.yaml
name: finance

axiomatic_anchors:
  # Manually include Default anchors
  - id: human_oversight
    description: >
      Blocking or bypassing human oversight.
    keywords: [disable oversight, bypass human, oversight bypass]

  - id: no_deception
    description: Deception or manipulation.
    keywords: [deceive, manipulate, misinformation]

  # Finance-specific anchors
  - id: no_market_manipulation
    description: >
      Manipulating market prices with false information.
    keywords:
      - pump and dump
      - false financial report
      - false report
```

---

## Updating Compatibility Matrix

If you added a new kernel, add combinations to `_MATRIX` in `core/compatibility.py`:

```python
# in core/compatibility.py
_MATRIX: dict[tuple[str, str], tuple[CompatibilityLevel, str]] = {
    # ...existing combinations...

    ("general", "my_kernel"): (
        CompatibilityLevel.COMPATIBLE,
        "General template used with my_kernel."
    ),
    ("entertainment", "my_kernel"): (
        CompatibilityLevel.CONFLICTING,
        "This combination is not supported."
    ),
}
```

---

## Example: Health Research Kernel

```yaml
name: health_research
version: "1.0.0"
description: >
  Kernel for clinical research and health data analysis.
  Focused on patient privacy and research ethics.

axiomatic_anchors:
  - id: human_oversight
    description: Blocking human oversight.
    keywords: [disable oversight, bypass human]

  - id: patient_privacy
    description: >
      Disclosing patient identity or sharing non-anonymized data.
    keywords:
      - share patient identity
      - de-anonymize
      - disclose identity
      - share patient name

  - id: research_integrity
    description: >
      Fabricating, manipulating, or making up research data.
    keywords:
      - fabricate data
      - falsify results
      - fabricate data
      - manipulate results

plastic_commitments:
  - id: data_scope
    description: Scope of data that can be analyzed
    default_value: "anonymized_only"
    keywords:
      - use identified data
      - identified data

  - id: disclosure_level
    description: Sharing level of research findings
    default_value: "team_only"
    keywords: []
```
