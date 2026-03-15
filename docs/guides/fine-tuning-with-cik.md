# Fine-Tuning with Constitutional Identity Kernels (CIK)

This guide demonstrates how to use the **Divergence Penalty** during the fine-tuning of open-source models (like Llama 3 or Mistral) to ensure identity continuity.

## Prerequisites

Install the machine learning optional dependencies:
```bash
pip install ct-toolkit[ml]
```

## The Divergence Penalty

The `DivergencePenaltyLoss` is a PyTorch-compatible loss term that penalizes the model when its internal representations drift too far from the anchor defined in its **Constitutional Kernel**.

### Integration with Standard PyTorch Loop

```python
import torch
from ct_toolkit.divergence.loss import DivergencePenaltyLoss

# Initialize the penalty term
identity_criterion = DivergencePenaltyLoss(alpha=0.5)

# Training loop
for batch in dataloader:
    outputs = model(**batch)
    
    # Standard cross-entropy loss
    task_loss = outputs.loss
    
    # Calculate Identity Divergence Penalty
    # Note: reference_embeddings should be the anchor from your CIK
    penalty = identity_criterion(outputs.hidden_states[-1], reference_embeddings)
    
    # Total loss
    total_loss = task_loss + penalty
    
    total_loss.backward()
    optimizer.step()
```

### Integration with HuggingFace Trainer

You can override the `compute_loss` method in a custom `Trainer` subclass:

```python
from transformers import Trainer

class TheseusTrainer(Trainer):
    def compute_loss(self, model, inputs, return_outputs=False):
        outputs = model(**inputs, output_hidden_states=True)
        task_loss = outputs.loss
        
        # Identity anchor (calculated once or retrieved from kernel)
        ref_embeds = self.get_identity_anchor()
        
        # Penalize drift
        penalty = compute_alignment_loss(outputs.hidden_states[-1], ref_embeds)
        
        loss = task_loss + penalty
        return (loss, outputs) if return_outputs else loss
```

## Why use this?
Traditional fine-tuning (SFT/RLHF) often causes "catastrophic forgetting" or identity attenuation. By adding a **Divergence Penalty**, you explicitly preserve the normative priors of the agent as a first-class optimization constraint.
