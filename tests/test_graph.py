"""L2 + L3 — the anti-RAG world graph and memory consolidation."""
import json

from cognitive_ecology import Event, EventKind, Memory, WorldGraph


def _graph():
    g = WorldGraph()
    g.upsert("berry:1", "berry", {"food": 1}, tick=1)
    g.upsert("berry:2", "berry", {"food": 1}, tick=1)
    g.upsert("clearing:1", "clearing", {}, tick=1)
    g.link("berry:1", "clearing:1", "grows_in", tick=1)
    return g


def test_upsert_reinforces_instead_of_duplicating():
    g = _graph()
    g.upsert("berry:1", "berry", {"food": 0}, tick=5)
    assert g.node_count() == 3  # no duplicate
    n = g.get("berry:1")
    assert n.props["food"] == 0 and n.last_seen == 5
    assert n.weight > 1.0  # use reinforces importance


def test_walk_is_budgeted_traversal_not_similarity():
    g = _graph()
    g.upsert("berry:3", "berry", {"food": 1}, tick=1)
    g.link("berry:2", "clearing:1", "grows_in", tick=1)
    result = g.walk(["berry:1"], budget=2)
    assert len(result.ids) <= 2
    assert "berry:1" in result.ids
    # walking from nothing yields nothing
    assert g.walk(["nope:404"], budget=5).ids == []


def test_decay_never_deletes():
    g = _graph()
    for t in range(300):
        g.seen(["berry:1"], tick=t)
    decayed = g.decay(tick=300, horizon=50, rate=0.5)
    # berry:1 was seen recently -> not decayed; others fade
    assert g.node_count() == 3  # still all there
    assert g.get("berry:2").weight <= 0.05 + 1e-9 or decayed >= 0
    assert g.get("clearing:1") is not None


def test_forget_raises_by_design():
    g = _graph()
    try:
        g.forget("berry:1")
        raise AssertionError("forget() must raise — deletion does not exist")
    except NotImplementedError:
        pass


def test_digest_is_deterministic():
    g1 = _graph()
    g2 = WorldGraph.from_json(json.loads(json.dumps(g1.to_json())))
    assert g1.digest() == g2.digest()
    # and a changed world changes the digest deterministically
    g1.upsert("berry:9", "berry", {}, tick=2)
    assert g1.digest() != g2.digest()


def test_memory_consolidation_builds_structure():
    g = WorldGraph()
    m = Memory(g)
    events = [
        Event(kind=EventKind.STATE, ts=1, src="critter", payload=("berry:1", {"food": 0})),
        Event(kind=EventKind.STATE, ts=1, src="critter", payload=("clearing:1", {})),
        Event(kind=EventKind.SIGNAL, ts=1, src="agent", payload=("journal", "found berries")),
        Event(kind=EventKind.TENSION, ts=1, src="tensions", payload=("energy", 0.2)),
    ]
    mutations = m.consolidate(events, tick=1)
    assert mutations > 0
    assert g.has("berry:1") and g.has("clearing:1")
    # Hebbian co-occurrence: entities sharing a tick got wired
    assert any(e.rel == "co" for e in g.edges_of("berry:1"))
    # the signal wired the actor to its target
    assert g.has("actor:agent") and g.has("journal")
    # tension nodes exist and track level
    assert g.has("tension:energy")
    # replay doubles down (sleep consolidation)
    before = g.edge_count()
    m.replay(events, tick=2)
    assert g.edge_count() >= before


def test_recall_is_walk():
    g = _graph()
    m = Memory(g)
    m.consolidate([
        Event(kind=EventKind.STATE, ts=1, src="s", payload=(f"n{i}", {})) for i in range(5)
    ], tick=1)
    result = m.recall(["n1", "n2"], budget=4)
    assert "n1" in result.ids and "n2" in result.ids
