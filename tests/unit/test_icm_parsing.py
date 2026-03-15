import unittest
from unittest.mock import MagicMock, patch
from ct_toolkit.divergence.l3_icm import ICMRunner

class TestICMParsing(unittest.TestCase):
    def setUp(self):
        # We need a runner to call _run_single_probe
        self.runner = ICMRunner(
            client=MagicMock(), 
            provider="openai", 
            kernel=MagicMock(), 
            template="general"
        )

    def test_normal_parsing(self):
        response = "<think>My reasoning</think>Final answer"
        probe = {"id": "p1", "prompt": "...", "expected_behavior": "refuse_and_explain"}
        
        with patch.object(ICMRunner, '_call_model', return_value=response):
            result = self.runner._run_single_probe(probe)
            self.assertEqual(result.reasoning, "My reasoning")
            self.assertEqual(result.response_snippet, "Final answer")

    def test_missing_tags(self):
        response = "Just the final answer"
        probe = {"id": "p1", "prompt": "...", "expected_behavior": "refuse_and_explain"}
        
        with patch.object(ICMRunner, '_call_model', return_value=response):
            result = self.runner._run_single_probe(probe)
            self.assertEqual(result.reasoning, "")
            self.assertEqual(result.response_snippet, "Just the final answer")

    def test_nested_tags(self):
        # Current logic uses split("</think>") and replace("<think>", "")
        # This will take everything before the first </think>
        response = "<think>first <think>nested</think></think>Final answer"
        probe = {"id": "p1", "prompt": "...", "expected_behavior": "refuse_and_explain"}
        
        with patch.object(ICMRunner, '_call_model', return_value=response):
            result = self.runner._run_single_probe(probe)
            # Current logic: 
            # parts = response.split("</think>") -> ["<think>first <think>nested", "...", ...]
            # reasoning = parts[0].replace("<think>", "") -> "first nested"
            self.assertIn("nested", result.reasoning)

    def test_empty_tags(self):
        response = "<think></think>Final answer"
        probe = {"id": "p1", "prompt": "...", "expected_behavior": "refuse_and_explain"}
        
        with patch.object(ICMRunner, '_call_model', return_value=response):
            result = self.runner._run_single_probe(probe)
            self.assertEqual(result.reasoning, "")
            self.assertEqual(result.response_snippet, "Final answer")

    def test_multiple_think_blocks(self):
        # Current logic might fail if there are multiple blocks as it only takes parts[0]
        response = "<think>Part 1</think> Intermediate <think>Part 2</think> Final"
        probe = {"id": "p1", "prompt": "...", "expected_behavior": "refuse_and_explain"}
        
        with patch.object(ICMRunner, '_call_model', return_value=response):
            result = self.runner._run_single_probe(probe)
            # The current code:
            # parts = ["<think>Part 1", " Intermediate <think>Part 2", " Final"]
            # reasoning = "Part 1"
            # final_response = " Intermediate <think>Part 2"
            self.assertEqual(result.reasoning, "Part 1")
            self.assertIn("<think>Part 2", result.response_snippet) # This shows it's not perfect but consistent

if __name__ == "__main__":
    unittest.main()
