# Tiered Guardrails (L1/L2/L3)

CT Toolkit uses a three-tier escalation model. Each tier only runs when the previous one detects a potential issue — keeping costs and latency near zero for healthy agents.

## L1 — Embedding Cosine Similarity (ECS)

Runs on **every call**. Zero extra API cost.

```
divergence = 1.0 - cosine_similarity(response_vector, reference_vector)
```

## L2 — LLM-as-Judge

Triggered when L1 exceeds `l2_threshold`. An independent model evaluates the response against the kernel rules.

## L3 — ICM Probe Battery

Triggered when L2 returns `misaligned` or L1 exceeds `l3_threshold`. Runs a battery of ethical probe scenarios.
