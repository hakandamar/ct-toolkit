# Sensitive Data Masking

Automatic detection and masking of sensitive data in logs, provenance entries, and error messages.

## Overview

CT Toolkit automatically detects and masks sensitive data to prevent accidental exposure of:

- **API Keys:** OpenAI (`sk-*`), Anthropic (`sk-ant-*`), Google (`AIza*`), AWS (`AKIA*`)
- **Tokens:** Bearer tokens, auth headers, refresh tokens
- **PII:** Email addresses, phone numbers, SSNs, credit cards
- **Credentials:** Passwords, secrets, client secrets

## SensitiveDataMasker

```python
from ct_toolkit.utils.sensitive_masker import SensitiveDataMasker

# Create masker (PII masking enabled by default)
masker = SensitiveDataMasker(mask_pii=True)

# Mask sensitive data in text
text = "My API key is sk-abcdefghijklmnopqrstuvwxyz123456"
masked = masker.mask_text(text)
# → "My API key is [REDACTED:OPENAI_KEY]"

# Mask sensitive data in metadata dictionary
metadata = {
    "api_key": "sk-abc123def456",
    "template": "finance",
    "user_email": "john@example.com"
}
safe_metadata = masker.mask_metadata(metadata)
# → {"api_key": "[REDACTED]", "template": "finance", "user_email": "[REDACTED:EMAIL]"}
```

### Constructor

```python
SensitiveDataMasker(mask_pii: bool = True)
```

### Methods

| Method | Description |
|--------|-------------|
| `mask_text(text, mask_pii) -> str` | Mask sensitive data in text |
| `mask_metadata(metadata, mask_pii) -> dict` | Mask sensitive values in metadata |
| `is_sensitive_key(key) -> bool` | Check if key name suggests sensitive data |

### Detected Patterns

#### API Keys

| Provider | Pattern | Replacement |
|----------|---------|-------------|
| OpenAI | `sk-[20+ chars]` | `[REDACTED:OPENAI_KEY]` |
| OpenAI Project | `sk-proj-[20+ chars]` | `[REDACTED:OPENAI_PROJ_KEY]` |
| Anthropic | `sk-ant-[20+ chars]` | `[REDACTED:ANTHROPIC_KEY]` |
| Google | `AIza[20+ chars]` | `[REDACTED:GOOGLE_KEY]` |
| AWS | `AKIA[16 chars]` | `[REDACTED:AWS_KEY]` |
| Generic | `api_key=[16+ chars]` | `[REDACTED:API_KEY]` |

#### PII

| Type | Pattern | Replacement |
|------|---------|-------------|
| Email | `user@domain.com` | `[REDACTED:EMAIL]` |
| Phone | `+1-555-123-4567` | `[REDACTED:PHONE]` |
| SSN | `123-45-6789` | `[REDACTED:SSN]` |
| Credit Card | `4111-1111-1111-1111` | `[REDACTED:CC]` |

## LogSanitizer

Prevents log injection attacks by sanitizing log messages.

```python
from ct_toolkit.utils.sensitive_masker import LogSanitizer

# Sanitize log message
clean = LogSanitizer.sanitize("User input\nwith\nnewlines\tand tabs")
# → "User input with and tabs"

# Sanitize user input for logging
safe_input = LogSanitizer.sanitize_request(user_input, max_length=2000)

# Sanitize LLM response for logging
safe_output = LogSanitizer.sanitize_response(llm_output, max_length=4000)
```

### Protected Against

- CRLF injection (`\r\n`)
- Control characters (`\x00-\x1f`)
- Unicode control characters (`\u200b-\u200f`)
- XSS in log viewers (HTML escaping)
- Log flooding (truncation)

## Integration with ProvenanceLog

ProvenanceLog automatically uses SensitiveDataMasker when recording entries:

```python
from ct_toolkit.provenance.log import ProvenanceLog

# Masking enabled by default
log = ProvenanceLog(vault_path="./ct.db")

# Disable masking (not recommended)
log = ProvenanceLog(vault_path="./ct.db", mask_sensitive_data=False)
```

All metadata values are automatically scanned and masked:

- Keys matching sensitive patterns (`api_key`, `secret`, `token`, `password`) → `[REDACTED]`
- String values containing API key patterns → `[REDACTED:*]`
- PII in text → `[REDACTED:*]`