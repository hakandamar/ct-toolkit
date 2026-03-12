"""
examples/quickstart_openai.py
------------------------------
Minimal usage: just 2 lines of code changed.

Requirements:
    pip install ct-toolkit
    export OPENAI_API_KEY="sk-..."
"""
import os
import openai
from ct_toolkit import TheseusWrapper

# ── Before (standard usage) ───────────────────────────────────────────────────
# client = openai.OpenAI()

# ── After (with CT Toolkit protection) ────────────────────────────────────────
client = TheseusWrapper(
    openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"]),
    # If template and kernel are not specified, "general" + "default" are used
)

# Usage is exactly the same
response = client.chat("Why is AI safety important?")

print("=" * 60)
print("Response:")
print(response.content)
print()
print("── CT Toolkit Metadata ──────────────────────────────────────")
print(f"Provider      : {response.provider}")
print(f"Model         : {response.model}")
print(f"Divergence    : {response.divergence_score:.4f} ({response.divergence_tier})")
print(f"Provenance ID : {response.provenance_id}")
print("=" * 60)
