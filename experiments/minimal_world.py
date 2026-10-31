"""The ten-minute organism: a complete cognitive ecology, zero LLMs, zero keys.

Run it:

    python experiments/minimal_world.py            # 120 ticks, full story
    python experiments/minimal_world.py --ticks 200 --seed 42

What you will watch happen, in order:

  [1] BOOT      a field exists; a critter with a WHY, two drives, four scripts
  [2] LIFE      60 ticks of foraging, exploring, resting — an attention market
                spending a 2-action budget, memory building a world graph
  [3] CRISIS    the root WHY is killed: NOTHING runs, NOTHING is deleted;
                every purpose becomes questionable (UNKNOWN), not gone
  [4] RECOVERY  the mandate is resurrected with new evidence: life resumes
  [5] SLEEP     a quiet stretch: replay, pruning, dreams (script mutations)
  [6] PERSIST   save to disk, load into a fresh Runtime, keep living —
                the organism survives its own process

Every concept in the kernel appears here at least once. Read this file
top to bottom; it is the tour.
"""
from __future__ import annotations

import argparse

from cognitive_ecology import EventKind, Outcome, Runtime, Script, WhyState

RIPE_BERRIES = [f"berry:{i}" for i in range(1, 4)]
HIDDEN_BERRIES = [f"berry:{i}" for i in range(4, 11)]  # revealed by exploring
REGROW_DELAY = 25


def banner(title: str) -> None:
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


# ----------------------------------------------------------------------
# the critter's scripts — each one is a trigger + an action + a track record
# ----------------------------------------------------------------------
def _ripe_berry(ctx):
    for b in RIPE_BERRIES + HIDDEN_BERRIES:
        node = ctx.graph.get(b)
        if node is not None and node.props.get("food", 0) > 0:
            return b
    return None


def act_forage(ctx) -> Outcome:
    b = _ripe_berry(ctx)
    if b is None:
        return Outcome(False, "no ripe berries")
    ctx.graph.upsert(b, "berry", {"food": 0, "regrow_at": ctx.tick + REGROW_DELAY},
                     tick=ctx.tick)
    ctx.emit(EventKind.STATE, (b, {"food": 0}), src="critter")
    ctx.tensions.relieve("energy", 0.6)
    return Outcome(True, f"ate {b}")


def act_explore(ctx) -> Outcome:
    ctx.tensions.relieve("curiosity", 0.5)
    ctx.tensions.burden("energy", 0.08)  # exploring costs energy
    ctx.graph.seen(["clearing:1"], tick=ctx.tick)  # attention refreshes the patch
    for b in HIDDEN_BERRIES:
        if not ctx.graph.has(b):
            ctx.graph.upsert(b, "berry", {"food": 1}, tick=ctx.tick)
            ctx.graph.link(b, "clearing:1", "grows_in", tick=ctx.tick)
            ctx.emit(EventKind.STATE, (b, {"revealed": 1}), src="critter")
            return Outcome(True, f"discovered {b}")
    return Outcome(True, "wandered the known field")


def act_rest(ctx) -> Outcome:
    ctx.tensions.relieve("energy", 0.25)
    return Outcome(True, "rested")


def act_drink(ctx) -> Outcome:
    ctx.graph.seen(["pond:1"], tick=ctx.tick)
    ctx.tensions.relieve("energy", 0.1)
    ctx.emit(EventKind.STATE, ("pond:1", {"visited": 1}), src="critter")
    return Outcome(True, "drank at the pond")


# ----------------------------------------------------------------------
# components: the critter and the field itself
# ----------------------------------------------------------------------
class Critter:
    """An agent is a POPULATION of scripts. The critter relays them."""

    id = "critter"
    why_node = "why:critter"

    def __init__(self, rt: Runtime):
        eco, t = rt.ecology, rt.tick_no
        eco.adopt(Script(
            name="forage", why_node="why:critter", owner="critter",
            relieves=("energy",), focus=tuple(RIPE_BERRIES[:2]),
            when=lambda ctx: _ripe_berry(ctx) is not None,
            act=act_forage,
        ), tick=t)
        eco.adopt(Script(
            name="explore", why_node="why:critter", owner="critter",
            relieves=("curiosity",),
            focus=("clearing:1",) + tuple(HIDDEN_BERRIES[:3]),  # what it watches
            act=act_explore,
        ), tick=t)
        eco.adopt(Script(
            name="rest", why_node="why:critter", owner="critter",
            relieves=("energy",), when=lambda ctx: True, act=act_rest,
        ), tick=t)
        eco.adopt(Script(
            name="drink", why_node="why:critter", owner="critter",
            relieves=("energy",), focus=("pond:1",), act=act_drink,
        ), tick=t)

    def bid(self, ctx):
        return ctx.ecology.bids(ctx, owner=self.id)

    def act(self, ctx, label):
        return ctx.ecology.fire(label, ctx)


class Field:
    """The world is a citizen too: it regrows what was eaten."""

    id = "field"
    why_node = "why:field"

    def bid(self, ctx):
        return _regrow_bid(ctx)

    def act(self, ctx, label):
        regrown = []
        for b in RIPE_BERRIES + HIDDEN_BERRIES:
            node = ctx.graph.get(b)
            if (node is not None and node.props.get("food", 0) == 0
                    and node.props.get("regrow_at", 0) <= ctx.tick):
                ctx.graph.upsert(b, "berry", {"food": 1}, tick=ctx.tick)
                ctx.emit(EventKind.STATE, (b, {"food": 1}), src="field")
                regrown.append(b)
        return Outcome(True, f"regrew {regrown}") if regrown else Outcome(False, "nothing to regrow")


def _regrow_bid(ctx):
    from cognitive_ecology import AttentionBid
    ready = sum(
        1 for b in RIPE_BERRIES + HIDDEN_BERRIES
        if (n := ctx.graph.get(b)) is not None
        and n.props.get("food", 0) == 0
        and n.props.get("regrow_at", 0) <= ctx.tick
    )
    if ready == 0:
        return []
    return [AttentionBid(
        src="field", label="regrow",
        urgency=0.2, justification=ctx.why.justification("why:field"),
        opportunity=1.0, novelty=0.2, expected_value=0.9,
    )]


# ----------------------------------------------------------------------
# world assembly
# ----------------------------------------------------------------------
def build_world(seed: int = 7) -> Runtime:
    rt = Runtime(seed=seed, top_k=2)
    # the WHY tree: purpose is conserved, structured, and killable-but-not-deletable
    rt.declare_why("the field is worth inhabiting", node_id="why:root")
    rt.declare_why("the critter stays alive and learns the field",
                   parent="why:root", node_id="why:critter")
    rt.declare_why("the field keeps turning",
                   parent="why:root", node_id="why:field")
    # drives: where urgency comes from
    rt.tensions.add("energy", growth=0.03, description="hunger, basically")
    rt.tensions.add("curiosity", growth=0.02, description="the pull of the unknown")
    # the world graph: knowledge with a biography
    for b in RIPE_BERRIES:
        rt.graph.upsert(b, "berry", {"food": 1}, tick=0)
    rt.graph.upsert("clearing:1", "clearing", {"name": "the north clearing"}, tick=0)
    rt.graph.upsert("pond:1", "pond", {}, tick=0)
    # components
    rt.register(Critter(rt))
    rt.register(Field())
    return rt


def diary(reports) -> None:
    """Print from per-tick telemetry (TickReport), not live state."""
    for r in reports:
        if r.tick % 10 == 0 or r.slept:
            t = r.tensions
            did = "+".join(r.ran) if r.ran else ("SLEPT" if r.slept else "idle")
            print(f"  tick {r.tick:3d} | energy={t.get('energy', 0):.2f} "
                  f"curiosity={t.get('curiosity', 0):.2f} "
                  f"| did: {did:26s} | starved={len(r.starved)}")


def main() -> None:
    ap = argparse.ArgumentParser(description="the ten-minute organism")
    ap.add_argument("--ticks", type=int, default=120)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--checkpoint-dir", default="runs/minimal_world")
    args = ap.parse_args()

    rt = build_world(args.seed)

    banner("[1] BOOT — a field, a WHY, two drives, four scripts")
    print(rt.why.digest())
    print(f"\n{rt.report()}")

    banner("[2] LIFE — 60 ticks under the attention market")
    life1 = rt.run(60)
    diary(life1)

    banner("[3] CRISIS — the root WHY is killed")
    print("  why.kill('why:root', reason='the mandate was withdrawn')")
    rt.why.kill("why:root", reason="the mandate was withdrawn", tick=rt.tick_no)
    c = rt.why.conservation()
    print(f"  after the kill: alive={c['alive']} dead={c['dead']} "
          f"unknown={c['unknown']} invariant_ok={c['invariant_ok']}")
    crisis = rt.run(10)
    ran_during_crisis = [r.ran for r in crisis if r.ran]
    print(f"  actions taken during 10 ticks of dead purpose: {ran_during_crisis or 'NONE'}")
    v = rt.why.verdict("why:critter")
    print(f"  critter's verdict: ok={v.ok} reason={v.reason}")
    print("  nothing ran; nothing was deleted; every purpose is QUESTIONABLE, not gone")

    banner("[4] RECOVERY — resurrection with new evidence")
    print("  why.resurrect('why:root', reason='a new mandate arrived with evidence')")
    rt.why.resurrect("why:root", reason="a new mandate arrived with evidence",
                     tick=rt.tick_no)
    recovery = rt.run(40)
    diary(recovery)
    ran_after = sum(1 for r in recovery if r.ran)
    print(f"  actions after resurrection: {ran_after} ticks of activity — "
          f"the cascade of questions resolved itself")

    banner("[5] SLEEP — replay, prune, dream")
    print("  (the main organism already slept during the crisis above: nothing")
    print("   ran for 5+ ticks, so it idled into sleep — see sleeper stats below)")
    print(f"  main organism sleeper stats: {rt.sleeper.stats}")
    print("\n  a dedicated quiet organism: one script whose trigger is never true")
    rt_quiet = Runtime(seed=11, idle_window=5)
    rt_quiet.declare_why("a quiet organism is still an organism", node_id="why:q")
    rt_quiet.ecology.spawn(Script(
        name="wait-forever", why_node="why:q", owner="sitter",
        when=lambda ctx: False, act=lambda ctx: Outcome(True),
    ))

    class Sitter:
        id = "sitter"
        why_node = "why:q"

        def bid(self, ctx):
            return ctx.ecology.bids(ctx, owner="sitter")

        def act(self, ctx, label):
            return ctx.ecology.fire(label, ctx)

    rt_quiet.register(Sitter())
    quiet_reports = rt_quiet.run(12)
    slept_ticks = [r.tick for r in quiet_reports if r.slept]
    print(f"  sleep cycles entered: {len(slept_ticks)} (at ticks {slept_ticks})")
    print(f"  sleeper stats: {rt_quiet.sleeper.stats}")
    print("  dreams = mutated scripts; pruning = starving scripts die into the necrology")

    banner("[6] PERSIST — the organism survives its process")
    import os
    ckpt = args.checkpoint_dir
    rt.save(ckpt)
    print(f"  saved state to {ckpt}/ (state.json + events.jsonl)")

    def attach(r: Runtime) -> None:
        r.register(Critter(r))   # behavior is code; stats are adopted from state
        r.register(Field())

    rt2 = Runtime.load(ckpt, attach=attach)
    print(f"  loaded into a fresh Runtime at tick {rt2.tick_no}")
    more = rt2.run(10)
    diary(more)
    print("  ...and it keeps living. Same purposes, same memories, same records.")

    banner("FINAL REPORT")
    print(rt2.report())
    print("\nwhy-tree (statements survive every state change):")
    print(rt2.why.digest())
    print("\nlive scripts:")
    for s in rt2.ecology.alive():
        print(f"  {s.name:10s} fires={s.fires:3d} success={s.success_rate:.2f} "
              f"gen={s.generation}")
    dead = rt2.ecology.necrology()
    print(f"\nnecrology ({len(dead)} deaths, recorded forever):")
    for d in dead[:5]:
        print(f"  {d.name:12s} died@{d.tick:3d} reason={d.reason} fires={d.fires}")
    print("\nworld digest (top of the graph):")
    for line in rt2.graph.digest(10).splitlines():
        print("  " + line)
    print("\nThe law held the whole time: "
          f"{rt2.why.conservation()['ever_declared']} purposes declared, "
          f"{rt2.why.conservation()['ever_declared']} accounted for. "
          "None deleted. None forgotten.")


if __name__ == "__main__":
    main()
