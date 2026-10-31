#!/usr/bin/env python3

"""Round 5 (live) — the decision model as the market's tie-breaker.

The decision-model integration question (docs/08, OPEN_QUESTIONS #3):
where exactly do typed, calibrated choices enter the kernel? This round
runs the experiment at the executive's arbiter hook — the ONE bounded
decision the kernel delegates: which contender joins the leading bid as
the tick's second winner.

Two measurements, both with receipts:

1. ARBITRATION: jev (typesafe.ai) breaks the last-slot contention live.
   Cost, latency, confidence, and how often it disagrees with the
   deterministic shadow (divergence is not a failure — it is the price
   and the point of judgment).
2. CALIBRATION: every component claims a success probability on each
   bid (success_p); outcomes are seeded; the runtime scores every claim.
   Per-component Brier scores tell us whose self-model is honest.

Zero-LLM fallback: with no TYPESAFE_API_KEY the arbiter is skipped and
the round runs keyless (deterministic clearing) — the experiment shape
is identical, only the delegation is absent.

    PYTHONPATH=src python3 scripts/decision_arbiter_round.py
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from cognitive_ecology import (  # noqa: E402
    AttentionBid, Executive, Outcome, Runtime,
)
from cognitive_ecology.agents import DecisionArbiter  # noqa: E402
from cognitive_ecology.attention import AttentionMarket  # noqa: E402

TICKS = 50
SLOTS = 2

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
        jitter = 0.75 + 0.5 * self._rng.random()  # seeded per component
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
    import random

    rng = random.Random(21)
    rt = Runtime(seed=21, top_k=SLOTS, attestation_horizon=400)
    rt.tensions.add("energy", growth=0.02)
    rt.declare_why("stay alive", node_id="why:root")
    rt.executive = Executive(
        AttentionMarket(), bus=rt.bus, max_actions=SLOTS,
    )  # rebuilt below with arbiter if key present

    arbiter = None
    decide_fn = None
    if os.environ.get("TYPESAFE_API_KEY"):
        from ecology.config import Settings
        from ecology.llm.base import DecisionRequest
        from ecology.llm.ledger import Ledger
        from ecology.llm.typesafe import TypeSafeClient

        settings = Settings.from_env()
        ledger = Ledger(REPO / settings.ledger_path)
        jev = TypeSafeClient(settings, ledger=ledger)

        def decide_fn(state, questions):  # noqa: F811
            resp = jev.decide(
                DecisionRequest(state=state, questions=questions),
                role="market-arbiter",
            )
            return {name: a.value for name, a in resp.answers.items()}

        arbiter = DecisionArbiter(decide_fn)
        rt.executive = Executive(
            AttentionMarket(), bus=rt.bus, max_actions=SLOTS, arbiter=arbiter,
        )
        print("arbiter: live (typesafe/jev)")
    else:
        print("arbiter: none (keyless deterministic clearing)")

    for cid, urgency, p, rate in PROFILES:
        rt.declare_why(f"be the {cid}", parent="why:root", node_id=f"why:{cid}")
        rt.register(SeededWorker(cid, f"why:{cid}", cid, urgency, p, rate,
                                 random.Random(hash(cid) % 2**31)))

    started = time.monotonic()
    rt.run(TICKS)
    wall = time.monotonic() - started

    print(f"\n--- arbitration receipts ({TICKS} ticks, {wall:.1f}s wall) ---")
    ex = rt.executive
    print(f"arbiter calls   : {ex.arbiter_calls}")
    print(f"divergences     : {ex.last_divergence}")
    if arbiter is not None:
        print(f"adapter calls   : {arbiter.calls}")
        print(f"adapter errors  : {arbiter.errors}")
        if arbiter.last_error:
            print(f"last error      : {arbiter.last_error[:200]}")
        print(f"last choice     : {arbiter.last_choice} "
              f"(confidence {arbiter.last_confidence})")

    print("\n--- calibration receipts (per component) ---")
    print(f"{'component':>10} {'claims':>7} {'claimed p':>10} {'true rate':>10} "
          f"{'brier':>7}  verdict")
    for cid, urgency, p, rate in PROFILES:
        recs = rt.calibration.records(claimer=cid)
        if not recs:
            print(f"{cid:>10} {0:>7}")
            continue
        claimed = sum(r.predicted for r in recs) / len(recs)
        realized = sum(r.realized for r in recs) / len(recs)
        brier = rt.calibration.brier(claimer=cid)
        verdict = "calibrated" if brier <= 0.25 else "MISCALIBRATED"
        print(f"{cid:>10} {len(recs):>7} {claimed:>10.2f} {realized:>10.2f} "
              f"{brier:>7.3f}  {verdict}")
    print(f"overall brier   : {rt.calibration.brier():.3f}")

    # receipt file
    lines = [
        "# Round 5 — the decision model as the market's tie-breaker",
        "",
        f"*Run: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} — "
        f"{TICKS} ticks, {SLOTS} slots; arbiter "
        f"{'live (typesafe/jev)' if arbiter else 'none (keyless)'}.*",
        "",
        "## Arbitration",
        "",
        f"- arbiter calls: **{ex.arbiter_calls}**  "
        f"divergences from deterministic shadow: **{ex.last_divergence}**",
    ]
    if arbiter is not None:
        lines.append(f"- adapter calls: {arbiter.calls}; errors: "
                     f"{arbiter.errors}; last choice: {arbiter.last_choice} "
                     f"(confidence {arbiter.last_confidence})")
        if arbiter.last_error:
            lines.append(f"- last error: `{arbiter.last_error[:200]}`")
    lines += [
        "",
        "## Calibration (success_p claims vs seeded outcomes)",
        "",
        "| component | claims | claimed p | true rate | Brier | verdict |",
        "|---|---|---|---|---|---|",
    ]
    for cid, urgency, p, rate in PROFILES:
        recs = rt.calibration.records(claimer=cid)
        if recs:
            claimed = sum(r.predicted for r in recs) / len(recs)
            realized = sum(r.realized for r in recs) / len(recs)
            brier = rt.calibration.brier(claimer=cid)
            lines.append(
                f"| {cid} | {len(recs)} | {claimed:.2f} | {realized:.2f} "
                f"| {brier:.3f} | "
                f"{'calibrated' if brier <= 0.25 else 'MISCALIBRATED'} |")
    lines += [
        "",
        f"Overall Brier: **{rt.calibration.brier():.3f}** "
        "(0 = perfect foresight, 0.25 = honest coin flip)",
        "",
        "## Reading",
        "",
        "- The scout (claims 0.90, truly 0.40) should land MISCALIBRATED —",
        "  that is the immune system working: confident-and-wrong is now",
        "  measurable, per component, from the organism's own receipts.",
        "- Divergence between the jev arbiter and the deterministic shadow",
        "  is not a failure metric; it is the measurement of judgment.",
        "  The shadow is what you get for free; the question is whether the",
        "  paid divergence correlates with better outcomes.",
        "",
    ]
    out = REPO / "library" / "rounds" / "005-decision-arbiter.md"
    out.write_text("\n".join(lines))
    print(f"\nwritten: {out}")
    if arbiter is not None:
        ledger.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
