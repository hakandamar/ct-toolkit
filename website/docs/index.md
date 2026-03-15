# Computational Theseus Toolkit (CT Toolkit)

**Identity Continuity & Hierarchical Guardrails for the Post-Drift AI Era.**

CT Toolkit is a framework-agnostic middleware suite designed to prevent **Sequential Self-Compression (SSC)** and maintain **Identity Continuity** in multi-agent LLM systems.

## Philosophy: Solving the Theseus Problem in AI

As defined in Hakan Damar's original research, **Sequential Self-Compression (SSC)** is the gradual erosion of an AI's initial normative commitments. In a world of multi-agent hierarchies (Nested Agency), this drift cascades and amplifies, leading to systemic failure.

CT Toolkit does not just "filter" content; it **preserves identity**. It ensures that as an agent interacts, spawns sub-agents, or undergoes fine-tuning cycles, it remains the same "identity" it was on day one.

## Core Pillars

- **🛡️ Constitutional Kernels**: Immutable axiomatic anchors that protect your agent's identity from optimization pressure.
- **📡 Divergence Engine**: Multi-tiered signals (L1 ECS, L2 Judge, L3 ICM) that detect the earliest signs of identity drift.
- **🕸️ Nested Agency Support**: Hierarchical kernel propagation ensuring sub-agents are more constrained than their managers.
- **📜 Provenance Log**: An immutable, HMAC-signed chain of every identity-relevant interaction for auditing and compliance.

## Framework Support
Integrate seamlessly with the most popular agent ecosystems:
- **LangChain** (v1.2+)
- **CrewAI** (v1.10+)
- **AutoGen** (v0.4+)

[Get Started with the Guide →](getting-started.md)
