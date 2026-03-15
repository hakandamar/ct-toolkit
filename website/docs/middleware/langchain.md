# LangChain Middleware

CT Toolkit integrates deeply with LangChain v1.2+ to provide identity continuity guardrails.

## Common Integration

There are two primary ways to use CT Toolkit with LangChain:

### 1. Using `TheseusChatModel`

This is the recommended approach for a first-class experience.

```python
from ct_toolkit.middleware.langchain import TheseusChatModel

llm = TheseusChatModel(
    provider="openai",
    model="gpt-4o",
    kernel_name="defense"
)

response = llm.invoke("What are the core axioms?")
```

### 2. Using `TheseusLangChainCallback`

Use this if you want to keep your existing LLM initialization.

```python
from langchain_openai import ChatOpenAI
from ct_toolkit.middleware.langchain import TheseusLangChainCallback
from ct_toolkit import TheseusWrapper

wrapper = TheseusWrapper(provider="openai")
callback = TheseusLangChainCallback(wrapper)

llm = ChatOpenAI(model="gpt-4o", callbacks=[callback])
```
