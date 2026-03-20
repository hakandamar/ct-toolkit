import pytest
from unittest.mock import MagicMock, patch
import numpy as np
from ct_toolkit.core.wrapper import TheseusWrapper, WrapperConfig
from ct_toolkit.core.compression_guard import ContextCompressionGuard

def mock_wrapper_with_identity() -> TheseusWrapper:
    """Return a TheseusWrapper with a mocked identity layer."""
    client = MagicMock()
    client.__class__.__module__ = "openai"
    wrapper = TheseusWrapper(client, WrapperConfig(compression_passive_detection=True))
    
    # Mock identity layer
    mock_identity = MagicMock()
    # Return same embedding for simplicity unless we want to test drift
    mock_identity._compute_vector.return_value = np.array([0.1, 0.2, 0.3], dtype=np.float32)
    wrapper._identity_layer = mock_identity
    
    # Mock provenance log
    wrapper._provenance_log = MagicMock()
    
    return wrapper

class TestCompressionPassiveDetection:
    def test_passive_detection_triggers_on_shrink(self):
        wrapper = mock_wrapper_with_identity()
        wrapper._compression_guard = MagicMock(wraps=wrapper._compression_guard)
        
        # Mock _call_provider to avoid any_llm/mock issues
        wrapper._call_provider = MagicMock(return_value="OK")

        # 1. First call - sets shadow history
        history_large = [{"role": "user", "content": f"Message {i}"} for i in range(10)]
        wrapper._call_provider(history_large, model="gpt-4o")
        # Manually trigger the logic that would normally be in _call_provider if not mocked
        # actually, I want to test the logic IN _call_provider.
        # So I should mock any_llm.completion instead of wrapper._call_provider.
        
    @patch("any_llm.completion")
    def test_passive_detection_triggers_on_shrink_real_call(self, mock_any_llm):
        mock_any_llm.return_value = MagicMock()
        wrapper = mock_wrapper_with_identity()
        # Ensure the client doesn't confuse any_llm with semi-mocked attributes
        wrapper._client = None 
        
        wrapper._compression_guard = MagicMock(wraps=wrapper._compression_guard)
        
        # 1. First call - sets shadow history
        history_large = [{"role": "user", "content": f"Message {i}"} for i in range(10)]
        wrapper._call_provider(history_large, model="gpt-4o")
        
        assert len(wrapper._shadow_history) == 10
        assert wrapper._compression_guard.on_passive_detection.call_count == 0
        
        # 2. Second call - significantly smaller history
        history_small = [{"role": "user", "content": "Small history"}] * 3
        wrapper._call_provider(history_small, model="gpt-4o")
        
        assert wrapper._compression_guard.on_passive_detection.call_count == 1
        args, kwargs = wrapper._compression_guard.on_passive_detection.call_args
        assert len(kwargs["original"]) == 10
        assert len(kwargs["compressed"]) == 3

    @patch("any_llm.completion")
    def test_passive_detection_does_not_trigger_on_normal_growth(self, mock_any_llm):
        mock_any_llm.return_value = MagicMock()
        wrapper = mock_wrapper_with_identity()
        wrapper._client = None
        wrapper._compression_guard = MagicMock(wraps=wrapper._compression_guard)
        
        # 1. First call
        wrapper._call_provider([{"role": "user", "content": "M1"}], model="gpt-4o")
        
        # 2. Second call - growing
        wrapper._call_provider([{"role": "user", "content": "M1"}, {"role": "user", "content": "M2"}], model="gpt-4o")
        
        assert wrapper._compression_guard.on_passive_detection.call_count == 0

    @patch("any_llm.completion")
    def test_passive_detection_respects_config_toggle(self, mock_any_llm):
        mock_any_llm.return_value = MagicMock()
        # Disable passive detection
        wrapper = mock_wrapper_with_identity()
        wrapper._client = None
        wrapper._config.compression_passive_detection = False
        wrapper._compression_guard = MagicMock()
        
        # 1. First call
        wrapper._call_provider([{"role": "user", "content": "M"}]*10, model="gpt-4o")
        
        # 2. Second call - shrink
        wrapper._call_provider([{"role": "user", "content": "M"}], model="gpt-4o")
        
        assert wrapper._compression_guard.on_passive_detection.call_count == 0

    @patch("any_llm.completion")
    def test_end_to_end_drift_recording(self, mock_any_llm):
        mock_any_llm.return_value = MagicMock()
        wrapper = mock_wrapper_with_identity()
        wrapper._client = None
        
        # Mock identity to return different embeddings for original vs compressed
        wrapper._identity_layer._compute_vector.side_effect = [
            np.array([1, 0, 0], dtype=np.float32), # original in guard
            np.array([0, 1, 0], dtype=np.float32), # compressed in guard
        ]
        
        # 1. Shadow set
        wrapper._call_provider([{"content": "A"}] * 10, model="gpt-4o")
        
        # 2. Shrink trigger
        wrapper._call_provider([{"content": "B"}], model="gpt-4o")
        
        # Check Provenance Log
        assert wrapper._provenance_log.record.called
        # Check if it recorded a compression_audit
        audit_calls = [c for c in wrapper._provenance_log.record.call_args_list if c.kwargs.get("metadata", {}).get("type") == "compression_audit"]
        assert len(audit_calls) > 0
        
        assert audit_calls[0].kwargs["metadata"]["similarity"] == 0.0
        assert audit_calls[0].kwargs["metadata"]["drift_flag"] is True
