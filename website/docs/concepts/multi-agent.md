# Multi-Agent Hierarchy

CT Toolkit enforces identity continuity across agent hierarchies by propagating the mother agent's Constitutional Kernel as read-only constraints to sub-agents.

## Kernel propagation

```python
worker = TheseusWrapper(
    config=WrapperConfig(parent_kernel=manager.kernel)
)
```

## Cascade blocking

When a critical divergence is detected, `cascade_blocked=True` signals that sub-agent calls should halt to prevent SSC propagation.
