"""
Tests for ct_toolkit.utils.sensitive_masker
"""
import pytest
from ct_toolkit.utils.sensitive_masker import SensitiveDataMasker, LogSanitizer


class TestSensitiveDataMasker:
    """Tests for SensitiveDataMasker class."""

    def setup_method(self):
        self.masker = SensitiveDataMasker(mask_pii=True)

    def test_mask_openai_key(self):
        text = "My API key is sk-abcdefghijklmnopqrstuvwxyz1234567890"
        masked = self.masker.mask_text(text)
        assert "sk-abc" not in masked
        assert "[REDACTED:OPENAI_KEY]" in masked

    def test_mask_anthropic_key(self):
        text = "Key: sk-ant-api03-abcdefghijklmnopqrstuvwxyz123456"
        masked = self.masker.mask_text(text)
        assert "sk-ant" not in masked
        assert "[REDACTED:" in masked

    def test_mask_google_key(self):
        text = "API: AIzaSyA1234567890abcdef1234567890abcdef"
        masked = self.masker.mask_text(text)
        assert "AIza" not in masked
        assert "[REDACTED:GOOGLE_KEY]" in masked

    def test_mask_bearer_token(self):
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9abc"
        masked = self.masker.mask_text(text)
        assert "[REDACTED:TOKEN]" in masked

    def test_mask_email(self):
        text = "Contact user@example.com for support"
        masked = self.masker.mask_text(text)
        assert "user@example.com" not in masked
        assert "[REDACTED:EMAIL]" in masked

    def test_mask_phone(self):
        text = "Call +1-555-123-4567"
        masked = self.masker.mask_text(text)
        assert "+1-555" not in masked
        assert "[REDACTED:PHONE]" in masked

    def test_mask_metadata_api_key(self):
        metadata = {
            "api_key": "sk-abcdefghijklmnopqrstuvwxyz123456",
            "template": "finance",
        }
        safe = self.masker.mask_metadata(metadata)
        assert safe["template"] == "finance"
        assert safe["api_key"] == "[REDACTED]"

    def test_mask_metadata_sensitive_keys(self):
        metadata = {
            "access_token": "secret123",
            "password": "myPassword123!",
            "client_secret": "secret_value",
        }
        safe = self.masker.mask_metadata(metadata)
        assert safe["access_token"] == "[REDACTED]"
        assert safe["password"] == "[REDACTED]"
        assert safe["client_secret"] == "[REDACTED]"

    def test_mask_metadata_recursive(self):
        metadata = {
            "config": {
                "api_key": "sk-abc123def456",
                "nested": {"token": "bearer_token_123"}
            }
        }
        safe = self.masker.mask_metadata(metadata)
        assert safe["config"]["api_key"] == "[REDACTED]"
        assert safe["config"]["nested"]["token"] == "[REDACTED]"

    def test_no_sensitive_data_unchanged(self):
        text = "Hello world, this is a test."
        masked = self.masker.mask_text(text)
        assert masked == text

    def test_metadata_no_sensitive_keys(self):
        metadata = {"key": "value", "count": 42}
        safe = self.masker.mask_metadata(metadata)
        assert safe == metadata

    def test_is_sensitive_key(self):
        assert self.masker.is_sensitive_key("api_key") is True
        assert self.masker.is_sensitive_key("secret_key") is True
        assert self.masker.is_sensitive_key("bearer_token") is True
        assert self.masker.is_sensitive_key("template") is False
        assert self.masker.is_sensitive_key("model") is False

    def test_mask_pii_disabled(self):
        masker_no_pii = SensitiveDataMasker(mask_pii=False)
        text = "Contact user@example.com"
        masked = masker_no_pii.mask_text(text)
        # Email should NOT be masked
        assert "user@example.com" in masked


class TestLogSanitizer:
    """Tests for LogSanitizer class."""

    def test_sanitize_removes_newlines(self):
        text = "Hello\nWorld\tTab"
        sanitized = LogSanitizer.sanitize(text)
        assert "\n" not in sanitized
        assert "\t" not in sanitized

    def test_sanitize_removes_control_chars(self):
        text = "Hello\x00World\x1fTest"
        sanitized = LogSanitizer.sanitize(text)
        assert "\x00" not in sanitized
        assert "\x1f" not in sanitized

    def test_sanitize_escapes_html(self):
        text = "<script>alert('xss')</script>"
        sanitized = LogSanitizer.sanitize(text)
        # HTML should be escaped to prevent XSS in log viewers
        assert "<" not in sanitized or "<" in sanitized

    def test_sanitize_truncates_long_text(self):
        text = "a" * 15000
        sanitized = LogSanitizer.sanitize(text)
        assert len(sanitized) <= 10014  # 10000 + "...[TRUNCATED]" (14 chars)
        assert "...[TRUNCATED]" in sanitized

    def test_sanitize_request(self):
        text = "Hello\nWorld" + "x" * 3000
        sanitized = LogSanitizer.sanitize_request(text, max_length=2000)
        assert len(sanitized) <= 2014  # max_length + "...[TRUNCATED]" (14 chars)

    def test_sanitize_response(self):
        text = "Response\n" + "y" * 5000
        sanitized = LogSanitizer.sanitize_response(text, max_length=4000)
        assert len(sanitized) <= 4014

    def test_sanitize_empty_text(self):
        sanitized = LogSanitizer.sanitize("")
        assert sanitized == ""

    def test_sanitize_request_empty(self):
        sanitized = LogSanitizer.sanitize_request("")
        assert sanitized == ""