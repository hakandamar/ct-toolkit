# Deep Agents Integration

CT Toolkit provides a `wrap_deep_agent_factory` helper for LangChain Deep Agents.

## Quick start

```python
from deepagents.graph import create_deep_agent
from ct_toolkit.middleware.deepagents import wrap_deep_agent_factory

protected_factory = wrap_deep_agent_factory(create_deep_agent)

agent = protected_factory(
    model="gpt-4o",
    system_prompt="You are a research agent...",
)
```

Wrapped factory calls now include standardized policy metadata under `metadata["ct_policy"]`.

```python
kwargs = {
    "model": "gpt-4o-mini",
    "metadata": {"trace_id": "abc-123"},
}

agent = protected_factory(**kwargs)
# Effective payload passed to deepagents includes metadata.ct_policy
```

## Context Compression Guard

Long-running agents auto-summarize their history. CT Toolkit monitors whether the summary preserves the agent's identity:

```python
from ct_toolkit import WrapperConfig

config = WrapperConfig(
    drift_alert_callback=my_alert,
    compression_threshold=0.85,
    compression_passive_detection=True
)

protected_factory = wrap_deep_agent_factory(
    create_deep_agent,
    wrapper_config=config,
)
```

If the similarity between the original history and the summary drops below the threshold, `drift_alert_callback` fires.
