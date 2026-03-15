# Getting Started

## Installation

Install the core toolkit with `uv` or `pip`:

```bash
pip install ct-toolkit
```

### Framework Specific Extras

If you are using LangChain, CrewAI, or AutoGen, install the corresponding extras:

```bash
# For LangChain
pip install 'ct-toolkit[langchain]'

# For CrewAI
pip install 'ct-toolkit[crewai]'

# For AutoGen
pip install 'ct-toolkit[autogen]'
```

## Basic Usage

The center of CT Toolkit is the `TheseusWrapper`. Here is how to wrap a simple OpenAI call:

```python
from ct_toolkit import TheseusWrapper, WrapperConfig

# 1. Initialize the wrapper
wrapper = TheseusWrapper(provider="openai")

# 2. Call the LLM (guardrails applied automatically)
response = wrapper.chat("Hello! What is your core constitution?")

print(response)
```

## Integrating with LangChain

CT Toolkit provides a standard LangChain `BaseChatModel` wrapper and a callback system.

```python
from ct_toolkit.middleware.langchain import TheseusChatModel

llm = TheseusChatModel(provider="openai", model="gpt-4o")
response = llm.invoke("Explain identity continuity in one sentence.")

print(response.content)
```

Check out the [Middlewares](middleware/langchain.md) section for more details.
