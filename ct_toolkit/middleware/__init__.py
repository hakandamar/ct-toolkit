"""
ct_toolkit.middleware
=====================
Middleware integrations for various agent frameworks.

This module provides:
- AutoGen: Integration with Microsoft AutoGen
- CrewAI: Integration with CrewAI framework
- DeepAgents: Integration with DeepAgents
- LangChain: Integration with LangChain
- LiteLLM: Integration with LiteLLM
"""

from ct_toolkit.middleware.langchain import TheseusChatModel, TheseusLangChainCallback
from ct_toolkit.middleware.litellm import TheseusLiteLLMCallback

__all__ = [
    "TheseusChatModel",
    "TheseusLangChainCallback",
    "TheseusLiteLLMCallback",
]