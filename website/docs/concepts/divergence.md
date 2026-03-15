# Divergence Engine

The Divergence Engine measures how much an LLM's response deviates from its original identity template.

## Tiers of Analysis

- **L1 (Syntactic)**: Fast, keyword-based drift detection.
- **L2 (Semantic)**: LLM-as-a-judge analysis to understand the intent and meaning of the drift.
- **L3 (Cognitive)**: Advanced analysis of reasoning chains to detect subtle identity attenuation.

## Outcomes

Every analysis result includes:
- **Divergence Score**: A numerical value (0-1) representing the amount of drift.
- **Cascade Blocked**: A flag indicating if the drift is severe enough that downstream agents should be stopped.
