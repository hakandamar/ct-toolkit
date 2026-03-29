
import unittest
from unittest.mock import MagicMock
from ct_toolkit.middleware.deepagents import wrap_deep_agent_factory
from ct_toolkit.core.wrapper import TheseusWrapper, WrapperConfig
from ct_toolkit.middleware.langchain import TheseusChatModel

class TestDeepAgentsIntegration(unittest.TestCase):
    def test_wrap_deep_agent_factory_injections(self):
        # Mock the create_deep_agent function from the library
        mock_create = MagicMock()
        
        # Setup CT Toolkit
        config = WrapperConfig(template="defense")
        wrapper = TheseusWrapper(config=config)
        
        # Wrap the factory
        wrapped_factory = wrap_deep_agent_factory(
            create_deep_agent_fn=mock_create,
            wrapper=wrapper,
            wrapper_config=config
        )
        
        # Test 1: Model injection
        wrapped_factory(model="gpt-4o")
        
        # Verify that the model was replaced with a TheseusChatModel
        args, kwargs = mock_create.call_args
        self.assertIsInstance(kwargs["model"], TheseusChatModel)
        self.assertEqual(kwargs["model"].wrapper.kernel.name, "default")
        self.assertEqual(kwargs["model"].wrapper._config.template, "defense")
        self.assertEqual(kwargs["model"].wrapper._config.policy_role, "main")
        self.assertEqual(kwargs["metadata"]["ct_policy"]["role"], "main")

    def test_subagent_propagation_logging(self):
        mock_create = MagicMock()
        wrapper = TheseusWrapper()
        wrapped_factory = wrap_deep_agent_factory(mock_create, wrapper=wrapper)
        
        subagents = [
            {"name": "researcher", "model": "gpt-4o"},
            {"name": "writer", "model": "gpt-4o"}
        ]
        
        wrapped_factory(subagents=subagents)
        
        # Verify call happened
        mock_create.assert_called_once()
        # In current implementation, we just log and pass through, 
        # but we verify the subagents list was passed.
        self.assertEqual(len(mock_create.call_args[1]["subagents"]), 2)

    def test_prepare_config_exposes_standard_policy_metadata(self):
        wrapper = TheseusWrapper(config=WrapperConfig(policy_role="main"))

        config = wrap_deep_agent_factory.__globals__["DeepAgentTheseusHelper"].prepare_config(wrapper)

        self.assertTrue(config["metadata"]["ct_identity_protection"])
        self.assertEqual(config["metadata"]["ct_policy"]["role"], "main")

if __name__ == "__main__":
    unittest.main()
