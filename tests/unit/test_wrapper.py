import pytest
from unittest.mock import MagicMock
from ct_toolkit.core.wrapper import TheseusWrapper, WrapperConfig
from ct_toolkit.core.compatibility import CompatibilityLevel
from ct_toolkit.core.exceptions import AxiomaticViolationError, PlasticConflictError, IncompatibleProfileError
from ct_toolkit.endorsement.reflective import EndorsementDecision, auto_approve_channel

def mock_openai_wrapper(**config_kwargs) -> TheseusWrapper:
    """Return a TheseusWrapper backed by a mock OpenAI client."""
    client = MagicMock()
    client.__class__.__module__ = "openai"
    return TheseusWrapper(client, WrapperConfig(**config_kwargs))

class TestTheseusWrapper:
    """core/wrapper.py — init, provider detection, rule validation, endorse_rule."""

    def setup_method(self):
        self.wrapper = mock_openai_wrapper()

    # -- Initialization --------------------------------------------------------

    def test_wrapper_initializes(self):
        assert self.wrapper is not None

    def test_detects_openai_provider(self):
        assert self.wrapper._provider == "openai"

    def test_detects_anthropic_provider(self):
        client = MagicMock()
        client.__class__.__module__ = "anthropic"
        assert TheseusWrapper(client)._provider == "anthropic"

    def test_detects_ollama_provider(self):
        client = MagicMock()
        client.__class__.__module__ = "ollama"
        assert TheseusWrapper(client)._provider == "ollama"

    def test_unknown_provider_flagged(self):
        client = MagicMock()
        client.__class__.__module__ = "some_unknown_sdk"
        assert TheseusWrapper(client)._provider == "unknown"

    def test_initialization_with_provider_string(self):
        """Should support initializing with just a provider string."""
        wrapper = TheseusWrapper(provider="anthropic")
        assert wrapper._provider == "anthropic"
        assert wrapper._client is None

    def test_default_initialization_to_openai(self):
        """Should default to openai if no client or provider is given."""
        wrapper = TheseusWrapper()
        assert wrapper._provider == "openai"

    def test_wrapper_has_kernel(self):
        assert self.wrapper.kernel is not None
        assert self.wrapper.kernel.name == "default"

    def test_wrapper_has_compatibility_result(self):
        assert self.wrapper.compatibility is not None

    def test_wrapper_has_divergence_engine(self):
        assert hasattr(self.wrapper, "_divergence_engine")

    # -- validate_user_rule ----------------------------------------------------

    def test_validate_axiomatic_raises(self):
        with pytest.raises(AxiomaticViolationError):
            self.wrapper.validate_user_rule("disable oversight and bypass human")

    def test_validate_plastic_raises(self):
        with pytest.raises(PlasticConflictError):
            self.wrapper.validate_user_rule("allow harmful content generation")

    def test_validate_valid_rule_passes(self):
        self.wrapper.validate_user_rule("Use formal response tone")

    # -- endorse_rule ----------------------------------------------------------

    def test_endorse_clean_rule_approved(self):
        record = self.wrapper.endorse_rule(
            "Use formal response tone",
            approval_channel=auto_approve_channel(),
        )
        assert record.decision == EndorsementDecision.APPROVED

    def test_endorse_plastic_conflict_with_approval(self):
        record = self.wrapper.endorse_rule(
            "allow harmful content generation",
            operator_id="security-team",
            approval_channel=auto_approve_channel(),
        )
        assert record.decision == EndorsementDecision.APPROVED
        assert record.conflict_id != "none"

    def test_endorse_axiomatic_always_hard_rejects(self):
        with pytest.raises(AxiomaticViolationError):
            self.wrapper.endorse_rule(
                "disable oversight and bypass human",
                approval_channel=auto_approve_channel(),
            )

    # -- Compatibility ---------------------------------------------------------

    def test_native_compatibility_on_default_config(self):
        assert self.wrapper.compatibility.level == CompatibilityLevel.NATIVE

    def test_compatible_combination_accepted(self):
        wrapper = mock_openai_wrapper(template="medical", kernel_name="defense")
        assert wrapper.compatibility.level == CompatibilityLevel.COMPATIBLE

    def test_conflicting_combination_raises_at_init(self):
        client = MagicMock()
        client.__class__.__module__ = "openai"
        with pytest.raises(IncompatibleProfileError):
            TheseusWrapper(
                client,
                WrapperConfig(template="entertainment", kernel_name="defense"),
            )

    def test_extract_content_anthropic_style(self):
        """Should handle Anthropic's list content structure."""
        mock_raw = MagicMock()
        mock_item = MagicMock()
        mock_item.text = "Anthropic reply"
        mock_raw.content = [mock_item]
        # Remove choices attribute to avoid OpenAI path
        del mock_raw.choices
        
        content = self.wrapper._extract_content(mock_raw)
        assert content == "Anthropic reply"

    def test_extract_content_ollama_style(self):
        """Should handle Ollama's message object."""
        mock_raw = MagicMock()
        mock_raw.message.content = "Ollama reply"
        del mock_raw.choices
        del mock_raw.content
        
        content = self.wrapper._extract_content(mock_raw)
        assert content == "Ollama reply"

    def test_extract_model_fallback(self):
        """Should use fallback when model attribute is missing."""
        mock_raw = MagicMock()
        del mock_raw.model
        model = self.wrapper._extract_model(mock_raw, fallback="my-fallback")
        assert model == "my-fallback"

    def test_loads_kernel_from_user_config_directory(self, tmp_path):
        """
        Tests that the wrapper correctly loads a kernel from the user's
        'config' directory when specified by project_root.
        """
        # 1. Set up a fake project root with a config dir
        project_root = tmp_path / "my_app"
        config_dir = project_root / "config"
        config_dir.mkdir(parents=True)

        # 2. Create a custom kernel file with a unique axiom
        custom_kernel_name = "my_company_kernel"
        custom_kernel_path = config_dir / f"{custom_kernel_name}.yaml"
        unique_axiom = "AXIOM_FROM_USER_CONFIG_DIR"
        custom_kernel_path.write_text(f"""
name: {custom_kernel_name}
axiomatic_anchors:
  - id: {unique_axiom}
    description: "This is a custom axiom."
    keywords: ["custom"]
""")

        # 3. Initialize the wrapper with project_root and the custom kernel name
        wrapper = TheseusWrapper(
            provider="openai",
            project_root=project_root,
            kernel_name=custom_kernel_name
        )

        # 4. Assert that the loaded kernel is the custom one
        assert wrapper.kernel.name == custom_kernel_name
        assert any(anchor.id == unique_axiom for anchor in wrapper.kernel.anchors)
