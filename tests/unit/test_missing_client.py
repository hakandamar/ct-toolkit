
import pytest
import os
from unittest.mock import MagicMock, patch
from ct_toolkit.core.wrapper import TheseusWrapper
from ct_toolkit.core.exceptions import MissingClientError

def test_missing_client_raises_error():
    """Verifies that TheseusWrapper.chat raises MissingClientError if no client or env key exists."""
    # Ensure environment keys are NOT set
    with patch.dict(os.environ, {}, clear=True):
        wrapper = TheseusWrapper(provider="openai")
        assert wrapper._client is None
        
        with pytest.raises(MissingClientError) as exc:
            wrapper.chat("Hello")
        
        assert "No client provided and no environment credentials found" in str(exc.value)

def test_missing_client_passes_with_env_key():
    """Verifies that TheseusWrapper.chat works if environment key is provided (mocked)."""
    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-dummy"}):
        wrapper = TheseusWrapper(provider="openai")
        
        # Mock litellm.completion to avoid real API call
        with patch("litellm.completion") as mock_comp:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Environment key works!"
            mock_response.model = "gpt-4o-mini"
            mock_comp.return_value = mock_response
            
            response = wrapper.chat("Hello")
            assert response.content == "Environment key works!"

def test_ollama_does_not_need_env_key():
    """Ollama is local-friendly and should not raise MissingClientError even without explicit credentials."""
    with patch.dict(os.environ, {}, clear=True):
        wrapper = TheseusWrapper(provider="ollama")
        
        with patch("litellm.completion") as mock_comp:
            mock_response = MagicMock()
            mock_response.model = "llama3"
            # LiteLLM standardised response for Ollama goes through .choices
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Ollama works!"
            mock_comp.return_value = mock_response
            
            response = wrapper.chat("Hello")
            assert response.content == "Ollama works!"
