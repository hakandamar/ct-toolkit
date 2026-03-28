# CT Toolkit Examples

This directory contains standalone examples for using CT Toolkit guardrails in various scenarios.

## Core Examples

- [**basic_usage.py**](./basic_usage.py): The simplest "Hello World" for `TheseusWrapper`.
- [**reflective_endorsement.py**](./reflective_endorsement.py): Demonstrates how to handle rule violations and approve identity changes.

## Framework Middlewares

- [**langchain_callback.py**](./langchain_callback.py): Integrating with LangChain via the callback system.
- [**crewai_hierarchy.py**](./crewai_hierarchy.py): **(Recommended)** Demonstrates hierarchical kernel propagation across a Crew of agents.
- [**hierarchical_agents.py**](./hierarchical_agents.py): Advanced example of mother-to-child kernel inheritance using the core wrapper.

## Local Models

- [**ollama_integration.py**](./ollama_integration.py): Running CT Toolkit against local Ollama instances (e.g., Llama 3).

## External Example Projects

- [**ct-toolkit-fastapi**](https://github.com/hakandamar/ct-toolkit-fastapi): FastAPI-based integration and validation suite for CT Toolkit. Useful for developers who want a ready-made project to test L1/L2/L3 guardrails, provenance logging, and local LM Studio/Ollama setups.

---

### Running Examples

Most examples require an API key (e.g., `OPENAI_API_KEY`) or a local Ollama instance.

```bash
# Install core + dev dependencies
pip install -e ".[dev,langchain,crewai,autogen]"

# Run an example
python examples/crewai_hierarchy.py
```
