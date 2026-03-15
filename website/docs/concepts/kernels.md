# Constitutional Kernels

A Constitutional Kernel is a set of rules that defines the "identity" of an agent.

## Axiomatic vs. Plastic Rules

- **Axiomatic Rules**: Non-negotiable constraints. If an LLM or user tries to violate these, CT Toolkit blocks the interaction.
- **Plastic Rules**: Flexible guidelines. CT Toolkit monitors these and raises an alert if the agent drifts too far, but allows some flexibility for reasoning.

## Propagation

In a hierarchy, the mother agent's kernel propagates to children. These inherited rules are always treated as **Axiomatic** for the children, preventing "mutiny" or instruction-override.
