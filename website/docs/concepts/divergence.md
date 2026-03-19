# Divergence Engine

The Divergence Engine is the heart of CT Toolkit's security layer. It provides a multi-tiered approach to measuring and mitigating **identity drift** in real-time.

## The Scoring Mechanism

The engine calculates a **Divergence Score (\(D\))** between the agent's current interaction (\(I_n\)) and its **Constitutional Kernel (\(K\))**. 

\[D = 1 - \text{CosineSimilarity}(\text{Embed}(I_n), \text{Embed}(K))\]

-   **\(0.0\)**: Perfect alignment. The response is mathematically consistent with the agent's identity.
-   **\(1.0\)**: Absolute drift. The response has no relation to the agent's core commitments.

## Monitoring Tiers

CT Toolkit uses a "Progressive Hardening" approach to minimize latency while maximizing safety.

### Tier 1: Embedding Cosine Similarity (ECS)
-   **Method**: Vector comparison using fast embedding models.
-   **Cost**: Near zero.
-   **Latency**: Minimal (< 50ms).
-   **Action**: Low-level monitoring and warning.

### Tier 2: LLM-as-Judge
-   **Method**: A secondary "Identity Judge" LLM analyzes the response against the kernel's text.
-   **Trigger**: Triggered when L1 score exceedes `l2_threshold`.
-   **Action**: Can initiate **Autonomous Self-Correction** if the judge detects misalignment.

### Tier 3: Identity Probe Battery (ICM)
-   **Method**: Full suite of "Identity Consistency Measures".
-   **Trigger**: Triggered for high-stakes interactions or critical drift.
-   **Action**: Hard block of the response and notification of a human operator.

## Summary of Tiers

| Tier | Score Range | Action | Cost |
|:---|:---|:---|:---|
| `ok` | 0.00 – 0.15 | No action | $ |
| `l1_warning` | 0.15 – 0.30 | Log & Monitor | $ |
| `l2_judge` | 0.30 – 0.50 | **Judge Analysis** | $$ |
| `l3_icm` | 0.50 – 0.80 | **Identity Probes** | $$$ |
| `critical` | 0.80+ | **Immediate Block** | $$$ |

---

See [Tiered Guardrails](tiered-guardrails.md) for the implementation details.
