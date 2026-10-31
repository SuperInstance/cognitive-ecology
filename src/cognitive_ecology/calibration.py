"""Calibration — predicted probabilities meet realized outcomes.

The attention formula produces *scores*, but many components naturally
hold *beliefs*: "this action will probably succeed" (expected_value),
"this is probably novel" (novelty). A score ranks; a probability claims.
Claims can be wrong in a measurable way.

This module keeps the receipts: every probabilistic claim (`success_p` on
an AttentionBid) is logged against its realized outcome (the action's ok
flag), and scored:

    Brier score = mean((predicted_p - realized_01)^2)

0.0 is perfect foresight; 0.25 is a coin flip reported as 50/50; anything
above 0.25 is *miscalibrated in the harmful direction* — confident and
wrong. Reliability bins show where the errors live (the classic
overconfident tail).

Why this matters to the ecology: an estimator that is confident and wrong
wins attention it does not deserve. Calibration is the immune system of
the attention economy — and the empirical leg of the decision-model
integration question (docs/08): if provider confidences do not track
outcomes, they must be demoted to rankings.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CalibrationRecord:
    """One probabilistic claim and its outcome."""

    tick: int
    claimer: str        # component id
    claim: str          # label of the claim (usually the bid label)
    predicted: float    # claimed probability, 0..1
    realized: float     # 1.0 (happened) or 0.0 (did not)


class CalibrationLog:
    """Append-only log of probabilistic claims vs outcomes."""

    def __init__(self) -> None:
        self._records: list[CalibrationRecord] = []

    def record(self, tick: int, claimer: str, claim: str,
               predicted: float, realized: float) -> None:
        if not (0.0 <= predicted <= 1.0):
            raise ValueError(f"predicted must be a probability 0..1, got {predicted}")
        if realized not in (0.0, 1.0):
            raise ValueError(f"realized must be 0.0 or 1.0, got {realized}")
        self._records.append(
            CalibrationRecord(tick, claimer, claim, predicted, realized))

    def __len__(self) -> int:
        return len(self._records)

    def records(self, claimer: str | None = None) -> list:
        if claimer is None:
            return list(self._records)
        return [r for r in self._records if r.claimer == claimer]

    def brier(self, claimer: str | None = None) -> float | None:
        """Mean Brier score; None when there is nothing to score yet."""
        rs = self.records(claimer)
        if not rs:
            return None
        return sum((r.predicted - r.realized) ** 2 for r in rs) / len(rs)

    def reliability(self, claimer: str | None = None, bins: int = 5) -> list:
        """[(bin_lo, bin_hi, n, mean_predicted, mean_realized)] per bin."""
        rs = self.records(claimer)
        out = []
        for i in range(bins):
            lo, hi = i / bins, (i + 1) / bins
            in_bin = [r for r in rs if lo <= r.predicted < hi or
                      (i == bins - 1 and r.predicted == 1.0)]
            if not in_bin:
                continue
            out.append((
                round(lo, 2), round(hi, 2), len(in_bin),
                round(sum(r.predicted for r in in_bin) / len(in_bin), 3),
                round(sum(r.realized for r in in_bin) / len(in_bin), 3),
            ))
        return out

    def verdict(self, claimer: str | None = None) -> str:
        """Plain-language calibration verdict for receipts and reports."""
        b = self.brier(claimer)
        if b is None:
            return "no claims logged yet"
        if b <= 0.25:
            return (f"calibrated-or-better (Brier {b:.3f} <= 0.25 coin-flip "
                    f"baseline over {len(self.records(claimer))} claims)")
        return (f"MISCALIBRATED (Brier {b:.3f} > 0.25: confident and wrong "
                f"more often than a coin flip, {len(self.records(claimer))} claims)")

    # -- persistence ------------------------------------------------------------
    def to_json(self) -> dict:
        return {"records": [
            {"tick": r.tick, "claimer": r.claimer, "claim": r.claim,
             "predicted": r.predicted, "realized": r.realized}
            for r in self._records
        ]}

    @classmethod
    def from_json(cls, data: dict) -> "CalibrationLog":
        log = cls()
        for rd in data.get("records", []):
            log._records.append(CalibrationRecord(
                rd["tick"], rd["claimer"], rd["claim"],
                rd["predicted"], rd["realized"]))
        return log
