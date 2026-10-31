"""The 60-second heartbeat: the whole kernel in ~80 readable lines.

A WHY, a drive, two scripts, an attention market — and the conservation
law demonstrated live: kill the purpose, watch everything stop without
anything being deleted, then resurrect it with new evidence.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from cognitive_ecology import (  # noqa: E402
    EventKind, Outcome, Runtime, Script,
)

rt = Runtime(seed=7, top_k=1)  # a body with a 1-action-per-tick budget

# L6 — purpose, conserved forever
rt.declare_why("understand why I run", node_id="why:root")
rt.declare_why("demonstrate the conservation law", parent="why:root",
               node_id="why:demo")

# homeostasis — where urgency comes from
rt.tensions.add("curiosity", growth=0.05, description="the pull of the unexamined")

# L4 — an agent is a population of scripts


def act_observe(ctx) -> Outcome:
    # relief (0.03) is smaller than the drive's growth (0.05), so curiosity
    # visibly ACCUMULATES — you can watch the drive and the relief race
    ctx.tensions.relieve("curiosity", 0.03)
    ctx.emit(EventKind.STATE, ("the-kernel", {"observed": 1}), src="tiny")
    return Outcome(True, "looked closely")


def act_wonder(ctx) -> Outcome:
    ctx.tensions.relieve("curiosity", 0.15)
    ctx.emit(EventKind.SIGNAL, ("journal", "what else is conserved?"), src="tiny")
    return Outcome(True, "wondered")


class Tiny:
    """The whole organism: it relays its script population's bids."""

    id = "tiny"
    why_node = "why:demo"

    def __init__(self, rt_: Runtime):
        rt_.ecology.spawn(Script(
            name="observe", why_node="why:demo", owner="tiny",
            relieves=("curiosity",), focus=("the-kernel",), act=act_observe,
        ), tick=0)
        rt_.ecology.spawn(Script(
            name="wonder", why_node="why:demo", owner="tiny",
            relieves=("curiosity",), act=act_wonder,
        ), tick=0)

    def bid(self, ctx):
        return ctx.ecology.bids(ctx, owner="tiny")

    def act(self, ctx, label):
        return ctx.ecology.fire(label, ctx)


rt.register(Tiny(rt))

# ---------------------------------------------------------------- life
# the executive emits a DECISION event per cleared bid, carrying the
# attention value — subscribing to the event log is the observability story
decisions = []
rt.bus.subscribe(lambda e: decisions.append(e.payload), kinds=[EventKind.DECISION])

print("tick  attention  ran                     curiosity")


def show(r):
    """on_tick callback: drain this tick's DECISION events as they happen."""
    for label, src, status, attention in decisions:
        print(f"{r.tick:4d}  {attention:8.4f}  {label:22s} "
              f"{r.tensions['curiosity']:.2f}")
    decisions.clear()


rt.run(10, on_tick=show)

# ---------------------------------------------------------------- crisis
print("\n-- killing the root WHY --")
rt.why.kill("why:root", reason="the demo withdraws its mandate", tick=rt.tick_no)
c = rt.why.conservation()
print(f"after: alive={c['alive']} dead={c['dead']} unknown={c['unknown']}"
      f" absent={c['absent']} invariant_ok={c['invariant_ok']}")
quiet = rt.run(5)
print(f"ticks 11-15: {'nothing runs' if not any(r.ran for r in quiet) else 'SOMETHING RAN?!'}"
      " (purpose is QUESTIONABLE, not gone)")
print(f"tiny's verdict: {rt.why.verdict('why:demo').reason}")

# ---------------------------------------------------------------- recovery
print("\n-- resurrecting with new evidence --")
rt.why.resurrect("why:root", reason="a new mandate arrived", tick=rt.tick_no)
alive_again = rt.run(5)
ran = [", ".join(r.ran) for r in alive_again if r.ran]
print(f"ticks 16-20: {ran or 'nothing'}")

# ---------------------------------------------------------------- the law
print("\n-- the audit --")
final = rt.why.conservation()
print(f"purposes declared: {final['ever_declared']}   accounted for: "
      f"{final['alive'] + final['dead'] + final['unknown'] + final['absent']}")
print(f"invariant_ok: {final['invariant_ok']}")
print(f"necrology records: {len(rt.why.necrology())}")
for rec in rt.why.necrology():
    print(f"  tick {rec.tick:2d}: {rec.node_id} {rec.from_state.value} -> "
          f"{rec.to_state.value} ({rec.reason})")
print("\nNothing was ever deleted. That is the whole idea.")
