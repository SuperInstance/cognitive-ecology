"""The arbiter scorecard — paid judgment must earn its keep (ADR-0013).

ADR-0009 let a decision model into exactly one bounded hook: the
executive's tie-break among live contenders. It counts DIVERGENCES —
how often the arbiter disagreed with the deterministic shadow — but a
divergence count is not a value: disagreeing badly and disagreeing
well look identical.

This module closes OPEN_QUESTIONS #3's remainder by scoring the
delegated judgment by REALIZED OUTCOMES:

* every arbiter pick is a probabilistic claim — "this contender
  deserves the slot", with the client's calibrated confidence — and
  when the pick acts, its outcome (ok/fail) is scored by the SAME
  immune system as component claims (calibration.CalibrationLog:
  Brier, reliability bins). An arbiter that is confident and wrong is
  measurably dishonest from the organism's own receipts;
* every DIVERGENT pick (the arbiter overrode the shadow) is compared
  against the base rate of all actions on arbiter ticks: if the
  arbiter's overrides succeed below (base - margin), the delegation is
  destroying value, not adding judgment;
* an arbiter that fails either test over a large enough window is
  BENCHED — the executive silently degrades to the deterministic
  shadow (the fail-safe ADR-0009 already guaranteed), the benching is
  announced once as a DECISION event, and the receipt explains why.

The scorecard is kernel-side and zero-dependency: it scores whatever
callable the executive delegates to, with no knowledge of providers.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .calibration import CalibrationLog


@dataclass
class BenchEvent:
    """The receipt for a benching: what happened, and why."""

    tick: int
    reason: str


class ArbiterScorecard:
    """Scores the executive's delegated tie-break by realized outcomes.

    Parameters
    ---------
    name:
        for receipts and calibration claimer identity.
    brier_threshold:
        bench when the arbiter's Brier score exceeds this over at
        least ``window`` scored picks (0.25 = the coin-flip baseline).
    base_rate_margin:
        bench when divergent picks' success rate falls this far below
        the base rate of all actions on arbiter ticks.
    window:
        minimum scored picks / divergent picks before benching is
        allowed — no snap judgments about judgment.
    """

    def __init__(self, name: str = "arbiter", brier_threshold: float = 0.25,
                 base_rate_margin: float = 0.10, window: int = 20) -> None:
        if not (0.0 <= brier_threshold <= 1.0):
            raise ValueError("brier_threshold must be 0..1")
        if not (0.0 <= base_rate_margin <= 1.0):
            raise ValueError("base_rate_margin must be 0..1")
        if window < 1:
            raise ValueError("window must be >= 1")
        self.name = name
        self.brier_threshold = brier_threshold
        self.base_rate_margin = base_rate_margin
        self.window = window
        # the immune system, reused: claimer is the arbiter's name
        self.calibration = CalibrationLog()
        self.calls = 0                 # arbiter invocations scored
        self.divergences = 0           # picks that overrode the shadow
        self.divergent_picks = 0       # divergent picks that acted
        self.divergent_successes = 0
        self._base_actions = 0         # all actions on arbiter ticks
        self._base_successes = 0
        self.benched = False
        self.bench: BenchEvent | None = None

    # -- live bookkeeping (called by the executive / runtime) --------------

    def note_call(self) -> None:
        """The arbiter was invoked (before we know what it picked)."""
        self.calls += 1

    def note_divergence(self) -> None:
        """The arbiter overrode the deterministic shadow."""
        self.divergences += 1

    def note_action_outcome(self, ok: bool) -> None:
        """Base-rate bookkeeping: one action's outcome on an arbiter tick."""
        self._base_actions += 1
        if ok:
            self._base_successes += 1

    def record_outcome(self, tick: int, pick: str,
                       confidence: float | None, ok: bool,
                       divergent: bool) -> None:
        """The arbiter's pick acted; score the realized outcome.

        A confidence-carrying pick is a probabilistic claim and lands
        in the calibration log (no confidence -> no claim, but the
        outcome still counts toward the value comparison).
        """
        if self.benched:
            return  # benched arbiters accrue no further debt
        if confidence is not None:
            self.calibration.record(
                tick, f"arbiter:{self.name}", pick, float(confidence),
                1.0 if ok else 0.0)
        if divergent:
            self.divergent_picks += 1
            if ok:
                self.divergent_successes += 1
            self._maybe_bench(tick)

    # -- the immune response ------------------------------------------------

    def _maybe_bench(self, tick: int) -> None:
        if self.benched:
            return
        # test A: calibration — confident and wrong more often than a
        # coin flip, over a large enough sample of scored claims
        claims = self.calibration.records(f"arbiter:{self.name}")
        brier = self.calibration.brier(f"arbiter:{self.name}")
        if brier is not None and len(claims) >= self.window \
                and brier > self.brier_threshold:
            self._bench(tick, (
                f"miscalibrated: Brier {brier:.3f} > {self.brier_threshold} "
                f"over {len(claims)} scored picks — confident and wrong more "
                f"often than a coin flip"))
            return
        # test B: value — divergent picks succeed below the base rate
        # of all actions on arbiter ticks, by more than the margin
        if self.divergent_picks >= self.window and self._base_actions > 0:
            base = self._base_successes / self._base_actions
            divergent = self.divergent_successes / self.divergent_picks
            if divergent < base - self.base_rate_margin:
                self._bench(tick, (
                    f"value-destroying: divergent picks succeed at "
                    f"{divergent:.3f} vs base rate {base:.3f} "
                    f"(margin {self.base_rate_margin}) over "
                    f"{self.divergent_picks} overrides"))

    def _bench(self, tick: int, reason: str) -> None:
        self.benched = True
        self.bench = BenchEvent(tick=tick, reason=reason)

    # -- receipts -----------------------------------------------------------

    @property
    def base_rate(self) -> float | None:
        if self._base_actions == 0:
            return None
        return self._base_successes / self._base_actions

    @property
    def divergent_rate(self) -> float | None:
        if self.divergent_picks == 0:
            return None
        return self.divergent_successes / self.divergent_picks

    def summary(self) -> str:
        brier = self.calibration.brier(f"arbiter:{self.name}")
        lines = [
            f"arbiter scorecard [{self.name}]: "
            f"{self.calls} calls, {self.divergences} divergences",
            f"  calibration : {self.calibration.verdict(f'arbiter:{self.name}')}",
            f"  divergent   : {self.divergent_successes}/"
            f"{self.divergent_picks} overrides succeeded "
            f"(base rate {self.base_rate if self.base_rate is None else round(self.base_rate, 3)})",
        ]
        if self.benched and self.bench is not None:
            lines.append(
                f"  BENCHED at tick {self.bench.tick}: {self.bench.reason}")
        elif brier is not None:
            lines.append("  standing    : earning its keep")
        return "\n".join(lines)

    # -- persistence ----------------------------------------------------------

    def to_json(self) -> dict:
        return {
            "name": self.name,
            "brier_threshold": self.brier_threshold,
            "base_rate_margin": self.base_rate_margin,
            "window": self.window,
            "calibration": self.calibration.to_json(),
            "calls": self.calls,
            "divergences": self.divergences,
            "divergent_picks": self.divergent_picks,
            "divergent_successes": self.divergent_successes,
            "base_actions": self._base_actions,
            "base_successes": self._base_successes,
            "benched": self.benched,
            "bench": {"tick": self.bench.tick, "reason": self.bench.reason}
            if self.bench else None,
        }

    @classmethod
    def from_json(cls, data: dict) -> "ArbiterScorecard":
        sc = cls(
            name=data.get("name", "arbiter"),
            brier_threshold=data.get("brier_threshold", 0.25),
            base_rate_margin=data.get("base_rate_margin", 0.10),
            window=data.get("window", 20),
        )
        sc.calibration = CalibrationLog.from_json(data.get("calibration", {}))
        sc.calls = data.get("calls", 0)
        sc.divergences = data.get("divergences", 0)
        sc.divergent_picks = data.get("divergent_picks", 0)
        sc.divergent_successes = data.get("divergent_successes", 0)
        sc._base_actions = data.get("base_actions", 0)
        sc._base_successes = data.get("base_successes", 0)
        sc.benched = data.get("benched", False)
        b = data.get("bench")
        if b:
            sc.bench = BenchEvent(tick=b["tick"], reason=b["reason"])
        return sc
