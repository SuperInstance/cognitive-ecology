"""The attestation economy: use it or lose it, in sixty lines.

Two purposes are born together. One is served every day; the other is
left alone. Watch the unserved purpose lose market strength, lapse to
questionable, and return only through a recorded act of re-justification
— first WITHOUT service (it lapses again), then WITH it (it holds).

Zero LLM calls. Zero keys.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from cognitive_ecology import (  # noqa: E402
    AttentionBid, Outcome, Runtime, WhyState,
)

HORIZON = 120
rt = Runtime(seed=7, top_k=2, attestation_horizon=HORIZON)

rt.declare_why("stay alive", node_id="why:root")
rt.declare_why("forage for energy", parent="why:root", node_id="why:forage")
rt.declare_why("archive the old logs", parent="why:root", node_id="why:archive")
rt.tensions.add("energy", growth=0.03)
rt.tensions.add("order", growth=0.02)


class Worker:
    id, why_node = "worker", "why:forage"

    def bid(self, ctx):
        yield AttentionBid(
            src=self.id, label="worker:forage",
            urgency=max(0.4, ctx.tensions.level("energy")),
            justification=ctx.why.justification(self.why_node),
            opportunity=1.0, novelty=1.0, expected_value=1.0,
        )

    def act(self, ctx, label):
        ctx.tensions.relieve("energy", 0.35)
        return Outcome(True, "foraged")


class Archivist:
    id, why_node = "archivist", "why:archive"
    on = False

    def bid(self, ctx):
        if not self.on:
            return
        yield AttentionBid(
            src=self.id, label="archivist:file",
            urgency=max(0.4, ctx.tensions.level("order")),
            justification=ctx.why.justification(self.why_node),
            opportunity=1.0, novelty=1.0, expected_value=1.0,
        )

    def act(self, ctx, label):
        ctx.tensions.relieve("order", 0.4)
        return Outcome(True, "filed logs")


rt.register(Worker())
archivist = Archivist()
rt.register(archivist)

print(f"attestation horizon: {HORIZON} ticks — liveness is a subscription")
print(f"{'tick':>5} {'served just':>12} {'unserved just':>14}  event")
lapses = revives = 0
for tick in range(1, 481):
    note = ""
    if tick == 150 and rt.why.node("why:archive").state is WhyState.UNKNOWN:
        rt.why.revive("why:archive", "re-justified (but hired nobody)", tick)
        revives += 1
        note = "REVIVED without service -> parole (justification 0.5)"
    if tick == 300 and rt.why.node("why:archive").state is WhyState.UNKNOWN:
        rt.why.revive("why:archive", "the archive matters again", tick)
        archivist.on = True  # this time someone serves it
        revives += 1
        note = "REVIVED and served (archivist joins)"
    r = rt.tick()
    lapses += len(r.lapsed)
    if r.lapsed:
        note = f"LAPSED (questionable, not deleted): {','.join(r.lapsed)}"
    if tick % 60 == 0 or note:
        print(f"{tick:>5} {rt.why.justification('why:forage'):>12.3f} "
              f"{rt.why.justification('why:archive'):>14.3f}  {note}")

c = rt.why.conservation()
print("\n--- the law held ---")
print(f"lapses: {lapses}, revives: {revives}")
print(f"ever declared: {c['ever_declared']} (nothing deleted)  "
      f"invariant_ok: {c['invariant_ok']}")
print("lesson 1: revival without service buys exactly one more horizon.")
print("lesson 2: revival WITH service holds — use it or lose it.")
