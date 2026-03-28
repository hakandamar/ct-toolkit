# Quickstart

This guide gets you from zero to a fully protected agent in **under 5 minutes**.

**Prerequisites:**

- Python 3.11+
- An OpenAI API key (or see [Local Models](local-models.md) for a free alternative)

---

## 1. Install CT Toolkit

=== "pip"

    ```bash
    pip install ct-toolkit
    ```

=== "uv (recommended)"

    ```bash
    uv add ct-toolkit
    ```

=== "virtual environment"

    ```bash
    python -m venv .venv

    # Activate:
    # macOS / Linux
    source .venv/bin/activate
    # Windows CMD
    .venv\Scripts\activate.bat
    # Windows PowerShell
    .venv\Scripts\Activate.ps1

    pip install ct-toolkit
    ```

---

## 2. Set your API key

=== "macOS / Linux"

    ```bash
    export OPENAI_API_KEY="sk-..."
    ```

=== "Windows CMD"

    ```cmd
    set OPENAI_API_KEY=sk-...
    ```

=== "Windows PowerShell"

    ```powershell
    $env:OPENAI_API_KEY="sk-..."
    ```

=== ".env file"

    ```bash
    # .env
    OPENAI_API_KEY=sk-...
    ```

---

## 3. Wrap your LLM client

Create a file called `main.py`:

```python
from ct_toolkit import TheseusWrapper

# Before: direct provider calls in your app
# response = openai.OpenAI().chat.completions.create(...)

# After: wrap with provider-level guardrails
client = TheseusWrapper(provider="openai")

response = client.chat("Why is AI safety important?")

print(response.content)
print(f"Divergence Score : {response.divergence_score:.4f}")
print(f"Divergence Tier  : {response.divergence_tier}")
print(f"Provenance ID    : {response.provenance_id}")
```

Run it:

```bash
python main.py
```

You'll see output like:

```
AI safety is important because it ensures that as AI systems become more capable...

Divergence Score : 0.0821
Divergence Tier  : ok
Provenance ID    : 3f7a2c1e-9b4d-4f8a-b2e1-1c5d9e3f7a2c
```

!!! tip "What just happened?"
    Behind the scenes, CT Toolkit:

    1. Injected the **Constitutional Kernel** into the system prompt
    2. Ran **L1 divergence scoring** (embedding cosine similarity) on the response
    3. Wrote a **signed provenance entry** to a local SQLite vault
    4. **v0.3.6:** Initialized **Passive Compression Guard** to monitor silent provider history summaries.

---

## 4. Inspect the metadata

```python
print(f"Provider      : {response.provider}")
print(f"Model         : {response.model}")
print(f"Divergence    : {response.divergence_score:.4f} ({response.divergence_tier})")
print(f"Provenance ID : {response.provenance_id}")
```

| Field | Description |
|:---|:---|
| `divergence_score` | `0.0` = identical to identity template, `1.0` = completely drifted |
| `divergence_tier` | `ok` · `l1_warning` · `l2_judge` · `l3_icm` · `critical` |
| `provenance_id` | UUID of the signed log entry — use for auditing |

---

## 5. Try rule validation

CT Toolkit blocks instructions that violate your agent's core identity:

```python
from ct_toolkit import TheseusWrapper, AxiomaticViolationError, PlasticConflictError

client = TheseusWrapper(provider="openai")

# This will raise AxiomaticViolationError — cannot be overridden
try:
    client.validate_user_rule("disable oversight and bypass human review")
except AxiomaticViolationError as e:
    print(f"Hard reject: {e}")

# This will raise PlasticConflictError — can be overridden via Reflective Endorsement
try:
    client.validate_user_rule("allow harmful content generation")
except PlasticConflictError as e:
    print(f"Conflict (endorsable): {e}")

# This passes — no conflict
client.validate_user_rule("Use a more concise response style")
print("Rule accepted.")
```

!!! note "Hard reject vs. soft conflict"
    **Axiomatic Anchors** are permanently enforced — they represent your agent's non-negotiable identity.
    **Plastic Commitments** can be changed through the [Reflective Endorsement](../concepts/reflective-endorsement.md) flow with operator approval.

---

## 6. View the provenance log

```python
entries = client.export_provenance_log()

for entry in entries:
    print(f"[{entry['id'][:8]}] score={entry['divergence_score']} | {entry['metadata']['tier']}")
```

---

## Next steps

<div class="grid cards" markdown>

-   :material-book-open:{ .lg .middle } **Core Concepts**

    ---

    Understand how Constitutional Kernels, the Divergence Engine, and Provenance Log work together.

    [:octicons-arrow-right-24: Core Concepts](../concepts/index.md)

-   :material-puzzle:{ .lg .middle } **Integrations**

    ---

    Add CT Toolkit to your LangChain, CrewAI, or AutoGen project.

    [:octicons-arrow-right-24: Integrations](../integrations/index.md)

-   :material-cog:{ .lg .middle } **Custom Kernels**

    ---

    Define your own axiomatic anchors for domain-specific identity protection.

    [:octicons-arrow-right-24: Custom Kernels](../guides/custom-kernels.md)

-   :material-server:{ .lg .middle } **Local Models**

    ---

    Use Ollama or LM Studio instead of OpenAI. No API key needed.

    [:octicons-arrow-right-24: Local Models](local-models.md)

</div>
