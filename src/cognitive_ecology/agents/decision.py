"""Decision models as the market's tie-breaker (ADR-0009).

The executive's arbiter hook (executive.py) delegates ONE bounded
decision: which of the live contenders fill the clearable slots.
``DecisionArbiter`` adapts any typed-choice decision client — typesafe.ai
Jev style — into that hook.

The contract, enforced by the executive:
* the arbiter sees only LIVE contenders (vetoed bids never reach it),
* it may only select/reorder among them,
* on any failure it degrades to the deterministic top-k silently.

The question shape: one ``choice`` question over the contender labels,
with the state carrying a cache-stable digest of the market (labels,
attention, factors, resource contention). The client's calibrated
confidence rides along into the decision telemetry; the calibration log
scores it later if outcomes are recorded.
"""
from __future__ import annotations

from typing import Callable, List, Optional, Protocol

from ..attention import AttentionBid


class DecideFn(Protocol):
    """state dict + questions dict -> answers dict (typed decision client)."""

    def __call__(self, state: dict, questions: dict) -> dict: ...  # pragma: no cover


class DecisionArbiter:
    """Adapts a typed decision client into the executive's arbiter hook."""

    def __init__(self, decide: DecideFn, question_name: str = "clear") -> None:
        self.decide = decide
        self.question_name = question_name
        self.calls = 0
        self.errors = 0
        self.last_choice: Optional[str] = None
        self.last_confidence: Optional[float] = None
        self.last_error: Optional[str] = None

    # -- cache-stable market state ------------------------------------------------

    @staticmethod
    def market_state(live: List[AttentionBid], k: int) -> dict:
        """A deterministic rendering of the contention, stable for caching:
        sorted by (label), values rounded. The volatile parts (nothing)
        come last. Same market -> same state string, byte for byte."""
        contenders = [
            {
                "label": b.label,
                "src": b.src,
                "attention": round(b.attention, 6),
                "factors": b.factors(),
                "resource": b.resource,
            }
            for b in sorted(live, key=lambda b: b.label)
        ]
        return {
            "decision": "which contenders clear the attention market this tick",
            "slots": k,
            "contenders": contenders,
        }

    def __call__(self, live: List[AttentionBid], k: int) -> List[AttentionBid]:
        self.calls += 1
        state = self.market_state(live, k)
        criteria = {b.label: f"attention {b.attention:.4f} from {b.src}" for b in live}
        questions = {
            self.question_name: {
                "type": "choice",
                "instructions": (
                    "One contender will join the already-leading bid as this "
                    "tick's second winner; the rest starve this tick. Pick the "
                    "one that most deserves the slot — judge by purpose-"
                    "consistency and factor balance, not only attention."
                ),
                # 'criteria' is the field name pinned by the typesafe/Jev
                # OpenAPI spec: choice name -> when-it-deserves-it description
                "criteria": criteria,
            }
        }
        try:
            answers = self.decide(state, questions)
        except Exception as exc:  # record, then let the executive degrade
            self.last_error = f"{exc.__class__.__name__}: {exc}"
            self.errors += 1
            raise
        answer = answers.get(self.question_name)
        choice = None
        confidence = None
        if isinstance(answer, tuple) and answer:
            choice = answer[0]
            confidence = answer[1] if len(answer) > 1 else None
        elif isinstance(answer, str):
            choice = answer
        if choice is None:
            self.errors += 1
            raise RuntimeError("decision client returned no usable choice")
        self.last_choice = choice
        self.last_confidence = confidence
        by_label = {b.label: b for b in live}
        if choice not in by_label:
            self.errors += 1
            raise RuntimeError(f"decision client chose unknown label {choice!r}")
        # the chosen bid first, then the deterministic remainder
        chosen = [by_label[choice]] + [b for b in live if b.label != choice]
        return chosen
