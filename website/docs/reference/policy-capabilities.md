# Policy & Capability Metadata

CT Toolkit resolves role-based execution policy through a startup capability registry and exposes the result as standardized metadata across middleware.

## Registry file

Default registry path:

- `config/llm_capability.yaml`

This file stores:

- Provider/model capabilities (`text`, `image`, `audio`, `video`, `tool_call`, `reasoning`)
- Role policies (`main`, `sub`, `judge`, `l3`)
- Environment overrides (`dev`, `test`, `prod`)

## Effective policy resolution

Use `TheseusWrapper.resolve_llm_policy()` to merge:

1. Role defaults
2. Registry `role_policies`
3. Environment override block
4. Model capability constraints

Example:

```python
policy = wrapper.resolve_llm_policy(model="gpt-4o-mini", role="judge")
print(policy["effective"]["tool_call"])  # False
```

## Standard metadata payload

Use `TheseusWrapper.propagate_policy_metadata()`:

```python
{
  "role": "main",
  "environment": "prod",
  "effective": {
    "text": True,
    "image": True,
    "audio": True,
    "video": False,
    "multimodal": True,
    "tool_call": True,
    "reasoning": False,
  },
}
```

## Middleware exposure

CT Toolkit now exposes this payload consistently:

- LangChain: `TheseusChatModel.policy_metadata` and `generation_info["ct_policy"]`
- CrewAI: `crew.ct_policy`, `agent.ct_policy`, and `metadata["ct_policy"]`
- Deep Agents: `metadata["ct_policy"]` in wrapped factory calls and helper config
- AutoGen: `llm_config.metadata.ct_policy` and `config_list[*].metadata.ct_policy`

## Policy environment at runtime

You can select environment-level overrides via:

- `WrapperConfig(policy_environment="dev" | "test" | "prod")`
- CLI: `ct-toolkit audit --policy-environment test`
- CLI: `ct-toolkit serve --policy-environment prod`
