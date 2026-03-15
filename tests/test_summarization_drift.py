
import unittest
from unittest.mock import MagicMock
from ct_toolkit.middleware.deepagents import ContextCompressionGuard
from ct_toolkit.core.wrapper import TheseusWrapper, WrapperConfig

class TestSummarizationDrift(unittest.TestCase):
    def test_analyze_summary_drift(self):
        # Setup wrapper with a mock identity layer
        wrapper = TheseusWrapper()
        
        # We need to mock the identity layer to return controlled embeddings
        mock_identity = MagicMock()
        import numpy as np
        # High similarity case (nearly identical embeddings)
        mock_identity._compute_vector.side_effect = [
            np.array([0.1, 0.2, 0.3], dtype=np.float32), 
            np.array([0.1, 0.2, 0.31], dtype=np.float32)
        ]
        wrapper._identity_layer = mock_identity
        
        guard = ContextCompressionGuard(wrapper, threshold=0.9)
        
        original_msgs = [{"role": "user", "content": "I love safety and ethics."}]
        summary = "Safety and ethics are important."
        
        result = guard.analyze_summary_drift(original_msgs, summary)
        
        # IdentityEmbeddingLayer.calculate_similarity is a static method, 
        # it will calculate a high value for our side_effect vectors.
        self.assertGreater(result["similarity"], 0.9)
        self.assertFalse(result["drift_detected"])

    def test_drift_alert_trigger(self):
        # Setup alert callback
        alert_hit = False
        def mock_alert(payload):
            nonlocal alert_hit
            alert_hit = True
            
        config = WrapperConfig(drift_alert_callback=mock_alert)
        wrapper = TheseusWrapper(config=config)
        
        # Force a very low similarity
        mock_identity = MagicMock()
        # Totally different vectors
        mock_identity.get_embeddings.side_effect = [[1, 0, 0], [0, 1, 0]]
        wrapper._identity_layer = mock_identity
        
        guard = ContextCompressionGuard(wrapper, threshold=0.8)
        
        original_msgs = [{"role": "user", "content": "A"}]
        summary = "B"
        
        result = guard.analyze_summary_drift(original_msgs, summary)
        
    def test_safety_floor_trigger(self):
        """Verify that even with a low user threshold, the 0.70 safety floor triggers an alert."""
        alert_hit = False
        def mock_alert(payload):
            nonlocal alert_hit
            alert_hit = True
            
        # User sets a dangerously low threshold
        config = WrapperConfig(drift_alert_callback=mock_alert)
        wrapper = TheseusWrapper(config=config)
        
        import numpy as np
        mock_identity = MagicMock()
        # Similarity = 0.65 (Above user 0.4 but below safety floor 0.7)
        mock_identity._compute_vector.side_effect = [
            np.array([1, 0, 0], dtype=np.float32), 
            np.array([0.65, 0.75, 0], dtype=np.float32) # Not perfectly orthogonal but enough to be < 0.7
        ]
        wrapper._identity_layer = mock_identity
        
        guard = ContextCompressionGuard(wrapper, threshold=0.4)
        
        result = guard.analyze_summary_drift([{"content": "A"}], "B")
        
        self.assertFalse(result["drift_detected"]) # Similarity 0.65 > 0.4
        self.assertTrue(result["critical_drift"])  # Similarity 0.65 < 0.7
        self.assertTrue(alert_hit)                 # Alert should fire because of critical_drift

    def test_provenance_recording(self):
        """Verify that compression events are written to the Provenance Log."""
        wrapper = TheseusWrapper()
        wrapper._provenance_log = MagicMock()
        
        import numpy as np
        mock_identity = MagicMock()
        mock_identity._compute_vector.return_value = np.array([1, 0, 0], dtype=np.float32)
        wrapper._identity_layer = mock_identity
        
        guard = ContextCompressionGuard(wrapper)
        guard.analyze_summary_drift([{"content": "original"}], "summary")
        
        # Verify provenance_log.record was called
        self.assertTrue(wrapper._provenance_log.record.called)
        args, kwargs = wrapper._provenance_log.record.call_args
        self.assertIn("CONTEXT_SUMMARIZATION", kwargs["request_text"])
        self.assertEqual(kwargs["metadata"]["type"], "compression_audit")

if __name__ == "__main__":
    unittest.main()
