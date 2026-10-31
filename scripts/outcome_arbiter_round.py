#!/usr/bin/env python3
"""Round 14 — the outcome-arbiter, live (typesafe/jev under a scorecard).

Round 005 wired jev into the executive's tie-break and counted 50
divergences in 50 calls — but a divergence count is not a value. This
round re-runs that organism with ADR-0013's scorecard attached: every
jev pick is scored by realized outcome (calibration + base-rate
comparison), and a value-destroying or miscalibrated arbiter gets
benched mid-run, silently degrading the organism back to its
deterministic shadow.

The experiment: are jev's overrides worth their cost, or does the
immune system catch them?

    PYTHONPATH=src python3 scripts/outcome_arbiter_round.py
"""
from __future__ import annotations

import os
import random
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from cognitive_ecology import (  # noqa: E402
    ArbiterScorecard, AttentionBid, Outcome, Runtime,
)
from cognitive_ecology.agents import DecisionArbiter  # noqa: E402

TICKS = 60
SLOTS = 2
WINDOW = 25  # bench only after this much evidence

# seeded action profiles: (label, urgency, success_p, true success rate)
PROFILES = [
    ("forager", 0.85, 0.90, 0.90),   # honest: claims 0.9, succeeds 0.9
    ("scout", 0.80, 0.90, 0.40),     # overconfident: claims 0.9, succeeds 0.4
    ("archivist", 0.75, 0.40, 0.40), # humble: claims 0.4, succeeds 0.4
    ("wanderer", 0.70, 0.60, 0.60),  # honest
]


class SeededWorker:
    """A component with a fixed self-model and a seeded true success rate."""

    def __init__(self, cid, why_node, label, urgency, success_p, true_rate, rng):
        self.id = cid
        self.why_node = why_node
        self.label = label
        self.urgency = urgency
        self.success_p = success_p
        self.true_rate = true_rate
        self._rng = rng

    def bid(self, ctx):
        jitter = 0.75 + 0.5 * self._rng.random()
        yield AttentionBid(
            src=self.id, label=f"{self.id}:{self.label}",
            urgency=min(1.0, self.urgency * jitter),
            justification=ctx.why.justification(self.why_node),
            opportunity=1.0, novelty=1.0, expected_value=1.0,
            success_p=self.success_p,
        )

    def act(self, ctx, label):
        ok = self._rng.random() < self.true_rate
        if ok:
            ctx.tensions.relieve("energy", 0.1)
        return Outcome(ok, "succeeded" if ok else "failed")


def main() -> int:
    rng = random.Random(21)
    rt = Runtime(seed=21, top_k=SLOTS, attestation_horizon=400,
                 idle_window=999)
    rt.tensions.add("energy", growth=0.02)
    rt.declare_why("stay alive", node_id="why:root")

    arbiter = None
    scorecard = None
    ledger = None
    # Settings.from_env() reads the repo .env (gitignored) if present
    from ecology.config import Settings
    settings = Settings.from_env()
    if settings.typesafe_api_key:
        from ecology.llm.base import DecisionRequest
        from ecology.llm.ledger import Ledger
        from ecology.llm.typesafe import TypeSafeClient

        ledger = Ledger(REPO / settings.ledger_path)
        jev = TypeSafeClient(settings, ledger=ledger)

        def decide_fn(state, questions):
            resp = jev.decide(
                DecisionRequest(state=state, questions=questions),
                role="outcome-arbiter",
            )
            return {name: a.value for name, a in resp.answers.items()}

        arbiter = DecisionArbiter(decide_fn)
        scorecard = ArbiterScorecard(name="jev", window=WINDOW)
        rt.executive.arbiter = arbiter
        rt.executive.scorecard = scorecard
        print("arbiter: live (typesafe/jev) under a scorecard "
              f"(window {WINDOW}, bench on Brier>0.25 or base-rate margin 0.10)")
    else:
        print("arbiter: none (keyless deterministic clearing)")

    for cid, urgency, p, rate in PROFILES:
        rt.declare_why(f"be the {cid}", parent="why:root", node_id=f"why:{cid}")
        rt.register(SeededWorker(cid, f"why:{cid}", cid, urgency, p, rate,
                                 random.Random(hash(cid) % 2**31)))

    bench_tick = None
    for tick in range(1, TICKS + 1):
        rt.tick()
        if (scorecard is not None and scorecard.benched
                and bench_tick is None):
            bench_tick = scorecard.bench.tick
            print(f"  tick {tick}: BENCHED — {scorecard.bench.reason}")

    print(f"\n--- outcome-arbiter receipts ({TICKS} ticks) ---")
    ex = rt.executive
    print(f"arbiter calls   : {ex.arbiter_calls}")
    print(f"divergences     : {ex.last_divergence}")
    if arbiter is not None:
        print(f"adapter errors  : {arbiter.errors}")
    if scorecard is not None:
        print()
        print(scorecard.summary())

    # receipt file
    lines = [
        "# Round 14 — the outcome-arbiter, live",
        "",
        f"*Run: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} — "
        f"{TICKS} ticks, {SLOTS} slots; arbiter "
        f"{'live (typesafe/jev)' if arbiter else 'none (keyless)'} under an "
        f"ArbiterScorecard (window {WINDOW}).*",
        "",
        "## The scorecard",
        "",
        "```",
        scorecard.summary() if scorecard else "(no arbiter attached)",
        "```",
        "",
        f"- arbiter calls: {ex.arbiter_calls}; "
        f"divergences: {ex.last_divergence}",
    ]
    if scorecard is not None:
        lines += [
            f"- calibration: "
            f"{scorecard.calibration.verdict('arbiter:jev')}",
            f"- divergent picks: {scorecard.divergent_successes}/"
            f"{scorecard.divergent_picks} succeeded "
            f"(base rate {scorecard.base_rate:.3f})"
            if scorecard.base_rate is not None else "- (no base rate)",
        ]
        if scorecard.benched:
            lines.append(
                f"- BENCHED at tick {scorecard.bench.tick}: "
                f"{scorecard.bench.reason}")
        else:
            lines.append("- standing: not benched in this run")
    lines.append("")
    lines.append("---\n*Triage: see JOURNAL round 14.*")
    out = REPO / "library" / "rounds" / "014-outcome-arbiter.md"
    out.write_text("\n".join(lines))
    print(f"\nwritten: {out}")
    if ledger is not None:
        ledger.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
