"""agents — LLMs and decision models as citizens of the ecology.

The kernel runs with zero models. When you do want a model, it joins as a
component subject to the same laws as everything else: WHY-gated,
market-cleared, necrology-recorded.

    from cognitive_ecology.agents import LLMAgent, MockProvider, \
        OpenAICompatProvider, StablePrefixSession
"""
from .providers import (
    Completion,
    HY4_PRICES,
    MockProvider,
    OpenAICompatProvider,
    StablePrefixSession,
)
from .orchestrator import (
    ACTION_LIBRARY,
    ACTION_LIBRARY_DOC,
    LLMAgent,
    build_when,
    parse_proposals,
)

__all__ = [
    "ACTION_LIBRARY", "ACTION_LIBRARY_DOC", "Completion", "HY4_PRICES",
    "LLMAgent", "MockProvider", "OpenAICompatProvider",
    "StablePrefixSession", "build_when", "parse_proposals",
]
