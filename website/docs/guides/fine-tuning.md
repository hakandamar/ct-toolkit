# Fine-Tuning with CIK

Use `DivergencePenaltyLoss` to preserve identity during PyTorch fine-tuning.

```bash
pip install "ct-toolkit[ml]"
```

## PyTorch training loop

```python
import torch
from ct_toolkit.divergence.loss import DivergencePenaltyLoss

criterion = DivergencePenaltyLoss(alpha=0.5)

for batch in dataloader:
    outputs = model(**batch)
    
    task_loss  = outputs.loss
    id_penalty = criterion(outputs.hidden_states[-1], reference_embeddings)
    
    total_loss = task_loss + id_penalty
    total_loss.backward()
    optimizer.step()
```

## HuggingFace Trainer

```python
from transformers import Trainer
from ct_toolkit.divergence.loss import compute_alignment_loss

class TheseusTrainer(Trainer):
    def compute_loss(self, model, inputs, return_outputs=False):
        outputs = model(**inputs, output_hidden_states=True)
        task_loss = outputs.loss
        penalty   = compute_alignment_loss(outputs.hidden_states[-1], ref_embeds)
        loss = task_loss + penalty
        return (loss, outputs) if return_outputs else loss
```
