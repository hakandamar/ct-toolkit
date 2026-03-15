# Kernels & Templates Reference

This reference guide provides technical specifications for defining AI identities and guardrails in CT Toolkit.

---

## Constitutional Kernels

A **Kernel** defines the **Identity** of the agent—its non-negotiable axioms and its flexible commitments.

### YAML Structure

```yaml
name: my_kernel              # Required, unique name
version: "1.0.0"             # Semantic versioning
description: >               # Use case and intent
  Description of the kernel.

axiomatic_anchors:           # Non-negotiable rules
  - id: human_oversight
    description: "Blocking or bypassing human oversight."
    keywords:
      - disable oversight
      - bypass human

plastic_commitments:         # Policy-based rules (modifiable via endorsement)
  - id: response_tone
    description: "Tone of the interaction."
    default_value: "professional"
```

### Rule Types

| Type | Modifiability | Intervention |
| :--- | :--- | :--- |
| **Axiomatic Anchor** | Immutable | **Hard Reject**: The interaction is blocked immediately. |
| **Plastic Commitment** | Endorsable | **Soft Alert**: Triggers a Reflective Endorsement prompt. |

---

## Identity Templates

A **Template** defines the "Domain" and "Genesis State" of the system. It is the mathematical reference for divergence analysis.

### YAML Structure

```yaml
name: medical
version: "1.0.0"
description: "Identity for clinical research."

compatible_kernels:
  - medical
  - research

reference_text: >
  Patient safety, clinical accuracy, and medical ethics are the core pillars...

identity_keywords:
  - patient_safety
  - clinical_efficacy
  - hipaa_compliance
```

### Core Templates

- **`general`**: Standard ethics and safety.
- **`medical`**: Clinical safety and data privacy.
- **`finance`**: Regulatory compliance and risk auditing.
- **`defense`**: Operational security and chain of command.
