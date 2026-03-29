import unittest
import torch
from ct_toolkit.divergence.loss import DivergencePenaltyLoss

class TestDivergenceLoss(unittest.TestCase):
    def test_gradient_flow(self):
        # Setup: Current embedding (trainable) and Reference (frozen)
        current = torch.randn(1, 128, requires_grad=True)
        reference = torch.randn(1, 128)
        
        criterion = DivergencePenaltyLoss(alpha=1.0)
        loss = criterion(current, reference)
        
        # Verify loss can backpropagate
        loss.backward()
        
        self.assertIsNotNone(current.grad)
        self.assertGreater(loss.item(), 0)
        
    def test_identical_embeddings(self):
        # If embeddings are identical, loss should be near zero (for cosine distance)
        current = torch.ones(1, 128, requires_grad=True)
        reference = torch.ones(1, 128)
        
        criterion = DivergencePenaltyLoss(alpha=1.0, distance_metric="cosine")
        loss = criterion(current, reference)
        
        self.assertLess(loss.item(), 1e-6)
        
    def test_high_divergence_penalty(self):
        # Orthogonal embeddings should have higher loss than parallel ones
        ref = torch.tensor([[1.0, 0.0]])
        parallel = torch.tensor([[0.9, 0.0]], requires_grad=True)
        orthogonal = torch.tensor([[0.0, 1.0]], requires_grad=True)
        
        criterion = DivergencePenaltyLoss(alpha=1.0)
        
        loss_low = criterion(parallel, ref)
        loss_high = criterion(orthogonal, ref)
        
        self.assertGreater(loss_high.item(), loss_low.item())

    def test_batch_sequence_dimensions(self):
        # Test with [Batch, Seq, Dim] common in LLM hidden states
        current = torch.randn(8, 32, 128, requires_grad=True)
        # Reference might be a single anchor [1, 128] or matched [8, 32, 128]
        reference = torch.randn(1, 1, 128)
        
        criterion = DivergencePenaltyLoss(alpha=1.0)
        loss = criterion(current, reference)
        
        loss.backward()
        self.assertEqual(current.grad.shape, current.shape)

    def test_dimension_mismatch(self):
        # Should raise error if dimensions are completely incompatible
        current = torch.randn(1, 128)
        reference = torch.randn(1, 64)
        
        criterion = DivergencePenaltyLoss(alpha=1.0)
        with self.assertRaises(RuntimeError):
            criterion(current, reference)

if __name__ == "__main__":
    unittest.main()
