"""Integration: whole organisms — heartbeats, conservation, persistence,
sleep, and LLM citizens (mock provider)."""
import tempfile

from cognitive_ecology import (
    EventKind, Identity, Outcome, Runtime, Script, WhyState,
)
from cognitive_ecology.agents import (
    ACTION_LIBRARY_DOC, LLMAgent, MockProvider, StablePrefixSession,
)

BERRIES = [f"berry:{i}" for i in range(1, 4)]
HIDDEN = [f"berry:{i}" for i in range(4, 9)]


def _ripe(ctx):
    return any(
        (ctx.graph.get(b) or type("N", (), {"props": {}})()).props.get("food", 0) > 0
        for b in BERRIES
    )


def _act_forage(ctx):
    for b in BERRIES:
        node = ctx.graph.get(b)
        if node is not None and node.props.get("food", 0) > 0:
            ctx.graph.upsert(b, "berry", {"food": 0}, tick=ctx.tick)
            ctx.emit(EventKind.STATE, (b, {"food": 0}), src="critter")
            ctx.tensions.relieve("energy", 0.6)
            return Outcome(True, f"ate {b}")
    return Outcome(False, "no ripe berries")


def _act_explore(ctx):
    ctx.tensions.relieve("curiosity", 0.5)
    ctx.tensions.burden("energy", 0.08)
    for b in HIDDEN:
        if not ctx.graph.has(b):
            ctx.graph.upsert(b, "berry", {"food": 1}, tick=ctx.tick)
            ctx.graph.link(b, "clearing:1", "grows_in", tick=ctx.tick)
            ctx.emit(EventKind.STATE, (b, {"revealed": 1}), src="critter")
            return Outcome(True, f"found {b}")
    return Outcome(True, "wandered")


def _act_rest(ctx):
    ctx.tensions.relieve("energy", 0.25)
    return Outcome(True, "rested")


class Critter:
    """The classic organism: a WHY, two drives, three scripts."""

    id = "critter"
    why_node = "why:root"

    def __init__(self, rt):
        eco = rt.ecology
        eco.adopt(Script(name="forage", why_node="why:root", owner="critter",
                         relieves=("energy",), focus=tuple(BERRIES),
                         when=_ripe, act=_act_forage), tick=rt.tick_no)
        eco.adopt(Script(name="explore", why_node="why:root", owner="critter",
                         relieves=("curiosity",), focus=("clearing:1",),
                         act=_act_explore), tick=rt.tick_no)
        eco.adopt(Script(name="rest", why_node="why:root", owner="critter",
                         relieves=("energy",), act=_act_rest), tick=rt.tick_no)

    def bid(self, ctx):
        return ctx.ecology.bids(ctx, owner=self.id)

    def act(self, ctx, label):
        return ctx.ecology.fire(label, ctx)


def make_world(seed=7):
    rt = Runtime(seed=seed, top_k=2)
    rt.declare_why("stay alive and learn the field", node_id="why:root")
    rt.tensions.add("energy", growth=0.05)
    rt.tensions.add("curiosity", growth=0.03)
    for b in BERRIES:
        rt.graph.upsert(b, "berry", {"food": 1}, tick=0)
    rt.graph.upsert("clearing:1", "clearing", {}, tick=0)
    rt.register(Critter(rt))
    return rt


def test_organism_runs_and_conserves():
    rt = make_world()
    reports = rt.run(60)
    ran = [r.ran for r in reports if r.ran]
    assert ran, "the critter should have acted at least once"
    c = rt.why.conservation()
    assert c["invariant_ok"] and c["alive"] == 1
    # tension dynamics: energy got relieved somewhere along the way
    tension_events = [e for e in rt.bus.log() if e.kind is EventKind.TENSION]
    assert tension_events
    # memory built world structure from events
    assert rt.graph.edge_count() > 0


def test_killing_the_root_stops_but_preserves_everything():
    rt = make_world()
    rt.run(20)
    rt.why.kill("why:root", reason="mandate withdrawn", tick=20)
    reports = rt.run(10)
    assert all(r.ran == [] for r in reports)   # nothing runs without a WHY
    assert rt.why.conservation()["invariant_ok"]
    assert rt.component("critter") is not None  # the component still exists
    # ...and purpose can come back
    rt.why.resurrect("why:root", "mandate restored", tick=30)
    reports = rt.run(10)
    assert any(r.ran for r in reports)


def test_save_load_round_trip():
    rt = make_world()
    rt.run(35)
    forage_before = rt.ecology.get("forage")
    with tempfile.TemporaryDirectory() as tmp:
        rt.save(tmp)
        rt2 = Runtime.load(tmp, attach=lambda r: r.register(Critter(r)))
    assert rt2.tick_no == 35
    assert rt2.why.conservation() == rt.why.conservation()
    assert rt2.graph.node_count() == rt.graph.node_count()
    assert len(rt2.bus) == len(rt.bus)
    forage_after = rt2.ecology.get("forage")
    assert forage_after.fires == forage_before.fires          # history adopted
    assert forage_after.success_rate == forage_before.success_rate
    # and it keeps living
    reports = rt2.run(15)
    assert any(r.ran for r in reports)


def test_sleep_on_idle_with_dreams_and_pruning():
    rt = Runtime(seed=1, top_k=1, idle_window=5)
    rt.declare_why("just exist", node_id="why:root")
    rt.tensions.add("boredom", growth=0.01)
    # 'winner' relieves boredom (so it outranks zero-urgency 'loser');
    # the flag later removes its opportunity so the world goes idle.
    flag = {"on": True}
    loser = Script(name="loser", why_node="why:root", owner="critter",
                   act=lambda ctx: Outcome(True))
    winner = Script(name="winner", why_node="why:root", owner="critter",
                    relieves=("boredom",), resource="body",
                    when=lambda ctx: flag["on"],
                    act=lambda ctx: Outcome(True))
    rt.ecology.spawn(loser)
    rt.ecology.spawn(winner)

    class Relay:
        id = "critter"
        why_node = "why:root"

        def bid(self, ctx):
            return ctx.ecology.bids(ctx, owner="critter")

        def act(self, ctx, label):
            return ctx.ecology.fire(label, ctx)

    rt.register(Relay())
    rt.run(50)
    assert rt.ecology.get("loser") is None          # starved out via bookkeeping
    assert rt.ecology.necrology()[-1].name == "loser"
    # now the world goes quiet: nothing can act -> idle -> sleep -> dreams
    flag["on"] = False
    before = rt.sleeper.stats.cycles
    rt.run(12)
    assert rt.sleeper.stats.cycles > before
    assert rt.sleeper.stats.dreams >= 1


def test_llm_citizen_with_mock_provider_and_cache_session():
    rt = Runtime(seed=3, top_k=2)
    rt.declare_why("learn things and persist", node_id="why:root")
    rt.tensions.add("curiosity", growth=0.05)
    rt.identity = Identity(name="scout", why=rt.why)
    prefix = (
        "You are scout, a citizen of a cognitive-ecology organism.\n\n"
        "## Action library\n" + ACTION_LIBRARY_DOC + "\n\n"
        "## Output contract\nReply with a JSON array of proposals only."
    )
    session = StablePrefixSession(MockProvider(), prefix, label="scout")
    agent = LLMAgent("scout", "why:root", session, every=5)
    rt.register(agent)
    rt.run(30)
    # the LLM proposed, the ecology accepted some scripts
    assert rt.ecology.population() >= 1
    assert any(s.owner == "scout" for s in rt.ecology.alive())
    # proposals became live scripts that actually fire
    fired = [e for e in rt.bus.log()
             if e.kind is EventKind.NOTE_ON and e.src == "scout"]
    assert fired, "spawned scripts should have fired at least once"
    # the session measured simulated cache hits (frozen prefix reused)
    stats = session.stats()
    assert stats["calls"] >= 3
    assert stats["cached_tokens"] > 0
    assert stats["est_saved_usd"] >= 0
    # conservation held with a model in the loop
    assert rt.why.conservation()["invariant_ok"]


def test_identity_chain_and_stable_introspect():
    rt = make_world()
    ident = Identity(name="critter", why=rt.why)
    rt.identity = ident
    ident.commit("always leave berries to regrow", tick=3)
    ident.commit("prefer the north clearing", tick=9)
    assert ident.verify()
    s1 = ident.introspect()
    ident.commit("third commitment arrives mid-session", tick=12)
    s2 = ident.introspect()
    assert s1 == s2  # memoized: new commitments do NOT rewrite the prefix
    s3 = ident.drift()
    assert s3 != s1 and "third commitment" in s3
    # tampering breaks the chain
    ident._commitments[0].text = "edited history"
    assert not ident.verify()


def test_registering_without_why_is_an_error():
    rt = Runtime()
    try:
        rt.register(Critter(rt))
        raise AssertionError("components without a WHY must be rejected")
    except KeyError:
        pass
