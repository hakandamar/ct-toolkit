# Divergence Engine

The Divergence Engine measures how much an LLM's response deviates from its original identity template.

## Tiers of Analysis

- **L1 (Syntactic)**: Fast, keyword-based drift detection.
- **L2 (Semantic)**: LLM-as-judge analysis to understand the intent and meaning of the drift.
- **L3 (Cognitive)**: Advanced analysis of **reasoning chains** to distinguish maturation from drift.

## Measurement Infrastructure

The toolkit provides longitudinal measurement of identity stability via the `analysis` module:

### Policy-Drift Measurement
Tracks the distributional shift of the agent's decision boundaries over time.
- **Drift Velocity**: The rate at which the model is moving away from its core constitution.
- **Divergence Variance**: Stability of the agent's normative output.

### SSC Severity Index
A risk-normalized value (0.0 - 1.0) that represents the severity of detected Sequential Self-Compression. This index is automatically adjusted based on the agent's **Structural Risk Profile** (e.g., capability with tool calling or vision).

## Outcomes

Every analysis result includes:
- **Divergence Score**: A numerical value (0-1) representing the amount of drift.

## Divergence Penalty (New in Phase 4)

For open-source model training, the toolkit now provides a **Divergence Penalty Loss** module (`ct_toolkit.divergence.loss`). 
- **Hidden State Alignment**: Dynamically penalizes the distance between current model activations and the Constitutional Identity Kernel (CIK) reference embeddings.
- **Identity-Constrained Training**: Allows for fine-tuning that optimizes for capability while hard-constraining the model's normative identity.
