# CrewAI Middleware

CT Toolkit provides hierarchical kernel propagation for CrewAI v1.10+.

## Hierarchical Propagation

In multi-agent systems, it's critical that sub-agents inherit the core constraints of the mother agent. `TheseusCrewMiddleware` automates this inheritance.

```python
from ct_toolkit import TheseusWrapper
from ct_toolkit.middleware.crewai import TheseusCrewMiddleware
from crewai import Crew

# 1. Initialize the manager's wrapper
manager_wrapper = TheseusWrapper(provider="openai", kernel_name="defense")

# 2. Your CrewAI setup
crew = Crew(agents=[...], tasks=[...])

# 3. Apply the middleware
TheseusCrewMiddleware.apply_to_crew(crew, manager_wrapper)

# 4. Kickoff
crew.kickoff()
```

When `apply_to_crew` is called, every agent's LLM is wrapped in a `TheseusChatModel` that enforces the manager's kernel.
