"""L5 — the Attention Market. Cognition is an economy, not a queue.

Every tick, every runnable script submits a bid for the organism's scarce
action budget. The bid is one number:

    attention = urgency * justification * opportunity * novelty * expected_value

Why MULTIPLICATION and not a weighted sum? Because the factors are vetoes,
not bonuses. An action that is urgent but unjustified (no living WHY) must
not run. An action that is justified but has no opportunity (its trigger
condition is false) must not run. In an additive scheme a huge urgency can
buy its way past a zero; in a multiplicative market a single zero factor
kills the bid outright. The formula encodes the ethics of the organism.

The five factors (all clamped to [0, 1]):
  urgency         pressure from unmet tensions (tension.py) — hunger, curiosity
  justification   health of the WHY chain (why.py) — is this purpose alive?
  opportunity     are the preconditions true right now? (script's `when`)
  novelty         has the relevant part of the world changed since last look?
  expected_value  what did this action earn before? (success_rate, or a
                  simulation rollout — simulations.py)

The market clears the top-k bids per tick; the executive (executive.py)
resolves resource conflicts among winners. Everything else starves this
tick — and starvation is measured, because starving scripts eventually die
(scripts.py). Scarcity is the point: attention is the organism's budget,
and the market spends it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .util import clamp01

FACTORS = ("urgency", "justification", "opportunity", "novelty", "expected_value")


@dataclass(frozen=True)
class AttentionBid:
    """One script's claim on this tick's action budget."""

    src: str                      # component id that owns the script
    label: str                    # script name (what to run if cleared)
    urgency: float = 0.0
    justification: float = 0.0
    opportunity: float = 0.0
    novelty: float = 0.0
    expected_value: float = 0.0
    resource: Optional[str] = None  # exclusive resource key, if any
    success_p: Optional[float] = None  # claimed probability the action succeeds

    @property
    def attention(self) -> float:
        """The product. Any factor at zero vetoes the bid entirely."""
        a = 1.0
        for f in FACTORS:
            a *= clamp01(getattr(self, f))
        return a

    def factors(self) -> dict:
        return {f: round(clamp01(getattr(self, f)), 4) for f in FACTORS}


@dataclass
class ClearResult:
    """Outcome of one market clearing."""

    winners: list = field(default_factory=list)  # bids that may run
    starved: list = field(default_factory=list)  # bids that lost this tick


class AttentionMarket:
    """Collects bids once per tick, clears top-k, counts the starvation."""

    def __init__(self) -> None:
        self._bids: list = []
        self.bids_total = 0
        self.cleared_total = 0
        self.starve_counts: dict = {}

    def submit(self, bid: AttentionBid) -> None:
        self._bids.append(bid)

    def pending(self) -> int:
        return len(self._bids)

    def clear(self, top_k: int = 3) -> ClearResult:
        """Rank by attention (desc); deterministic tie-breaks by src, label.

        THE VETO LAW: a bid whose attention is 0 (any factor at zero)
        NEVER clears — not even in an empty market. An organism with
        nothing worth doing would rather idle into sleep than spend its
        budget on vetoed actions. Scarcity is not desperation.
        """
        ranked = sorted(
            self._bids, key=lambda b: (-b.attention, b.src, b.label)
        )
        live = [b for b in ranked if b.attention > 0.0]
        vetoed = [b for b in ranked if b.attention <= 0.0]
        k = max(0, int(top_k))
        winners = live[:k]
        starved = live[k:] + vetoed
        self.bids_total += len(ranked)
        self.cleared_total += len(winners)
        for b in starved:
            self.starve_counts[b.label] = self.starve_counts.get(b.label, 0) + 1
        self._bids = []  # the market clears; next tick starts empty
        return ClearResult(winners=winners, starved=starved)

    def stats(self) -> dict:
        return {
            "bids_total": self.bids_total,
            "cleared_total": self.cleared_total,
            "clear_rate": (
                round(self.cleared_total / self.bids_total, 4) if self.bids_total else 0.0
            ),
            "most_starved": sorted(
                self.starve_counts.items(), key=lambda kv: (-kv[1], kv[0])
            )[:5],
        }
