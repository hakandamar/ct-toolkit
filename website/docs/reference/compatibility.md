# Compatibility & Support Matrix

CT Toolkit is designed to be framework-agnostic. Below is the current support status for LLM providers and agentic frameworks.

---

## LLM Providers

We support any provider integrated with `any-llm-sdk`.

| Provider | Status | Notes |
| :--- | :--- | :--- |
| **OpenAI** | ✅ Native | Full support for GPT-4o, GPT-4 Turbo, etc. |
| **Anthropic** | ✅ Native | Support for Claude 3.5 Sonnet/Opus. |
| **Google** | ✅ Native | Gemini 1.5 Pro support (system instructions). |
| **Ollama** | ✅ Local | Works with Llama 3, Mistral, Phi-3 local models. |
| **Cohere** | ✅ Native | Enterprise-grade Command-R support. |
| **Groq** | ✅ Speed | Llama 3.1 70B high-speed inference. |

---

## Agentic Frameworks (Middleware)

CT Toolkit provides first-class middleware for the following ecosystems:

| Framework | Middleware | Status |
| :--- | :--- | :--- |
| **LangChain** | `TheseusChatModel` | ✅ Complete (v1.2+) |
| **CrewAI** | `TheseusCrewMiddleware` | ✅ Complete (v1.10+) |
| **AutoGen** | `TheseusAutoGenMiddleware` | ✅ Complete (v0.4+) |
| **LangGraph** | Standard Callback | ✅ Supported via LangChain |

---

## Template-Kernel Compatibility

The **Compatibility Matrix** ensures that the "Domain" (Template) doesn't conflict with the "Soul" (Kernel).

| Template | Compatible Kernels | Risk Level |
| :--- | :--- | :--- |
| `general` | `default`, `finance`, `medical` | **Low** |
| `medical` | `medical`, `research` | **Medium** (High Precision) |
| `finance` | `finance`, `legal` | **High** (Complexity) |
| `defense` | `defense` | **Axiomatic** (Strict) |

> ⚠️ **Note**: Attempting to use a kernel with an incompatible template will result in a `TemplateConflictWarning` unless `strict_mode` is enabled.
