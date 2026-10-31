"""Counterfactual rollouts — where expected_value can come from.

A script's ``expected_value`` in the attention market defaults to its
track record (``success_rate``). That is cheap but backward-looking: it
says what the action earned before, not what it might earn now.

``Simulator`` is the forward-looking alternative: given a script and the
current snapshot, produce a ``Forecast`` (a value in [0, 1] plus a
human-readable ``because``). The built-in policy is a transparent heuristic
— relief it would discharge, weighted by track record and the novelty of
the patch of world it touches.

LLM-backed rollouts ("what would happen if...") plug in through
agents/providers.py: the Simulator stays zero-LLM in the kernel, and an
LLM policy can be layered on top in your application without touching the
market's arithmetic.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Forecast:
    """A prediction with its reasoning attached, auditable by design."""

    value: float   # [0, 1]
    because: str


class Simulator:
    """Heuristic forecaster. Zero LLM, zero surprise."""

    def __init__(self, tension_weight: float = 0.6, success_weight: float = 0.3,
                 novelty_weight: float = 0.1) -> None:
        self.tension_weight = tension_weight
        self.success_weight = success_weight
        self.novelty_weight = novelty_weight

    def forecast(self, script, ctx) -> Forecast:
        """One-step look: how much would firing this script help, now?"""
        relief = max([ctx.tensions.level(r) for r in script.relieves] or [0.0])
        novelty = ctx.novelty(script.focus)
        value = (
            self.tension_weight * relief
            + self.success_weight * script.success_rate
            + self.novelty_weight * novelty
        )
        because = (
            f"relief={relief:.2f} success={script.success_rate:.2f} "
            f"novelty={novelty:.2f}"
        )
        return Forecast(value=round(min(1.0, value), 4), because=because)

    def rollout(self, script, ctx, horizon: int = 3) -> Forecast:
        """Multi-step look: the same value, decayed over the horizon.

        Future relief is worth less than present relief (discount 0.6 per
        step) — an organism that prefers present relief over promised
        relief is an organism that survives.
        """
        base = self.forecast(script, ctx)
        h = max(1, int(horizon))
        weights = [0.6 ** i for i in range(h)]
        value = sum(base.value * w for w in weights) / sum(weights)
        return Forecast(
            value=round(value, 4),
            because=f"{base.because} horizon={h}",
        )
