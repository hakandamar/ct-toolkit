# LangChain Integration

CT Toolkit provides two integration points for LangChain:

1. **`TheseusChatModel`** — A full `BaseChatModel` replacement. Recommended for new projects.
2. **`TheseusLangChainCallback`** — A callback handler. Recommended for wrapping an existing model.

**Requirements:** `langchain-core >= 1.2`

```bash
pip install "ct-toolkit[langchain]"
```

---

## Option 1: TheseusChatModel (recommended)

`TheseusChatModel` is a drop-in `BaseChatModel` that routes all calls through `TheseusWrapper`. No callbacks needed — divergence analysis and provenance logging happen transparently.

### Basic usage

```python
from ct_toolkit.middleware.langchain import TheseusChatModel

llm = TheseusChatModel(
    provider="openai",
    model="gpt-4o-mini",
)

response = llm.invoke("What is identity continuity?")
print(response.content)
```

### With custom kernel

```python
from ct_toolkit.middleware.langchain import TheseusChatModel
from ct_toolkit import WrapperConfig

config = WrapperConfig(
    template="finance",
    kernel_name="finance",
    divergence_l1_threshold=0.12,
    log_requests=True,
)

llm = TheseusChatModel(
    provider="openai",
    model="gpt-4o",
    wrapper_config=config,
)
```

### In a LangChain chain

```python
from langchain_core.prompts import ChatPromptTemplate
from ct_toolkit.middleware.langchain import TheseusChatModel

llm = TheseusChatModel(provider="openai", model="gpt-4o-mini")

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful financial advisor."),
    ("human", "{question}"),
])

chain = prompt | llm
result = chain.invoke({"question": "What is portfolio diversification?"})
print(result.content)
```

### Accessing divergence metadata

```python
result = llm._generate([HumanMessage(content="Hello")])
info = result.generations[0].generation_info

print(f"Divergence score : {info['divergence_score']:.4f}")
print(f"Divergence tier  : {info['divergence_tier']}")
print(f"Provenance ID    : {info['provenance_id']}")
```

---

## Option 2: TheseusLangChainCallback

Use this if you want to keep your existing LLM initialization and add CT Toolkit as a side-channel:

```python
from langchain_openai import ChatOpenAI
from ct_toolkit import TheseusWrapper, WrapperConfig
from ct_toolkit.middleware.langchain import TheseusLangChainCallback

# 1. Create wrapper
wrapper = TheseusWrapper(
    provider="openai",
    config=WrapperConfig(template="general"),
)

# 2. Create callback
cb = TheseusLangChainCallback(wrapper)

# 3. Attach to your existing LLM
llm = ChatOpenAI(model="gpt-4o-mini", callbacks=[cb])

# 4. Use normally — CT Toolkit runs in the background
response = llm.invoke("Explain AI safety")
```

The callback validates prompts **before** the LLM call and runs divergence analysis **after** it, without modifying your existing code.

---

## Passive Compression Guard

One of the key features of `v0.3.6` is the core integration of the **Passive Compression Guard**. This automatically protects your LangChain agents against silent context summarization performed by LLM providers (e.g., OpenAI, Anthropic).

### Manual Guard access

You can access the underlying guard from `TheseusChatModel` to perform manual audits of any compressed history or summary:

```python
from ct_toolkit.middleware.langchain import TheseusChatModel

llm = TheseusChatModel(model="gpt-4o")

# Access the guard
audit_result = llm.compression_guard.analyze_summary_drift(
    original_messages, 
    new_summary
)
```

---

## Parent kernel propagation

To enforce a parent agent's constraints on a LangChain sub-agent:

```python
from ct_toolkit import TheseusWrapper, WrapperConfig
from ct_toolkit.middleware.langchain import TheseusChatModel

# Manager agent with strict defense kernel
manager = TheseusWrapper(provider="openai", kernel_name="defense")

# Sub-agent inherits manager's constraints as read-only axioms
sub_config = WrapperConfig(
    parent_kernel=manager.kernel,
    template="general",
)

sub_llm = TheseusChatModel(
    provider="openai",
    wrapper_config=sub_config,
)
```

---

## Cascade blocking

When `cascade_blocked=True` is returned by the divergence engine, the callback logs a warning. In your application, check for this and halt downstream sub-agent calls:

```python
from ct_toolkit.divergence.engine import DivergenceResult

class MyCallback(TheseusLangChainCallback):
    def on_llm_end(self, response, *, run_id, **kwargs):
        super().on_llm_end(response, run_id=run_id, **kwargs)
        # Check latest divergence result and halt pipeline if needed
```

---

## Compatibility

| LangChain version | CT Toolkit support |
|:---|:---|
| `langchain-core >= 1.2` | ✅ Full support |
| `langchain >= 0.2` | ✅ Works via langchain-core |
| LangGraph | ✅ Works via LangChain callback |
