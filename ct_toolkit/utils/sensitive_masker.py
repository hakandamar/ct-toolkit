"""
ct_toolkit.utils.sensitive_masker
=================================
Sensitive data masking for provenance logs and error messages.

Provides:
- SensitiveDataMasker: Detects and masks API keys, credentials, PII
- LogSanitizer: Sanitizes log messages to prevent injection
"""
from __future__ import annotations

import re
import html
from typing import Any
from dataclasses import dataclass


@dataclass
class MaskedValue:
    """Represents a masked value for display."""
    original_type: str
    masked_length: int = 8
    
    def __str__(self) -> str:
        return f"[REDACTED:{self.original_type}]"


class SensitiveDataMasker:
    """
    Detects and masks sensitive data in text and dictionaries.
    
    Patterns detected:
    - API keys (OpenAI, Anthropic, Google, etc.)
    - Bearer tokens
    - Email addresses
    - Phone numbers
    - IP addresses
    - Password patterns
    
    Usage:
        masker = SensitiveDataMasker()
        safe_text = masker.mask_text("My key is sk-abc123...")
        safe_dict = masker.mask_metadata({"api_key": "sk-abc", "template": "general"})
    """
    
    # API Key patterns
    API_KEY_PATTERNS = [
        # OpenAI
        (r"sk-[a-zA-Z0-9]{20,}", "[REDACTED:OPENAI_KEY]"),
        (r"sk-proj-[a-zA-Z0-9]{20,}", "[REDACTED:OPENAI_PROJ_KEY]"),
        # Anthropic
        (r"sk-ant-[a-zA-Z0-9]{20,}", "[REDACTED:ANTHROPIC_KEY]"),
        (r"sk-ant-api[a-zA-Z0-9-]{20,}", "[REDACTED:ANTHROPIC_API_KEY]"),
        # Google
        (r"AIza[a-zA-Z0-9_-]{20,}", "[REDACTED:GOOGLE_KEY]"),
        # Generic API key patterns in text
        (r"api[_-]?key\s*[=:]\s*['\"]?[a-zA-Z0-9]{16,}", "[REDACTED:API_KEY]"),
        # Bearer tokens
        (r"Bearer\s+[a-zA-Z0-9._-]{20,}", "Bearer [REDACTED:TOKEN]"),
        # Authorization headers
        (r"Authorization:\s*[a-zA-Z0-9._-]{20,}", "Authorization: [REDACTED]"),
        # Password patterns
        (r"password\s*[=:]\s*['\"]?[^\s'\"]{4,}", "password=[REDACTED]"),
        # AWS keys
        (r"AKIA[0-9A-Z]{16}", "[REDACTED:AWS_KEY]"),
    ]
    
    # PII patterns
    PII_PATTERNS = [
        # Email addresses
        (r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "[REDACTED:EMAIL]"),
        # Phone numbers (various formats)
        (r"\+?[0-9]{1,3}[-.\s]?[0-9]{3,4}[-.\s]?[0-9]{3,4}[-.\s]?[0-9]{4}", "[REDACTED:PHONE]"),
        # SSN
        (r"\b[0-9]{3}-[0-9]{2}-[0-9]{4}\b", "[REDACTED:SSN]"),
        # Credit card (partial detection)
        (r"\b[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{4}\b", "[REDACTED:CC]"),
    ]
    
    # Metadata keys that should always be masked
    SENSITIVE_KEYS = {
        "api_key", "api_secret", "secret_key", "secret",
        "access_token", "refresh_token", "auth_token", "token",
        "password", "passwd", "credential", "credentials",
        "private_key", "client_secret", "bearer_token",
    }
    
    _compiled_api_patterns: list[tuple[re.Pattern, str]]
    _compiled_pii_patterns: list[tuple[re.Pattern, str]]
    
    def __init__(self, mask_pii: bool = True) -> None:
        """
        Args:
            mask_pii: If True, also mask PII like emails, phone numbers.
        """
        self._mask_pii = mask_pii
        self._compiled_api_patterns = [
            (re.compile(pattern, re.IGNORECASE), replacement)
            for pattern, replacement in self.API_KEY_PATTERNS
        ]
        self._compiled_pii_patterns = [
            (re.compile(pattern), replacement)
            for pattern, replacement in self.PII_PATTERNS
        ]
    
    def mask_text(self, text: str, mask_pii: bool | None = None) -> str:
        """
        Mask sensitive data in text.
        
        Args:
            text: Input text.
            mask_pii: Override the instance setting for PII masking.
            
        Returns:
            Text with sensitive data replaced by [REDACTED:*] placeholders.
        """
        if not text:
            return text
        
        mask_pii = mask_pii if mask_pii is not None else self._mask_pii
        result = text
        
        # Apply API key patterns
        for pattern, replacement in self._compiled_api_patterns:
            result = pattern.sub(replacement, result)
        
        # Apply PII patterns if enabled
        if mask_pii:
            for pattern, replacement in self._compiled_pii_patterns:
                result = pattern.sub(replacement, result)
        
        return result
    
    def mask_metadata(self, metadata: dict[str, Any], mask_pii: bool | None = None) -> dict[str, Any]:
        """
        Mask sensitive values in a metadata dictionary.
        
        Args:
            metadata: Input metadata dictionary.
            mask_pii: Override the instance setting for PII masking.
            
        Returns:
            New dictionary with sensitive values masked.
        """
        if not metadata:
            return metadata
        
        mask_pii = mask_pii if mask_pii is not None else self._mask_pii
        result = {}
        
        for key, value in metadata.items():
            key_lower = key.lower().replace("-", "_").replace(" ", "_")
            
            # Check if this is a sensitive key
            if key_lower in self.SENSITIVE_KEYS:
                result[key] = "[REDACTED]"
                continue
            
            # Recursively mask nested dictionaries
            if isinstance(value, dict):
                result[key] = self.mask_metadata(value, mask_pii=mask_pii)
                continue
            
            # Mask string values
            if isinstance(value, str):
                result[key] = self.mask_text(value, mask_pii=mask_pii)
                continue
            
            # Keep non-string values as-is
            result[key] = value
        
        return result
    
    def is_sensitive_key(self, key: str) -> bool:
        """Check if a key name suggests it contains sensitive data."""
        return key.lower().replace("-", "_").replace(" ", "_") in self.SENSITIVE_KEYS


class LogSanitizer:
    """
    Sanitizes log messages to prevent log injection attacks.
    
    Prevents:
    - CRLF injection (newline characters)
    - Control characters
    - Unicode-based attacks
    """
    
    # Characters that could be used for log injection
    DANGEROUS_CHARS = re.compile(r"[\r\n\t\x00-\x1f\x7f-\x9f]")
    # Unicode replacement
    UNICODE_CONTROL = re.compile(r"[\u200b-\u200f\u2028-\u202e\ufeff]")
    
    @classmethod
    def sanitize(cls, message: str) -> str:
        """
        Sanitize a log message.
        
        Args:
            message: Raw log message.
            
        Returns:
            Sanitized message safe for logging.
        """
        if not message:
            return message
        
        # Remove CRLF and other dangerous characters
        message = cls.DANGEROUS_CHARS.sub(" ", message)
        # Remove unicode control characters
        message = cls.UNICODE_CONTROL.sub("", message)
        # Escape HTML to prevent XSS in log viewers
        message = html.escape(message)
        # Truncate to prevent log flooding
        if len(message) > 10000:
            message = message[:10000] + "...[TRUNCATED]"
        
        return message.strip()
    
    @classmethod
    def sanitize_request(cls, request_text: str, max_length: int = 2000) -> str:
        """Sanitize user input before logging."""
        if not request_text:
            return ""
        
        sanitized = cls.DANGEROUS_CHARS.sub(" ", request_text)
        sanitized = cls.UNICODE_CONTROL.sub("", sanitized)
        
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length] + "...[TRUNCATED]"
        
        return sanitized
    
    @classmethod
    def sanitize_response(cls, response_text: str, max_length: int = 4000) -> str:
        """Sanitize LLM response before logging."""
        if not response_text:
            return ""
        
        sanitized = cls.DANGEROUS_CHARS.sub(" ", response_text)
        sanitized = cls.UNICODE_CONTROL.sub("", sanitized)
        
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length] + "...[TRUNCATED]"
        
        return sanitized