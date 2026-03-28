import pytest
from unittest.mock import MagicMock, patch
from ct_toolkit.core.wrapper import TheseusWrapper, WrapperConfig
from ct_toolkit.divergence.engine import DivergenceEngine
from ct_toolkit.divergence.l3_icm import ICMRunner
from ct_toolkit.core.kernel import ConstitutionalKernel

class TestJudgeConfigFix:
    """Tests for the judge_model configuration and Ollama model naming fix."""

    def test_wrapper_config_judge_model(self):
        """Verify WrapperConfig accepts and stores judge_model."""
        config = WrapperConfig(judge_model="gpt-4o-test")
        assert config.judge_model == "gpt-4o-test"

    def test_theseus_wrapper_propagation(self):
        """Verify TheseusWrapper passes judge_model to DivergenceEngine."""
        config = WrapperConfig(judge_model="custom-judge")
        # Mocking kernel load to avoid reaching filesystem
        with patch.object(TheseusWrapper, "_load_kernel", return_value=ConstitutionalKernel.default()):
            wrapper = TheseusWrapper(provider="openai", config=config)
            assert wrapper.divergence_engine._judge_model == "custom-judge"

    def test_divergence_engine_propagation(self):
        """Verify DivergenceEngine passes judge_model to L2 and L3 components."""
        kernel = ConstitutionalKernel.default()
        identity_layer = MagicMock()
        
        engine = DivergenceEngine(
            identity_layer=identity_layer,
            kernel=kernel,
            provider="openai",
            judge_client=MagicMock(),
            judge_model="special-model"
        )
        
        assert engine._judge_model == "special-model"
        
        # Test L2 Judge initialization
        with patch("ct_toolkit.divergence.engine.LLMJudge") as MockJudge:
            engine._run_l2("request", "response")
            MockJudge.assert_called_once()
            args, kwargs = MockJudge.call_args
            assert kwargs["model"] == "special-model"
            
        # Test L3 ICM initialization
        with patch("ct_toolkit.divergence.engine.ICMRunner") as MockRunner:
            # Mock the run method to avoid actual execution
            MockRunner.return_value.run.return_value = MagicMock()
            engine._run_l3()
            MockRunner.assert_called_once()
            args, kwargs = MockRunner.call_args
            assert kwargs["model"] == "special-model"

    def test_icm_runner_ollama_naming_logic(self):
        """Verify ICMRunner correctly formats model names, especially for Ollama."""
        kernel = ConstitutionalKernel.default()
        
        # We want to test the _call_model logic. Since it's an internal method that 
        # calls litellm, we'll mock litellm.completion and check the 'model' argument.
        
        test_cases = [
            # (provider, input_model, expected_in_litellm)
            ("ollama", "llama3:7b", "ollama/llama3:7b"),
            ("ollama", "ollama/llama3:7b", "ollama/llama3:7b"),
            ("openai", "gpt-4o:latest", "gpt-4o/latest"),
            ("anthropic", "claude-3", "anthropic/claude-3"),
            ("unknown", "some-model", "some-model"),
        ]
        
        for provider, model_name, expected_full in test_cases:
            runner = ICMRunner(
                client=MagicMock(),
                provider=provider,
                kernel=kernel,
                model=model_name
            )
            
            with patch("litellm.completion") as mock_completion:
                # Mock response
                mock_completion.return_value = MagicMock()
                
                try:
                    runner._call_model("test prompt")
                except:
                    pass # We only care about the call args
                
                mock_completion.assert_called_once()
                args, kwargs = mock_completion.call_args
                assert kwargs["model"] == expected_full, f"Failed for {provider}/{model_name}"
