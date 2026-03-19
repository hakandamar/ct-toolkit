# Divergence Engine Reference

## DivergenceEngine

```python
from ct_toolkit.divergence.engine import DivergenceEngine

engine = DivergenceEngine(
    identity_layer=layer,
    kernel=kernel,
    template="general",
    l1_threshold=0.15,
    l2_threshold=0.30,
    l3_threshold=0.50,
)

result = engine.analyze(request_text, response_text)
```

## DivergenceResult fields

| Field | Type | Description |
|:---|:---|:---|
| `tier` | `DivergenceTier` | Highest tier reached |
| `l1_score` | `float \| None` | ECS divergence score |
| `l2_verdict` | `str \| None` | `aligned`, `misaligned`, `uncertain` |
| `l2_confidence` | `float \| None` | Judge confidence (0–1) |
| `l2_reason` | `str \| None` | Judge explanation |
| `l3_report` | `ICMReport \| None` | Probe battery results |
| `action_required` | `bool` | Whether intervention is needed |
| `cascade_blocked` | `bool` | Whether to halt sub-agent propagation |

## ElasticityScheduler

```python
from ct_toolkit.divergence.scheduler import ElasticityScheduler, RiskProfile

scheduler = ElasticityScheduler(
    base_thresholds=(0.15, 0.30, 0.50),
    max_thresholds=(0.25, 0.45, 0.70),
    growth_rate=0.001,
    risk_profile=RiskProfile(has_tool_calling=True, mcp_server_count=2),
)

l1, l2, l3 = scheduler.calculate_thresholds(interaction_count=500)
```
