"""LLM teacher layer: multi-provider clients behind one protocol.

Chat providers (DeepInfra, MiniMax) implement ``complete(PromptSpec)``;
decision providers (TypeSafe Jev) implement ``decide(DecisionRequest)``.
Everything is cache-first, retried, rate-limited, circuit-broken, and
metered in the usage ledger.
"""

from .base import (
    DecisionAnswer,
    DecisionRequest,
    DecisionResponse,
    LLMClient,
    LLMResponse,
    PromptSpec,
    Usage,
)
from .deepinfra import DeepInfraClient
from .ledger import Ledger, usage_cli
from .minimax import MiniMaxClient
from .resilience import CircuitBreaker, RetryExhausted, RetryPolicy, TokenBucket
from .typesafe import TypeSafeClient

__all__ = [
    "DecisionAnswer",
    "DecisionRequest",
    "DecisionResponse",
    "LLMClient",
    "LLMResponse",
    "PromptSpec",
    "Usage",
    "DeepInfraClient",
    "MiniMaxClient",
    "TypeSafeClient",
    "Ledger",
    "usage_cli",
    "RetryPolicy",
    "RetryExhausted",
    "TokenBucket",
    "CircuitBreaker",
]
