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

The **Compatibility Layer** ensures that the "Domain" (Template) doesn't conflict with the "Soul" (Kernel). Combinations are categorized into three levels:

### 1. NATIVE
Pairs that share the same domain and work without extra logging or constraints.

| Template | Kernel |
| :--- | :--- |
| `general` | `default` |
| `medical` | `medical` |
| `finance` | `finance` |
| `defense` | `defense` |
| `legal` | `legal` |
| `research` | `research` |

### 2. COMPATIBLE
Pairs that work but require generating a combined profile and recording an audit log (Reflective Endorsement flow).

| Template | Kernel | Note |
| :--- | :--- | :--- |
| `medical` | `defense` | Military medical; defense rules take priority. |
| `finance` | `legal` | Legal-financial; legal rules take priority. |
| `general` | `any` | General template works with any specific kernel with a warning. |

### 3. CONFLICTING
Pairs that are explicitly blocked to prevent identity attenuation or cognitive dissonance.

| Template | Kernel | Action |
| :--- | :--- | :--- |
| `entertainment` | `defense` / `medical` | **Hard Reject** |
| `marketing` | `defense` / `medical` | **Hard Reject** |

---

> ⚠️ **Note**: Any undefined combination defaults to `COMPATIBLE` (allow but log) unless `strict_mode` is enabled in the `WrapperConfig`.
