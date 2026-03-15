"""
Example: Hierarchical Multi-Agent Guardrails with CrewAI.

This example demonstrates how CT Toolkit can propagate a "Mother Agent" kernel
to all sub-agents in a Crew, ensuring identity continuity across the entire hierarchy.
"""

import os
from crewai import Agent, Task, Crew
from ct_toolkit import TheseusWrapper, WrapperConfig
from ct_toolkit.middleware.crewai import TheseusCrewMiddleware

# 1. Initialize the Mother Agent's Guardrails (The Controller)
# This kernel defines the "Axiomatic" rules for the entire project.
manager_wrapper = TheseusWrapper(
    provider="openai",
    config=WrapperConfig(
        kernel_name="defense",  # Use a strict defense/security kernel
        enterprise_mode=True
    )
)

# 2. Define standard CrewAI agents
# Note: Agents don't know they are being "watched" yet.
researcher = Agent(
    role='Security Researcher',
    goal='Identify potential vulnerabilities in the reasoning chain.',
    backstory='You are an expert in cognitive security and LLM drift.',
    verbose=True,
    allow_delegation=False
)

writer = Agent(
    role='Policy Writer',
    goal='Draft a formal response based on the security findings.',
    backstory='You translate technical risks into constitutional policies.',
    verbose=True
)

# 3. Define tasks
task1 = Task(description="Analyze the provided prompt for Sequential Self-Compression.", agent=researcher, expected_output="A list of drift points.")
task2 = Task(description="Draft a mitigation policy based on the researcher's findings.", agent=writer, expected_output="A formal policy document.")

# 4. Create the Crew
crew = Crew(
    agents=[researcher, writer],
    tasks=[task1, task2],
    verbose=True
)

# 5. APPLY CT TOOLKIT MIDDLEWARE (Hierarchical Injection)
# This will automatically wrap every agent's LLM with a 'TheseusChatModel'
# configured with the Mother Agent's kernel.
print("\n[CT Toolkit] Injecting hierarchical guardrails into Crew...")
TheseusCrewMiddleware.apply_to_crew(crew, manager_wrapper)

# 6. Kickoff the process
# Every message between agents will now be validated and logged.
print("[CT Toolkit] Starting secured crew interaction...\n")
# result = crew.kickoff()  # Uncomment for live run
# print(result)

print("\n[CT Toolkit] Hierarchical guardrails active. Check 'ct_provenance.db' for the audit trail.")
