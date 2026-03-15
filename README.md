# Computational Theseus Toolkit (CT Toolkit)

> **Identity Continuity Guardrails for Agentic Systems**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![PyPI version](https://badge.fury.io/py/ct-toolkit.svg)](https://badge.fury.io/py/ct-toolkit)
[![Documentation](https://img.shields.io/badge/docs-GitHub%20Pages-blue.svg)](https://hakandamar.github.io/ct-toolkit/)

CT Toolkit is an open-source security layer designed to preserve the **identity continuity** of AI agents over time. It implements the **Nested Agency Architecture (NAA)** framework to prevent **Sequential Self-Compression (SSC)** in multi-agent hierarchies.

---

## 📖 Official Documentation
For full API reference, architecture details, and integration guides, visit our documentation site:
👉 [**https://hakandamar.github.io/ct-toolkit/**](https://hakandamar.github.io/ct-toolkit/)

---

## Why CT Toolkit?

In complex agentic workflows, LLMs tend to "drift" from their original instructions. CT Toolkit provides the mathematical and cryptographic guardrails to ensure your agents remain aligned with their core constitution, even across deep hierarchies.

- **Constitutional Kernels**: Axiomatic identity anchors.
- **Divergence Engine**: Multi-tiered drift analysis (L1/L2/L3).
- **Hierarchical Propagation**: Mother-to-child constraint inheritance.
- **Provenance Log**: Immutable HMAC-signed interaction history.

---

## Quick Start

```bash
pip install ct-toolkit
```

```python
from ct_toolkit import TheseusWrapper

# One-line injection for any LLM provider
client = TheseusWrapper(provider="openai")

# Guardrails and drift analysis applied automatically
response = client.chat("What are your core security axioms?")

print(response.content)
print(f"Divergence Score: {response.divergence_score}")
```

---

## 🚦 Project Health & Status

| Metric | Status |
| :--- | :--- |
| **Tests** | ✅ 214/215 passing (92% coverage) |
| **Last Phase** | ✅ Phase 4: Open-Source Support & Live Verification (Complete) |
| **Current Goal** | 🔶 Phase 5: Vault and Security Infrastructure |

For a detailed breakdown of the 8-phase roadmap, see [**PROJECT_STATUS.md**](docs/PROJECT_STATUS.md).

### Framework Support
Seamlessly integrate with your favorite frameworks:

```python
# LangChain
from ct_toolkit.middleware.langchain import TheseusChatModel
llm = TheseusChatModel(provider="openai")

# CrewAI
TheseusCrewMiddleware.apply_to_crew(crew, manager_wrapper)
```

---

## Theoretical Foundation
Translating the framework proposed in [**The Computational Theseus (2025)**](https://hakandamar.com/the-computational-theseus-engineering-identity-continuity-as-a-guardrail-against-sequential-963918c1720d) into engineering practice.

---

## License
Apache License 2.0.
