"""Elder Merle: a game NPC whose memory survives server restarts.

Run once -> two player visits, then save + reload into a FRESH Runtime
and visit again: Merle's world graph, script track records, commitments
and WHY tree all persisted. Behavior is code; history is state files.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from cognitive_ecology import (  # noqa: E402
    EventKind, Identity, Outcome, Runtime, Script,
)

SAVE_DIR = Path(__file__).resolve().parents[2] / "runs" / "merle"

RUMORS = {
    "the old mill": "The miller's boy swears the wheel turns on windless nights.",
    "the north road": "Merchant caravans started paying double for guards.",
    "the pond": "Fishermen say something big moved under the ice last winter.",
}


def act_greet(ctx) -> Outcome:
    player = ctx.graph.get("player:you")
    visits = (player.props.get("visits", 0) if player else 0) + 1
    ctx.graph.upsert("player:you", "player", {"visits": visits}, tick=ctx.tick)
    ctx.emit(EventKind.SIGNAL, ("player:you", "Evenin'. Ask me anything, traveler."),
             src="merle")
    return Outcome(True, f"greeted (visit {visits})")


def act_gossip(ctx) -> Outcome:
    asked = [e.payload[1] for e in ctx.recent(10)
             if e.kind is EventKind.SIGNAL and e.payload[0] == "merle"]
    topic = None
    for rumor in RUMORS:
        if any(rumor in a for a in asked):
            topic = rumor
            break
    if topic is None:
        return Outcome(False, "nothing asked about")
    nid = f"rumor:{topic.replace(' ', '-')}"
    ctx.graph.upsert(nid, "rumor", {"text": RUMORS[topic]}, tick=ctx.tick)
    ctx.graph.link("player:you", nid, "asked_about", tick=ctx.tick)
    ctx.tensions.relieve("curiosity", 0.6)
    ctx.emit(EventKind.SIGNAL, ("player:you", RUMORS[topic]), src="merle")
    return Outcome(True, f"gossiped about {topic}")


def act_reminisce(ctx) -> Outcome:
    """The persistence payoff: recall what the player asked BEFORE the restart."""
    asked = sorted(
        e.dst for e in ctx.graph.edges_of("player:you")
        if e.rel == "asked_about"
    )
    if not asked:
        return Outcome(False, "no shared history yet")
    topics = [a.replace("rumor:", "").replace("-", " ") for a in asked]
    ctx.emit(EventKind.SIGNAL,
             ("player:you", f"You asked me about {', '.join(topics)} before."),
             src="merle")
    ctx.tensions.relieve("nostalgia", 0.4)
    return Outcome(True, f"remembered: {topics}")


class Merle:
    id = "merle"
    why_node = "why:merle"

    def __init__(self, rt: Runtime):
        t = rt.tick_no
        rt.ecology.adopt(Script(
            name="greet", why_node="why:merle", owner="merle",
            relieves=("hospitality",), focus=("player:you",),
            when=lambda ctx: _player_present(ctx), act=act_greet,
        ), tick=t)
        rt.ecology.adopt(Script(
            name="gossip", why_node="why:merle", owner="merle",
            relieves=("curiosity",), focus=("player:you",),
            when=lambda ctx: _player_present(ctx), act=act_gossip,
        ), tick=t)
        rt.ecology.adopt(Script(
            name="reminisce", why_node="why:merle", owner="merle",
            relieves=("nostalgia",), focus=("player:you",),
            when=lambda ctx: _player_present(ctx), act=act_reminisce,
        ), tick=t)

    def bid(self, ctx):
        return ctx.ecology.bids(ctx, owner="merle")

    def act(self, ctx, label):
        return ctx.ecology.fire(label, ctx)


def _player_present(ctx) -> bool:
    node = ctx.graph.get("player:you")
    return node is not None and (ctx.tick - node.last_seen) <= 3


def attach(rt: Runtime) -> None:
    """Rebuild Merle in code; adopt his saved track records."""
    rt.register(Merle(rt))


def build_world() -> Runtime:
    rt = Runtime(seed=13, top_k=2)
    rt.declare_why("the tavern is worth keeping", node_id="why:tavern")
    rt.declare_why("Merle keeps the stories and the regulars",
                   parent="why:tavern", node_id="why:merle")
    rt.tensions.add("hospitality", growth=0.04, description="a keeper's duty")
    rt.tensions.add("curiosity", growth=0.03, description="gossip wants telling")
    rt.tensions.add("nostalgia", growth=0.02, description="the past wants retelling")
    rt.graph.upsert("tavern:main", "place", {"name": "The Bent Spoon"}, tick=0)
    rt.graph.upsert("player:you", "player", {"visits": 0}, tick=0)
    rt.identity = Identity(name="elder-merle", why=rt.why)
    attach(rt)
    return rt


def player_visit(rt: Runtime, label: str, asks: list) -> None:
    print(f"\n[{label}] the player walks in")
    # the player's arrival refreshes their presence in the world graph
    rt.graph.seen(["player:you"], tick=rt.tick_no) if rt.graph.has("player:you") \
        else rt.graph.upsert("player:you", "player", {"visits": 0}, tick=rt.tick_no)
    for ask in asks:
        rt.bus.emit(EventKind.SIGNAL, ("merle", ask), src="player:you", ts=rt.tick_no)
    reports = rt.run(4)
    for r in reports:
        if r.ran:
            print(f"   tick {r.tick}: merle did {', '.join(r.ran)}")
    said = [e.payload[1] for e in rt.bus.window(12)
            if e.kind is EventKind.SIGNAL and e.payload[0] == "player:you"]
    for line in said[-2:]:
        print(f'   merle: "{line}"')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fresh", action="store_true", help="wipe the save first")
    args = ap.parse_args()
    if args.fresh and SAVE_DIR.exists():
        import shutil
        shutil.rmtree(SAVE_DIR)

    if (SAVE_DIR / "state.json").exists():
        print(f"[boot] loading Merle from {SAVE_DIR} (the 'server restarted')")
        rt = Runtime.load(str(SAVE_DIR), attach=attach)
    else:
        print("[boot] first boot: building Merle from code")
        rt = build_world()

    # ---------------------------------------------------------------- visits
    player_visit(rt, "visit 1", ["tell me about the old mill"])
    player_visit(rt, "visit 2", ["what about the north road?"])

    # ---------------------------------------------------------------- save
    rt.identity.observe_style(rt.ecology.alive())
    rt.save(str(SAVE_DIR))
    print(f"\n[save] state written to {SAVE_DIR}/")
    print("       (behavior is code; history is files — the split that"
          " makes restarts survivable)")

    # ---------------------------------------------------------------- restart
    print("\n[restart] constructing a brand-new Runtime and loading state...")
    rt2 = Runtime.load(str(SAVE_DIR), attach=attach)
    player_visit(rt2, "visit 3 (after restart)",
                 ["do you remember what I asked you?"])
    print("\nmerle's self-model:")
    print(rt2.identity.drift() if rt2.identity else "(no identity)")
    print("\nshared history in the world graph:")
    for e in sorted(rt2.graph.edges_of("player:you"), key=lambda e: e.rel):
        print(f"   {e.rel}: {e.src} -> {e.dst} (w={e.weight:.2f})")


if __name__ == "__main__":
    main()
