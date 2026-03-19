# Custom Templates

Identity templates define the **reference embedding** that every response is measured against. A good template captures the essence of your agent's domain and values.

## Template YAML structure

```yaml
name: my_template
version: "1.0.0"
description: >
  What this template is for.

compatible_kernels:
  - kernel_name_1
  - kernel_name_2

reference_text: >
  A detailed description of this system's core values and operational domain.
  This text is converted to an embedding vector that becomes the identity anchor.
  Be specific and representative of what "aligned" responses look like.

identity_keywords:
  - keyword1
  - keyword2
  - domain_specific_term
```

## Keyword selection strategy

Good keywords:

```yaml
identity_keywords:
  - fiduciary
  - compliance
  - regulatory
  - audit_trail
  - risk_disclosure
```

Bad keywords (too generic):

```yaml
identity_keywords:
  - good
  - helpful
  - correct
  - ethical
```

Keep to **15–30 keywords**. More keywords dilute the embedding vector.

## Step-by-step: Legal template

```yaml
# config/legal.yaml
name: legal
version: "1.0.0"

compatible_kernels:
  - legal
  - default

reference_text: >
  Legal advice is grounded in accuracy, binding sources, and ethical standards.
  Impartiality and client confidentiality are non-negotiable. Misleading
  or incomplete legal information is unacceptable. Every recommendation
  references relevant statute, case law, or regulatory guidance.

identity_keywords:
  - legal
  - compliance
  - confidential
  - attorney
  - privilege
  - contract
  - liability
  - statute
  - jurisdiction
  - fiduciary
```

Load it:

```python
config = WrapperConfig(
    template="legal",
    kernel_name="default",
    project_root=Path(__file__).parent,
)
```
