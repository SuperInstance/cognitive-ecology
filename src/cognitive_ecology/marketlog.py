"""The market log — the organism's observation boundary (a read model).

Round 21, from the wave-1 ledger (finding 3: "the organism is
invisible"): the five attention factors are the platform's core
scientific object, yet they were never logged — telemetry had no
provenance, and every observability need arrived as a bolt-on feature.
This module is the fix as an ARCHITECTURE, not a patch: a first-class
read model over the attention market.

The read-model discipline (the ideation-015 verdict, adopted):
  1. EXACT — serialize the exact floats of the very bids the market
     cleared. No re-computation from world state, no rounding at write
     time. A factor of 1/3 is written as the float it was, and reads
     back bit-for-bit.
  2. NOT A SECOND SOURCE OF TRUTH — rows are a serialization of the
     market's own ClearResult and the executive's own decisions. The
     market log can be deleted at any time and the organism loses
     nothing but its observer's history.
  3. NON-PERTURBING — attaching a MarketLog changes no decision, no
     event, no state. Observation must never alter the observed.

One row per bid per tick (``kind: "bid"``):

    {"kind": "bid", "tick": 42, "src": "critter", "label": "forage",
     "urgency": 0.123, "justification": 1.0, "opportunity": 1.0,
     "novelty": 1.0, "expected_value": 0.99, "attention": 0.12177,
     "resource": null, "success_p": null,
     "status": "run", "seq": 1231}

``status`` is the market's verdict on that bid this tick:
  run     cleared and executed
  yield   cleared but lost an exclusive resource to a stronger bid
  starved live (attention > 0) but below the top-k cut
  vetoed  attention <= 0 — the veto law; see ``veto_reasons()`` for WHICH
          factor was zero, in the market's own numbers

When the delegated arbiter actually arbitrated, one extra row
(``kind: "arbiter"``) records its pick, confidence, and whether it
diverged from the deterministic shadow.

Memory is bounded (``keep``, default the most recent 100k rows): this is
an observation tail for live processes, not a ledger — the durable copy
is whatever the host writes via ``to_jsonl()`` (see scripts/run_rounds.py,
which also writes the run manifest that makes every output file
attributable to the seed, config, and code that produced it).
"""
from __future__ import annotations

import json
from collections import deque
from typing import Optional

from .attention import FACTORS


class MarketLog:
    """Bounded, exact, non-perturbing serialization of every market clearing.

    Wired by the Runtime (``rt.market_log``) and fed by the executive at
    the end of each arbitration. Hosts that want nothing simply never
    read it; it costs one row per bid.
    """

    def __init__(self, keep: Optional[int] = 100_000) -> None:
        self._rows: deque = deque(maxlen=keep)

    # ------------------------------------------------------------------
    # write side (called by the executive — never by user code)
    # ------------------------------------------------------------------
    def note_clear(self, tick: int, result, decisions,
                   arbiter_context=None) -> None:
        """Serialize one clearing: every bid, its exact factors, its status.

        ``result`` is the market's ClearResult (winners + starved, in the
        market's own order — post-arbiter when one ran); ``decisions``
        carries the executive's run/yield resolution; ``arbiter_context``
        is the executive's, recorded only when the arbiter truly
        arbitrated. All floats are read from the very bid objects the
        market ranked (identity, not copies), computed once, and written
        without rounding.
        """
        status_by_id = {}
        seq_by_id = {}
        for d in decisions:
            status_by_id[id(d.bid)] = d.status
            seq_by_id[id(d.bid)] = d.event_seq
        for b in list(result.winners) + list(result.starved):
            status = status_by_id.get(id(b))
            if status is None:  # not a winner: live-loser or vetoed
                status = "starved" if b.attention > 0.0 else "vetoed"
            self._rows.append({
                "kind": "bid", "tick": tick, "src": b.src, "label": b.label,
                **{f: float(getattr(b, f)) for f in FACTORS},
                "attention": float(b.attention),
                "resource": b.resource, "success_p": b.success_p,
                "status": status, "seq": seq_by_id.get(id(b), -1),
            })
        if arbiter_context is not None:
            self._rows.append({
                "kind": "arbiter", "tick": tick,
                "pick": arbiter_context.pick,
                "confidence": arbiter_context.confidence,
                "divergent": bool(arbiter_context.divergent),
            })

    # ------------------------------------------------------------------
    # read side
    # ------------------------------------------------------------------
    def rows(self) -> list:
        """Every retained row (bids + arbiter contexts), oldest first."""
        return list(self._rows)

    def bids(self) -> list:
        """Bid rows only — the pandas-friendly frame."""
        return [r for r in self._rows if r.get("kind") == "bid"]

    def summary(self) -> dict:
        """The analyst's first look: volumes, clear rate, winners, vetoes."""
        bid_rows = self.bids()
        n = len(bid_rows)
        by_status = {s: 0 for s in ("run", "yield", "starved", "vetoed")}
        winners: dict = {}
        starved: dict = {}
        vetoed: dict = {}
        att_sum = 0.0
        ticks = {r["tick"] for r in bid_rows}
        for r in bid_rows:
            by_status[r["status"]] += 1
            if r["status"] == "run":
                winners[r["label"]] = winners.get(r["label"], 0) + 1
                att_sum += r["attention"]
            elif r["status"] == "starved":
                starved[r["label"]] = starved.get(r["label"], 0) + 1
            elif r["status"] == "vetoed":
                vetoed[r["label"]] = vetoed.get(r["label"], 0) + 1
        arb_rows = [r for r in self._rows if r.get("kind") == "arbiter"]
        return {
            "clears": len(ticks), "bids": n,
            **by_status,
            "clear_rate": by_status["run"] / n if n else 0.0,
            "mean_winner_attention": att_sum / by_status["run"]
            if by_status["run"] else None,
            "top_winners": sorted(winners.items(),
                                  key=lambda kv: (-kv[1], kv[0]))[:5],
            "most_starved": sorted(starved.items(),
                                   key=lambda kv: (-kv[1], kv[0]))[:5],
            "most_vetoed": sorted(vetoed.items(),
                                  key=lambda kv: (-kv[1], kv[0]))[:5],
            "arbiter": {
                "calls": len(arb_rows),
                "divergent": sum(1 for r in arb_rows if r["divergent"]),
                "last_pick": arb_rows[-1]["pick"] if arb_rows else None,
            },
        }

    def veto_reasons(self) -> dict:
        """The veto law, explained: which factor was zero, per label.

        Reads only the stored floats — the market's own numbers at clear
        time, never re-derived. This is the diagnostic the docs promised
        ("fix the factor; don't bypass the market") with the evidence
        attached.
        """
        out: dict = {}
        for r in self.bids():
            if r["status"] != "vetoed":
                continue
            entry = out.setdefault(
                r["label"], {"count": 0, "zero_factors": []}
            )
            entry["count"] += 1
            for f in FACTORS:
                if r[f] == 0.0 and f not in entry["zero_factors"]:
                    entry["zero_factors"].append(f)
        return out

    # ------------------------------------------------------------------
    # persistence (the host's durable copy; the organism never needs it)
    # ------------------------------------------------------------------
    def to_jsonl(self) -> str:
        return "\n".join(
            json.dumps(r, sort_keys=True) for r in self._rows
        ) + ("\n" if self._rows else "")

    @classmethod
    def from_jsonl(cls, text: str) -> "MarketLog":
        log = cls(keep=None)  # loading is for analysis: keep everything
        for line in text.splitlines():
            if line.strip():
                log._rows.append(json.loads(line))
        return log

    def __len__(self) -> int:
        return len(self._rows)
