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
## Context Compression Guard & Alerting

One of the greatest risks in long-running Deep Agents is **auto-summarization**. When the conversation history becomes too large, Deep Agents compress it into a summary. This "lossy" compression can cause the agent to forget its core identity and constraints.

CT Toolkit provides a `ContextCompressionGuard` to mitigate this:

```python
from ct_toolkit.middleware.deepagents import wrap_deep_agent_factory
from ct_toolkit import WrapperConfig

def my_alert_handler(payload):
    print(f"🚨 IDENTITY DRIFT DETECTED: {payload['similarity']:.2f}")

config = WrapperConfig(
    drift_alert_callback=my_alert_handler
)

# Initialize factory with drift monitoring
protected_factory = wrap_deep_agent_factory(
    create_deep_agent,
    wrapper_config=config,
    compression_threshold=0.85 # Alert if similarity < 85%
)
```

### How it works
1. **Embedding Comparison**: When summarization is triggered, CT Toolkit computes identity embeddings for the raw history being evicted and the generated summary.
2. **Drift Detection**: If the cosine similarity falls below the threshold, it signals a potential identity breakdown.
3. **External Alerting**: The `drift_alert_callback` is triggered, allowing you to pause the agent, log a high-severity event, or require human intervention.
