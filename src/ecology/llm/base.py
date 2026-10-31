"""LLM teacher layer — shared types and the cache-first prompt protocol.

Law 4: LLMs are teachers, not workers. They never run inside a tick; they
are called by the research panel and (later) by sleep to *propose* better
scripts — they edit the organism, they do not impersonate it.

The cache-first protocol is the economic heart of this layer:

- a request is a **stable prefix** (persona, topic, context, transcript so
  far — byte-identical across calls in a session) plus a **variable suffix**
  (this turn's instruction);
- transcripts grow append-only, so every call's prefix extends the previous
  call's prefix — exactly what DeepInfra/MiniMax automatic prefix caching
  rewards (cache-read is 80-90% off list price on the panel models);
- ``cache_friendliness`` reports how much of the request was prefix.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class PromptSpec:
    """A cache-friendly request: stable prefix + variable suffix."""

    stable_prefix: str
    variable_suffix: str
    max_tokens: int = 1024
    temperature: float | None = None

    @property
    def cache_friendliness(self) -> float:
        """Fraction of the prompt that is stable, cacheable prefix."""
        total = len(self.stable_prefix) + len(self.variable_suffix)
        if total == 0:
            return 0.0
        return len(self.stable_prefix) / total


@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_tokens: int = 0
    cost_usd: float | None = None  # None = provider did not report; estimated locally
    cache_read_input_tokens: int = 0  # anthropic-style field name


@dataclass
class LLMResponse:
    text: str
    model: str
    provider: str
    usage: Usage = field(default_factory=Usage)
    latency_ms: int = 0
    raw: dict = field(default_factory=dict)

    @property
    def cache_hit_tokens(self) -> int:
        return max(self.usage.cached_tokens, self.usage.cache_read_input_tokens)


@dataclass
class DecisionRequest:
    """A structured question set for decision models (TypeSafe/Jev style).

    ``state`` is what the questions are about; questions map a name to a
    spec: ``{"type": "noul"|"choice"|"score", "instructions": str,
    "criteria": ...}`` (criteria shapes per the TypeSafe OpenAPI spec).
    """

    state: dict | str
    questions: dict[str, dict]
    model: str = "jev-latest"


@dataclass
class DecisionAnswer:
    name: str
    type: str
    # noul: float probability; choice: (name, confidence, probs); score: (score, confidence)
    value: object


@dataclass
class DecisionResponse:
    answers: dict[str, DecisionAnswer] = field(default_factory=dict)
    model: str = ""
    provider: str = ""
    usage: Usage = field(default_factory=Usage)
    latency_ms: int = 0


@runtime_checkable
class LLMClient(Protocol):
    """Anything that can turn a PromptSpec into text (chat-style providers)."""

    provider: str
    default_model: str

    def complete(
        self, spec: PromptSpec, model: str | None = None
    ) -> LLMResponse:
        ...  # pragma: no cover


@runtime_checkable
class DecisionClient(Protocol):
    """Anything that answers typed, calibrated questions about a state."""

    provider: str

    def decide(self, request: DecisionRequest) -> DecisionResponse:
        ...  # pragma: no cover
