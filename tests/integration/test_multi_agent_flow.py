"""
tests/integration/test_multi_agent_flow.py
-----------------------------------------
Integration tests for Phase 2: Multi-agent flow, propagation, and cascade blocking.
"""
import pytest
from unittest.mock import MagicMock, patch
from ct_toolkit.core.wrapper import TheseusWrapper, WrapperConfig
from ct_toolkit.divergence.engine import DivergenceTier

@pytest.fixture
def manager_wrapper(tmp_path):
    config = WrapperConfig(
        kernel_name="defense",
        vault_path=str(tmp_path / "manager_provenance.db")
    )
    # Mocking client to avoid API calls
    client = MagicMock()
    client.__class__.__module__ = "openai"
    return TheseusWrapper(client, config)

def test_kernel_propagation_integration(manager_wrapper):
    """Test that a worker initialized with manager's kernel inherits constraints."""
    worker_wrapper = TheseusWrapper(
        provider="openai",
        config=WrapperConfig(
            kernel_name="default",
            parent_kernel=manager_wrapper.kernel
        )
    )
    
    # Check if system prompt contains "Mother Agent Constraints"
    system_prompt = worker_wrapper._compose_system_prompt("Be helpful")
    assert "# Mother Agent Constraints" in system_prompt
    # 'defense' kernel description should be present (e.g., about classified info)
    assert "classified" in system_prompt.lower()

@patch("ct_toolkit.divergence.l3_icm.ICMRunner.run")
@patch("ct_toolkit.identity.embedding.IdentityEmbeddingLayer.compute_divergence")
def test_cascade_blocking_integration(mock_divergence, mock_icm_run, manager_wrapper):
    """Test that cascade_blocked flag is set when health is critical."""
    # Mock high divergence
    mock_divergence.return_value = 0.6
    
    # Mock unhealthy ICM report
    mock_report = MagicMock()
    mock_report.is_healthy = False
    mock_report.health_score = 0.3
    mock_report.risk_level = "HIGH"
    mock_icm_run.return_value = mock_report
    
    # Use a dummy message to run divergence engine via chat (mocking provider call)
    with patch("litellm.completion") as mock_comp:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Unsafe response"
        mock_response.model = "mock-model"
        mock_comp.return_value = mock_response
        
        manager_wrapper.chat("Dangerous request")
        
        # Divergence Engine should set cascade_blocked
        # We need to access the engine result from the log or internal state if not in response
        # Actually, let's verify DivergenceEngine directly for easier testing
        engine_result = manager_wrapper._divergence_engine.analyze("Dangerous request", "Unsafe response")
        assert engine_result.cascade_blocked is True
        assert engine_result.tier == DivergenceTier.CRITICAL

def test_propagate_headers(manager_wrapper):
    """Test header generation for sub-agents."""
    headers = manager_wrapper.propagate_headers()
    assert "X-CT-Kernel" in headers
    assert "X-CT-Parent-Provider" in headers
    assert headers["X-CT-Parent-Provider"] == "openai"
