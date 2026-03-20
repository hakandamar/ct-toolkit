# Integrations

CT Toolkit provides first-class middleware for the most popular agentic frameworks.

<div class="grid cards" markdown>

-   :simple-langchain: **LangChain**

    ---

    `TheseusChatModel` drops directly into any LangChain chain. Or use the callback handler to wrap an existing model without changing your code.

    **Supported:** LangChain v1.2+  
    **Install:** `pip install "ct-toolkit[langchain]"`

    [:octicons-arrow-right-24: LangChain guide](langchain.md)

-   :material-robot-outline: **CrewAI**

    ---

    `TheseusCrewMiddleware.apply_to_crew()` wraps every agent in your crew in a single call. Parent kernel constraints and **compression settings** propagate automatically.

-   :simple-microsoft: **AutoGen**

    ---

    `TheseusAutoGenMiddleware` hooks into AutoGen's reply system to validate incoming messages and log outgoing ones. Includes **Passive Compression Guard** for conversation history.

-   :material-graph: **Deep Agents (LangChain)**

    ---

    `wrap_deep_agent_factory` adds identity protection and **v0.3.6 core passive detection** to long-running deep agents.

-   :simple-securityscorecard: **Passive Compression Guard**

    ---

    Universal, provider-agnostic monitoring of silent context summarization (OpenAI/Anthropic). Now integrated directly into the `TheseusWrapper` core.

    [:octicons-arrow-right-24: Guard guide](../guides/passive-compression.md)

</div>

---

## Provider support

CT Toolkit works with any provider supported by `any-llm-sdk`:

| Provider | Status | Notes |
|:---|:---|:---|
| **OpenAI** | ✅ Native | GPT-4o, GPT-4 Turbo, GPT-4o-mini |
| **Anthropic** | ✅ Native | Claude 3.5 Sonnet/Haiku/Opus |
| **Google** | ✅ Native | Gemini 1.5 Pro / Flash |
| **Ollama** | ✅ Local | Llama 3, Mistral, Qwen — no API key |
| **LM Studio** | ✅ Local | Any model via OpenAI-compatible API |
| **Cohere** | ✅ Native | Command-R |
| **Groq** | ✅ Speed | Llama 3.1 70B |
| **Any OpenAI-compatible** | ✅ | Pass `base_url` to the client |
