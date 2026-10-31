"""TEMPLATE — your own organism in five blanks.

Copy this file, fill the TODOs, run it. Everything else (market, memory,
sleep, conservation audits, save/load) comes from the kernel.

The checklist, in order:
  1. WHY      declare purpose roots and children (nothing runs without one)
  2. DRIVES   add tensions — they are where urgency comes from
  3. WORLD    seed the graph with the entities your organism cares about
  4. SCRIPTS  spawn trigger+action pairs; each relieves some tension
  5. BODY     Runtime(top_k=N) and register your component
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from cognitive_ecology import Outcome, Runtime, Script  # noqa: E402


# TODO 4a: write your actions. Keep them small; an agent is a POPULATION.
def act_example(ctx) -> Outcome:
    # ctx.tensions / ctx.graph / ctx.why / ctx.emit / ctx.recent / ctx.novelty
    ctx.tensions.relieve("TODO_drive", 0.5)
    return Outcome(True, "what success looks like")


class MyOrganism:
    """TODO 5: name it. bid() relays the script population; act() fires."""

    id = "TODO_name"           # component id (must be unique)
    why_node = "why:TODO"      # declared below — nothing runs without it

    def __init__(self, rt: Runtime):
        rt.ecology.spawn(Script(
            name="TODO_script",       # what it does, in one word
            why_node=self.why_node,
            owner=self.id,
            relieves=("TODO_drive",),  # which tensions it discharges
            focus=("TODO:node",),      # which graph nodes it watches
            when=lambda ctx: True,     # opportunity: when MAY it act?
            act=act_example,
        ), tick=rt.tick_no)
        # TODO 4b: more scripts. Vary relieves/focus/when. Let them compete.

    def bid(self, ctx):
        return ctx.ecology.bids(ctx, owner=self.id)

    def act(self, ctx, label):
        return ctx.ecology.fire(label, ctx)


def build_world() -> Runtime:
    rt = Runtime(seed=7, top_k=2)  # TODO 5: the action budget per tick

    # TODO 1: purpose. One root, a few children. Statements, not tasks.
    rt.declare_why("TODO why does this organism exist", node_id="why:root")
    rt.declare_why("TODO a sub-purpose", parent="why:root", node_id="why:TODO")

    # TODO 2: drives. growth rates are the organism's temperament.
    rt.tensions.add("TODO_drive", growth=0.03, description="...")

    # TODO 3: world. Seed the entities; memory will grow the rest.
    rt.graph.upsert("TODO:node", "TODO_kind", {"TODO": "prop"}, tick=0)

    rt.register(MyOrganism(rt))
    return rt


if __name__ == "__main__":
    rt = build_world()
    for report in rt.run(50):
        if report.ran:
            print(f"tick {report.tick}: {', '.join(report.ran)}")
    print(rt.report())
    # persistence is two lines:
    #   rt.save("runs/my_organism")
    #   rt2 = Runtime.load("runs/my_organism", attach=lambda r: r.register(MyOrganism(r)))
