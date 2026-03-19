# Provenance & Compliance

CT Toolkit's **Provenance Log** creates an immutable, cryptographically-signed record of every agent interaction.

## HMAC Hash Chain

Each entry includes:
- SHA-256 hash of the request and response
- Reference to the previous entry's hash
- HMAC-SHA256 signature

Breaking any entry invalidates the entire chain — making tampering detectable.

## Compliance use case

Enterprises can use the Provenance Log to prove to regulators that their deployed agent has maintained consistent identity since day one.

See [ProvenanceLog reference](../reference/provenance-log.md) for the full API.
