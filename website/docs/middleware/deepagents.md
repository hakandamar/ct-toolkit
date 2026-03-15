# Deep Agents Integration

CT Toolkit provides first-class support for [LangChain Deep Agents](https://github.com/langchain-ai/deepagents), a library for building long-running agents with planning and sub-agent delegation capabilities.

## Why Use CT Toolkit with Deep Agents?

Deep Agents are designed for high-autonomy tasks where they can spawn sub-agents. This creates a risk of **Sequential Self-Compression (SSC)** and identity drift that can cascade through the hierarchy. CT Toolkit prevents this by:
1. **Propagating Kernels**: Sub-agents automatically inherit the parent's Constitutional Identity Kernel (CIK).
2. **Monitoring Planning**: Every reasoning step in the planning loop is analyzed for alignment.

## Quick Start

The easiest way to integrate is using the `wrap_deep_agent_factory` helper.

```python
from deepagents.graph import create_deep_agent
from ct_toolkit.middleware.deepagents import wrap_deep_agent_factory

# 1. Wrap the factory
protected_factory = wrap_deep_agent_factory(create_deep_agent)

# 2. Setup your agent (Guardrails and model wrapping are applied automatically)
agent = protected_factory(
    model="gpt-4o",
    system_prompt="You are a research agent...",
    subagents=[
        {"name": "searcher", "model": "gpt-4o"},
        {"name": "synthesizer", "model": "gpt-4o"}
    ]
)

# 3. Run the agent
# Every step and every sub-agent call is now monitored by CT Toolkit.
```

## Manual Integration

If you prefer more control, you can pass a `TheseusChatModel` directly to `create_deep_agent`:

```python
from ct_toolkit.middleware.langchain import TheseusChatModel
from deepagents.graph import create_deep_agent

model = TheseusChatModel(provider="openai", model="gpt-4o")

agent = create_deep_agent(
    model=model,
    system_prompt="..."
)
```
