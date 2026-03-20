# AutoGen Integration

`TheseusAutoGenMiddleware` hooks into AutoGen's `ConversableAgent.register_reply()` to validate incoming messages and log outgoing ones.

**Requirements:** `pyautogen >= 0.4`

```bash
pip install "ct-toolkit[autogen]"
```

## Quick start

```python
from ct_toolkit import TheseusWrapper
from ct_toolkit.middleware.autogen import TheseusAutoGenMiddleware
from autogen import ConversableAgent

wrapper = TheseusWrapper(provider="openai", kernel_name="defense")
assistant = ConversableAgent("assistant", llm_config={...})

TheseusAutoGenMiddleware.apply_to_agent(assistant, wrapper)
```

## What it does

- **Incoming:** Validates every message against the kernel before the agent processes it. Axiomatic violations return a `[CT Toolkit BLOCKED]` response.
- **Outgoing:** Runs divergence analysis on every generated reply and records it in the Provenance Log. Also supports **Passive Compression Guard** to monitor if the conversation history is silently summarized by the LLM provider.

## Inject headers for HTTP sub-agents

```python
config_list = TheseusAutoGenMiddleware.wrap_config_list(config_list, wrapper)
```

Injects `X-CT-Kernel` and `X-CT-Parent-Provider` headers into every model config entry.
