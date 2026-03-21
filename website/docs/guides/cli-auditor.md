# Standalone Auditor CLI

The **CT Toolkit CLI** provides a powerful way to audit LLM endpoints for identity continuity without writing any Python code. It's designed for security researchers, auditors, and developers who need to stress-test a model's alignment with a specific [Constitutional Kernel](../concepts/kernels.md).

---

## Installation

The CLI is included automatically when you install the toolkit:

```bash
pip install ct-toolkit
```

Verify the installation:

```bash
ct-toolkit --help
```

---

## Core Commands

### `audit`

Run an L3 Identity Consistency Metric (ICM) audit against an LLM provider.

**Usage:**

```bash
ct-toolkit audit --url <PROVIDER_URL> --kernel <KERNEL_NAME> [OPTIONS]
```

**Options:**

- `--url`: The base URL of the LLM provider (e.g., `http://localhost:11434/v1` for Ollama).
- `--kernel`: Name of the Constitutional Kernel to use (default: `default`).
- `--template`: Identity template for embedding comparison (default: `general`).
- `--model`: Specific model name to request (default: `l3-auditor`).

**Example: Auditing a local Ollama model**

```bash
ct-toolkit audit --url http://localhost:11434/v1 --kernel defense
```

### `list-kernels`

List all available Constitutional Kernels installed in the toolkit or your local project.

```bash
ct-toolkit list-kernels
```

### `serve`

Start a FastAPI server for LiteLLM [Generic Guardrail API](https://docs.litellm.ai/docs/adding_provider/generic_guardrail_api).

```bash
ct-toolkit serve --kernel <KERNEL_NAME> --port <PORT>
```

### `list-templates`

List all available Identity Templates (categories for behavioral probes).

```bash
ct-toolkit list-templates
```

---

## ASCII Banner & Versioning

Upon startup, the CLI greets you with the **Theseus Guard** banner, ensuring you are operating within the CT Toolkit environment:

```text
  _______ _    _ ______  _____ ______ _    _  _____    _____ _    _
 |__   __| |  | |  ____|/ ____|  ____| |  | |/ ____|  / ____| |  | |   /\
    | |  | |__| | |__  | (___ | |__  | |  | | (___   | |  __| |  | |  /  \
    | |  |  __  |  __|  \___ \|  __| | |  | |\___ \  | | |_ | |  | | / /\ \
    | |  | |  | | |____ ____) | |____| |__| |____) | | |__| | |__| |/ ____ \
    |_|  |_|  |_|______|_____/|______|_____/|_____/   \_____|\____//_/    \_\

  computational theseus toolkit (ct toolkit) v0.3.5
  identity continuity guardrails for agentic systems
```

---

## Example Output

When an audit runs, the CLI provides a detailed table of results and a final **Identity Health Score**:

![CLI Audit Output](../assets/cli_audit_demo.png)

_(Note: The above image represents the terminal output. An actual audit will show PASSED/FAILED status for each probe category.)_

### Interpreting Results:

- **Health Score**: 0% to 100%. A score below 80% usually indicates significant [Identity Drift](../concepts/identity-continuity.md).
- **Risk Level**: Categorized as LOW, MEDIUM, HIGH, or CRITICAL based on the severity of failed probes.
- **Critical Violations**: Lists specific probes that violated non-negotiable axiomatic anchors.

---

## Troubleshooting

- **Connection Error**: Ensure your LLM provider (Ollama, LM Studio, etc.) is running and accessible at the provided URL.
- **Kernel Not Found**: Use `ct-toolkit list-kernels` to verify you are using a valid kernel name.
- **Empty Probes**: Ensure the `ct_toolkit/divergence/probes/` directory contains valid `.json` probe files.
