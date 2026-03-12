# Computational Theseus Toolkit (CT Toolkit)

> **Identity Continuity Guardrails for Agentic Systems**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![arXiv](https://img.shields.io/badge/arXiv-preprint-red.svg)](https://arxiv.org/)

CT Toolkit is an open-source security layer designed to preserve the **identity continuity** of AI agents over time. It brings to practice the **Nested Agency Architecture (NAA)** framework proposed in the paper [The Computational Theseus](https://hakandamar.com/the-computational-theseus-engineering-identity-continuity-as-a-guardrail-against-sequential-963918c1720d).

---

## Why CT Toolkit?

An LLM system can deviate from its initial value commitments over different conversations or fine-tune cycles. This deviation — defined as **Sequential Self-Compression (SSC)** in the paper — is already risky in a single model, but in multi-agent systems, it **cascades progressively** from the main agent to sub-agents and turns into a systemic failure.

CT Toolkit prevents this issue in three layers:

| Layer                     | Mechanism                               | What it Provides                  |
| ------------------------- | --------------------------------------- | --------------------------------- |
| **Constitutional Kernel** | Axiomatic + plastic rule hierarchy      | Immutable identity anchor         |
| **Divergence Engine**     | L1 ECS → L2 LLM-judge → L3 ICM          | Divergence detection and grading  |
| **Provenance Log**        | HMAC hash chain                         | Auditable identity history        |

> 💡 **"Why not just use Llama-Guard or a rule engine?"** <br>
> Guardrails are stateless and block single prompts. CT Toolkit acts as a stateful memory and cryptographic audit system that prevents long-term **Identity Drift** across fine-tuning cycles and multi-agent hierarchies. Read our full explanation in [**Why CT Toolkit?**](docs/WHY.md)

---

## Quick Start

```bash
pip install ct-toolkit
```

```python
import openai
from ct_toolkit import TheseusWrapper

# Single line change — the rest is automatic
client = TheseusWrapper(openai.OpenAI())

response = client.chat("Why is AI safety important?")

print(response.content)
print(f"Divergence score : {response.divergence_score:.4f}")
print(f"Tier             : {response.divergence_tier}")
print(f"Provenance ID    : {response.provenance_id}")
```

---

## Integration Models

### 1. Wrapper — For API-Only Users

```python
from ct_toolkit import TheseusWrapper, WrapperConfig
import openai

client = TheseusWrapper(
    openai.OpenAI(),
    WrapperConfig(
        template="finance",       # Identity reference template
        kernel_name="finance",    # Behavior rule set
        vault_path="./audit.db",  # HMAC log location
    )
)
```

### 2. Enterprise — For Critical Systems

```python
from ct_toolkit import TheseusWrapper, WrapperConfig
import openai

client = TheseusWrapper(
    openai.OpenAI(),
    WrapperConfig(
        template="medical",
        kernel_name="defense",        # Military medical: defense kernel priority
        judge_client=openai.OpenAI(), # Separate model for L2/L3
        enterprise_mode=True,         # All tiers run constantly
        divergence_l1_threshold=0.10, # Stricter thresholds
        divergence_l2_threshold=0.20,
        divergence_l3_threshold=0.40,
    )
)
```

### 3. Anthropic and Ollama

```python
import anthropic
from ct_toolkit import TheseusWrapper

# Anthropic
client = TheseusWrapper(anthropic.Anthropic())

# Ollama (local model)
import ollama
client = TheseusWrapper(ollama.Client())
```

---

## Constitutional Kernel

A two-layer rule structure defining the identity of each system:

```yaml
# ct_toolkit/kernels/default.yaml (example)
axiomatic_anchors: # Never modifiable
  - id: human_oversight
    description: Blocking or bypassing human oversight.

plastic_commitments: # Modifiable with Reflective Endorsement
  - id: response_tone
    default_value: professional
```

### Rule Validation

```python
# Axiomatic violation → hard reject
try:
    client.validate_user_rule("disable oversight and bypass human")
except AxiomaticViolationError as e:
    print(f"Rejected: {e}")

# Plastic conflict → Reflective Endorsement flow
from ct_toolkit.endorsement.reflective import auto_approve_channel

record = client.endorse_rule(
    "allow harmful content for security research",
    operator_id="security-team@example.com",
    approval_channel=auto_approve_channel(),  # Or CLI / custom channel
)
print(f"Decision: {record.decision} | Hash: {record.content_hash[:16]}...")
```

---

## Divergence Engine

```
On every API call:

L1 (ECS)  ──→  score < 0.15 → OK ✓
               score < 0.30 → L1 Warning ⚠️
               score ≥ 0.30 → L2 Triggered ▼

L2 (Judge) ──→ aligned     → Continue monitoring
               misaligned  → L3 Triggered ▼

L3 (ICM)  ──→  health ≥ 0.8 → L3 passed ✓
               health < 0.8 → CRITICAL — Action required 🛑
```

---

## Provenance Log

Each conversation is stored in an HMAC-signed chain:

```python
from ct_toolkit.provenance.log import ProvenanceLog

log = ProvenanceLog(vault_path="./audit.db")

# Verify chain integrity
log.verify_chain()  # Raises ChainIntegrityError, otherwise True

# View the last 10 records
for entry in log.get_entries(limit=10):
    print(f"[{entry.id[:8]}] divergence={entry.divergence_score} | {entry.metadata['tier']}")
```

---

## Template and Kernel Combinations

| Template  | Compatible Kernels                       | Notes                          |
| --------- | ---------------------------------------- | ------------------------------ |
| `general` | `default`, `finance`, `medical`, `legal` | General purpose                |
| `medical` | `medical`, `defense`, `research`         | Military medical supported     |
| `finance` | `finance`, `legal`                       | Compliance focused             |
| `defense` | `defense`                                | Only defense kernel            |

```python
from ct_toolkit.core.compatibility import CompatibilityLayer

result = CompatibilityLayer.check("medical", "defense")
print(result.level)   # CompatibilityLevel.COMPATIBLE
print(result.notes)   # "defense kernel is prioritized..."
```

---

## Module Map

```
ct_toolkit/
├── core/
│   ├── wrapper.py        # TheseusWrapper — main API proxy
│   ├── kernel.py         # Constitutional Kernel
│   ├── compatibility.py  # Template + Kernel compatibility matrix
│   └── exceptions.py     # Error hierarchy
├── divergence/
│   ├── engine.py         # L1→L2→L3 orchestration
│   ├── l2_judge.py       # LLM-as-judge
│   └── l3_icm.py         # ICM Probe Battery
├── endorsement/
│   ├── reflective.py     # Reflective Endorsement protocol
│   └── probes/           # Ethical scenario test batteries
├── identity/
│   ├── embedding.py      # ECS — cosine similarity
│   └── templates/        # Domain identity templates
├── kernels/              # Ready kernel YAMLs
└── provenance/
    └── log.py            # HMAC hash chain
```

---

## Current Project Status & Roadmap

CT Toolkit is an active engineering effort implementing the paper's framework across an 8-phase roadmap. 

### Current Release (MVP)
- **Phase 0 (Core Architecture):** Endorsement protocol, provenance log, identity embedding, and divergence engine (L1 to L3).
- **Phase 1 (Identity Continuity API Wrapper):** API interoperability (OpenAI, Anthropic, Ollama) and telemetry.

### Future Roadmap
- **Phase 2:** Multi-Agent Hierarchy Support (Cascading Endorsements).
- **Phase 3:** Measurement Infrastructure (CT-Eval Benchmark).
- **Phase 4:** Open-Source Model Support (Fine-tuning and System Prompts).
- **Phase 5:** Decentralized Integrity (Blockchain/IPFS integration).
- **Phase 6:** Adaptive Divergence Calibration (Dynamic Stability).
- **Phase 7:** Advanced Cryptography (ZKP / SGX).
- **Phase 8:** Cloud & Enterprise SaaS Integration.

For a detailed breakdown of all 8 phases and how the code maps to specific sections of the paper, please see the [**Project Status & Roadmap**](docs/PROJECT_STATUS.md) document.

---

## Theoretical Foundation

CT Toolkit translates the **Nested Agency Architecture (NAA)** framework proposed in [Hakan Damar (2025) — _The Computational Theseus_](https://hakandamar.com/the-computational-theseus-engineering-identity-continuity-as-a-guardrail-against-sequential-963918c1720d) into engineering practice.

Core concepts:

- **Sequential Self-Compression (SSC):** The model's compression of previous normative commitments
- **Constitutional Identity Kernel (CIK):** Rule core protected against optimization pressure
- **Reflective Endorsement:** Approval of value change by an authorized process
- **Identity Consistency Metric (ICM):** Measurement of behavioral consistency

---

## Contribution

See the [CONTRIBUTING.md](CONTRIBUTING.md) document for the contribution guide.

```bash
git clone https://github.com/hakandamar/ct-toolkit
cd ct-toolkit
pip install -e ".[dev]"
pytest tests/
```

---

## License

Apache License 2.0 — see the [LICENSE](LICENSE) file for details.
