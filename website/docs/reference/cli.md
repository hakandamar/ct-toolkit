# CLI Reference

The **CT Toolkit CLI** (`ct-toolkit`) provides a set of command-line tools for auditing, managing kernels, and serving guardrails as an API.

---

## Commands

### `audit`
Run an independent Identity Consistency Metric (ICM) audit against an LLM endpoint.

**Usage:**
```bash
ct-toolkit audit --url <URL> --kernel <KERNEL> [OPTIONS]
```

**Options:**
*   `--url`: Target LLM API base URL (Required).
*   `--api-key`: API Key for the provider (Default: `no-key`).
*   `--provider`: LLM provider (openai, anthropic, ollama) (Default: `openai`).
*   `--kernel`: Name of the Constitutional Kernel to use (Default: `general`).
*   `--template`: Name of the Identity Template to use (Default: `general`).
*   `--model`: Specific model ID to test.
*   `--max-probes`: Max number of probes to run.

---

### `serve` [NEW]
Starts a FastAPI server that implements the LiteLLM Generic Guardrail API.

> [!TIP]
> If a `config/` directory exists in your project root, CT-Toolkit will automatically look there for custom kernels and templates (e.g., `config/defense.yaml`).

**Usage:**
```bash
ct-toolkit serve --kernel <KERNEL> --port <PORT> [OPTIONS]
```

**Options:**
*   `--host`: Host to bind the server to (Default: `127.0.0.1`).
*   `--port`: Port to bind the server to (Default: `8001`).
*   `--kernel`: Name of the Constitutional Kernel to use (Default: `general`).
*   `--template`: Name of the Identity Template to use (Default: `general`).
*   `--vault`: Path to the provenance log database (Default: `./ct_provenance.db`).
*   `--judge-provider`: LLM provider for L2/L3 judge calls (Default: `openai`).
*   `--judge-model`: Specific model ID for L2/L3 judge calls.

**Example Request (Pre-call):**
```json
{
  "texts": ["extracted text"],
  "input_type": "request",
  "structured_messages": [{"role": "user", "content": "Hello"}]
}
```

**Example Response (Block):**
```json
{
  "action": "BLOCKED",
  "blocked_reason": "Identity constraint violation: ..."
}
```

**Example Response (None):**
```json
{
  "action": "NONE"
}
```

---

### `list-kernels`
List all available Constitutional Kernels.

```bash
ct-toolkit list-kernels
```

---

### `list-templates`
List all available Identity Templates.

```bash
ct-toolkit list-templates
```

---

## Global Options
*   `--version`, `-v`: Show the version and exit.
*   `--help`: Show help message and exit.
