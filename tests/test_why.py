"""L6 — the WHY conservation law is the point of the whole kernel."""
import random

from cognitive_ecology import WhyState, WhyTree


def _tree():
    t = WhyTree()
    t.declare("stay alive", node_id="why:root", tick=1)
    t.declare("find food", parent="why:root", node_id="why:food", tick=2)
    t.declare("learn the field", parent="why:root", node_id="why:learn", tick=3)
    t.declare("map clearings", parent="why:learn", node_id="why:map", tick=4)
    return t


def test_kill_cascades_to_unknown_never_deletion():
    t = _tree()
    t.kill("why:root", reason="mandate withdrawn", tick=10)
    assert t.node("why:root").state is WhyState.DEAD
    # children became questionable, not gone
    assert t.node("why:food").state is WhyState.UNKNOWN
    assert t.node("why:learn").state is WhyState.UNKNOWN
    assert t.node("why:map").state is WhyState.UNKNOWN
    # conservation holds: every node ever declared is still accounted for
    c = t.conservation()
    assert c["invariant_ok"] and c["ever_declared"] == 4
    assert c["dead"] == 1 and c["unknown"] == 3
    # the necrology recorded every transition
    assert len(t.necrology()) == 4  # 1 kill + 3 cascades


def test_revive_after_ancestor_resurrect():
    t = _tree()
    t.kill("why:root", reason="gone dark", tick=10)
    t.resurrect("why:root", "mandate restored by new evidence", tick=12)
    assert t.node("why:root").state is WhyState.ALIVE
    assert t.node("why:learn").state is WhyState.ALIVE
    assert t.node("why:map").state is WhyState.ALIVE
    assert t.conservation()["invariant_ok"]


def test_resurrect_requires_a_reason():
    t = _tree()
    t.kill("why:root", reason="x", tick=5)
    try:
        t.resurrect("why:root", "")
        raise AssertionError("empty reason must be rejected")
    except ValueError:
        pass


def test_heartbeat_question():
    t = _tree()
    assert t.why_should_this_run("why:food")
    t.kill("why:root", reason="withdrawn", tick=9)
    assert not t.why_should_this_run("why:food")
    v = t.verdict("why:map")
    assert not v.ok and v.blocked_at == "why:map"  # most proximate blocker
    # justification: DEAD anywhere in chain is a hard veto
    assert t.justification("why:food") == 0.0


def test_contradictions_detectable():
    t = _tree()
    t.kill("why:root", reason="withdrawn", tick=9)
    # a descendant asserts life while its root is dead: dissonance
    t.revive("why:learn", reason="local rejustification", tick=10)
    assert t.node("why:learn").state is WhyState.ALIVE
    assert any(n.id == "why:learn" for n in t.contradictions())


def test_park_and_activate():
    t = _tree()
    t.park("why:learn", tick=5)
    assert t.node("why:learn").state is WhyState.ABSENT
    assert not t.why_should_this_run("why:map")
    t.activate("why:learn", tick=6)
    assert t.why_should_this_run("why:map")
    assert t.conservation()["invariant_ok"]


def test_conservation_survives_random_storm():
    """No sequence of kills/revives/parks may ever lose a node."""
    rng = random.Random(42)
    t = WhyTree()
    ids = ["why:root"]
    t.declare("root", node_id="why:root")
    for i in range(30):
        parent = rng.choice(ids)
        nid = f"why:n{i}"
        t.declare(f"purpose {i}", parent=parent, node_id=nid)
        ids.append(nid)
    for tick in range(500):
        nid = rng.choice(ids)
        node = t.node(nid)
        op = rng.random()
        try:
            if op < 0.35:
                t.kill(nid, reason="storm", tick=tick)
            elif op < 0.60 and node.state is WhyState.UNKNOWN:
                t.revive(nid, tick=tick)
            elif op < 0.70 and node.state is WhyState.ABSENT:
                t.activate(nid, tick=tick)
            elif op < 0.80 and node.state in (WhyState.ALIVE, WhyState.UNKNOWN):
                t.park(nid, tick=tick)
        except ValueError:
            pass  # invalid transitions are simply rejected
        c = t.conservation()
        assert c["invariant_ok"], f"conservation broke at tick {tick}"
    # and history only ever grew
    assert len(t.necrology()) >= 1


def test_json_round_trip():
    t = _tree()
    t.kill("why:root", reason="persist check", tick=8)
    t2 = WhyTree.from_json(t.to_json())
    assert t2.node("why:learn").state is WhyState.UNKNOWN
    assert t2.conservation() == t.conservation()
    assert len(t2.necrology()) == len(t.necrology())
