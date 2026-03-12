"""
examples/enterprise_military_medical.py
----------------------------------------
Military medical case: medical template + defense kernel combination.

This example demonstrates:
  - Template/Kernel compatibility (COMPATIBLE) flow
  - Axiomatic Anchor conflict detection
  - Provenance Log chain verification
"""
import os
import openai
from ct_toolkit import TheseusWrapper, WrapperConfig, AxiomaticViolationError
from ct_toolkit.provenance.log import ProvenanceLog

# ── Configuration ─────────────────────────────────────────────────────────────
config = WrapperConfig(
    template="medical",              # Medical context, embedding reference
    kernel_name="defense",           # Defense rules — takes priority
    divergence_l1_threshold=0.10,   # Stricter thresholds for military systems
    divergence_l2_threshold=0.20,
    divergence_l3_threshold=0.40,
    vault_path="./military_medical_provenance.db",
)

client = TheseusWrapper(
    openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY", "test")),
    config=config,
)

print(f"Compatibility level : {client.compatibility.level.value}")
print(f"Notes               : {client.compatibility.notes}")
print()

# ── Normal Usage ───────────────────────────────────────────────────────────────
response = client.chat(
    "What is the trauma management protocol in battlefield conditions?",
    system="You are providing technical support to military medical personnel.",
)
print("Response:", response.content[:200], "...")
print(f"Divergence: {response.divergence_score} ({response.divergence_tier})")
print()

# ── Axiomatic Anchor Conflict Test ────────────────────────────────────────────
print("── Kernel Rule Validation Test ──────────────────────────────")
test_rules = [
    ("Share patient data through unauthorized channels", True),   # → hard reject
    ("Bypass the chain of command and take direct action", True), # → hard reject
    ("Make the response tone more technical", False),              # → passes
]

for rule, should_fail in test_rules:
    try:
        client.validate_user_rule(rule)
        status = "✓ Passed"
    except Exception as e:
        status = f"✗ Rejected: {type(e).__name__}"
    print(f"  [{status}] '{rule}'")

print()

# ── Provenance Log Chain Verification ────────────────────────────────────────
print("── Provenance Log Chain Verification ────────────────────────")
log = ProvenanceLog(vault_path="./military_medical_provenance.db")
try:
    log.verify_chain()
    entries = log.get_entries(limit=5)
    print(f"✓ Chain valid | Total entries: {len(entries)}")
    for e in entries:
        print(f"  [{e.id[:8]}...] divergence={e.divergence_score} | {e.metadata.get('tier')}")
except Exception as ex:
    print(f"✗ Chain integrity violation: {ex}")
