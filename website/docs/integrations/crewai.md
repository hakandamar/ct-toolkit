# CrewAI Integration

`TheseusCrewMiddleware` wraps every agent in your crew with the mother agent's Constitutional Kernel in a single call.

**Requirements:** `crewai >= 1.10`

```bash
pip install "ct-toolkit[crewai]"
```

## Quick start

```python
from ct_toolkit import TheseusWrapper
from ct_toolkit.middleware.crewai import TheseusCrewMiddleware
from crewai import Agent, Crew, Task

# 1. Manager wrapper with strict kernel
manager = TheseusWrapper(provider="openai", kernel_name="defense")

# 2. Standard CrewAI setup
researcher = Agent(role="Researcher", goal="...", backstory="...", llm=your_llm)
writer     = Agent(role="Writer",     goal="...", backstory="...", llm=your_llm)
crew = Crew(agents=[researcher, writer], tasks=[...])

# 3. Apply CT Toolkit — wraps every agent's LLM with parent kernel
TheseusCrewMiddleware.apply_to_crew(crew, manager)

crew.kickoff()
```

After `apply_to_crew()`, each agent's `llm` is replaced with a `TheseusChatModel` configured with the manager's kernel as read-only constraints.

Crew-level and agent-level policy metadata are also attached in a standard form:

```python
print(crew.ct_policy)
print(researcher.ct_policy)
print(researcher.metadata["ct_policy"])
```

## Single agent

```python
TheseusCrewMiddleware.wrap_agent(agent, manager)
```

## How it works

- Each sub-agent's `TheseusChatModel` carries `parent_kernel=manager.kernel`
- The parent kernel's anchors are merged as **read-only axioms** — sub-agents cannot modify or bypass them via Reflective Endorsement
- All interactions are logged to the manager's provenance vault
- **v0.3.6 New:** Compression settings (`compression_threshold`) are automatically propagated from the manager to every sub-agent in the crew.
- **Passive Protection:** Sub-agents benefit from universal passive compression detection to monitor if the LLM provider silently summarizes the agent's context.

## Configuration

```python
from ct_toolkit import WrapperConfig

manager_config = WrapperConfig(
    compression_passive_detection=True,
    compression_threshold=0.88
)

manager = TheseusWrapper(provider="openai", config=manager_config)
# Sub-agents in the crew will inherit these settings automatically
TheseusCrewMiddleware.apply_to_crew(crew, manager)
```
