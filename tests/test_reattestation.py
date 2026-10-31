"""Re-attestation economics: liveness is a subscription, not a purchase.

Pins the semantics the live panel's round 001 converged on: without a cost
to holding purpose alive, "never deleted" degenerates into "never
questioned". These tests price that cost: freshness discounts, lapse to
UNKNOWN (never deletion), and the revival ceremony.
"""
import random

from cognitive_ecology import EventKind, Runtime, WhyState, WhyTree


def _tree(horizon=None):
    t = WhyTree(attestation_horizon=horizon)
    t.declare("stay alive", node_id="why:root", tick=0)
    t.declare("find food", parent="why:root", node_id="why:food", tick=0)
    t.declare("map clearings", parent="why:food", node_id="why:map", tick=0)
    return t


# ---------------------------------------------------------------------------
# freshness
# ---------------------------------------------------------------------------

def test_no_horizon_keeps_v02_semantics_forever():
    t = _tree()  # horizon None
    t.now = 100_000
    assert t.freshness("why:map") == 1.0
    assert t.justification("why:map") == 1.0
    assert t.reap() == []


def test_horizon_must_be_positive():
    for bad in (0, -3):
        try:
            WhyTree(attestation_horizon=bad)
            raise AssertionError("non-positive horizon must be rejected")
        except ValueError:
            pass


def test_freshness_grace_then_linear_decay():
    t = _tree(horizon=90)  # grace = 30
    # inside grace: full
    assert t.freshness("why:map", tick=30) == 1.0
    # halfway between grace and horizon: half
    mid = t.freshness("why:map", tick=60)
    assert abs(mid - 0.5) < 1e-9
    # at horizon: zero
    assert t.freshness("why:map", tick=90) == 0.0
    assert t.freshness("why:map", tick=400) == 0.0


def test_weakest_link_rules_the_chain():
    t = _tree(horizon=90)
    t.stamp_chain("why:map", tick=10)  # everything fresh at 10
    # then only the leaf keeps being served
    t.heartbeat("why:map", tick=80)
    # root/food last stamped at 10 -> age 70 -> past grace, decaying
    f = t.freshness("why:map", tick=80)
    assert f < 1.0
    # the stale root is the weakest link, even though the leaf is fresh
    root_f = t.freshness("why:root", tick=80)
    assert abs(f - root_f) < 1e-9


def test_dead_ancestor_still_hard_zero_even_when_fresh():
    t = _tree(horizon=90)
    t.stamp_chain("why:map", tick=10)
    t.kill("why:root", reason="mandate withdrawn", tick=12)
    t.now = 12
    assert t.justification("why:map") == 0.0


def test_stale_chain_bids_less_than_fresh_chain():
    t = _tree(horizon=90)
    # a second, fresh lineage
    t.declare("second root", node_id="why:r2", tick=0)
    t.declare("fresh child", parent="why:r2", node_id="why:c2", tick=0)
    t.heartbeat("why:r2", tick=0)
    t.heartbeat("why:c2", tick=0)
    stale = t.justification("why:map", tick=60)   # age 60 of 90
    fresh = t.justification("why:c2", tick=60)   # never served either!
    # neither was ever served; both should decay identically -> economics
    # is about USE, not age of declaration
    assert abs(stale - fresh) < 1e-9
    # but serve one and the gap opens
    t.stamp_chain("why:c2", tick=60)
    served = t.justification("why:c2", tick=60)
    assert served == 1.0 and stale < served


# ---------------------------------------------------------------------------
# reaping
# ---------------------------------------------------------------------------

def test_unserved_purpose_lapses_to_unknown_never_deleted():
    t = _tree(horizon=60)
    lapsed = t.reap(tick=100)
    ids = {n.id for n in lapsed}
    assert ids == {"why:root", "why:food", "why:map"}
    for nid in ("why:root", "why:food", "why:map"):
        assert t.node(nid).state is WhyState.UNKNOWN
    c = t.conservation()
    assert c["invariant_ok"] and c["ever_declared"] == 3 and c["unknown"] == 3
    # necrology remembers the lapse, with the reason
    reasons = [r.reason for r in t.necrology()]
    assert any(r.startswith("lapsed: unattested for 100 ticks") for r in reasons)


def test_reap_spares_non_alive_nodes():
    t = _tree(horizon=60)
    t.kill("why:root", reason="withdrawn", tick=5)  # cascade -> food, map UNKNOWN
    t.declare("draft idea", node_id="why:draft", state=WhyState.ABSENT, tick=5)
    lapsed = t.reap(tick=500)
    assert lapsed == []  # DEAD/UNKNOWN/ABSENT never lapse


def test_reap_is_deterministic_and_idempotent():
    t = _tree(horizon=60)
    first = [n.id for n in t.reap(tick=100)]
    second = [n.id for n in t.reap(tick=100)]
    assert first == ["why:food", "why:map", "why:root"] and second == []  # id order


def test_lapsed_node_blocked_until_revived():
    t = _tree(horizon=60)
    t.reap(tick=100)
    t.now = 100
    assert not t.why_should_this_run("why:food")
    # heartbeat cannot sneak a lapsed node back
    assert not t.heartbeat("why:food", tick=101)
    # only the ceremony works, and it needs a reason
    t.revive("why:root", reason="mandate re-justified: new evidence", tick=101)
    assert t.node("why:root").state is WhyState.ALIVE
    assert t.node("why:root").last_beat == 101  # revival buys a fresh horizon
    assert t.why_should_this_run("why:food")


def test_serving_a_purpose_prevents_lapse():
    t = _tree(horizon=60)
    # serve the lineage every 20 ticks for a very long time
    for tick in range(0, 2000, 20):
        t.stamp_chain("why:map", tick)
    assert t.reap(tick=2000) == []
    assert t.justification("why:map", tick=2000) == 1.0


def test_stamp_chain_is_transitive_to_the_root():
    t = _tree(horizon=60)
    took = t.stamp_chain("why:map", tick=42)
    assert took == 3
    assert t.node("why:root").last_beat == 42


# ---------------------------------------------------------------------------
# conservation under storm + reaping
# ---------------------------------------------------------------------------

def test_conservation_survives_random_storm_with_reaping():
    rng = random.Random(11)
    t = _tree(horizon=30)
    extra = []
    for i in range(40):
        parent = rng.choice(["why:root", "why:food", "why:map"] + extra) if extra else \
            rng.choice(["why:root", "why:food", "why:map"])
        nid = f"why:x{i}"
        t.declare(f"purpose {i}", parent=parent, node_id=nid, tick=0)
        extra.append(nid)
    for tick in range(1, 300):
        t.now = tick
        victims = rng.sample(list(t.nodes()), k=min(3, len(t.nodes())))
        for v in victims:
            r = rng.random()
            if r < 0.25 and v.state is WhyState.ALIVE:
                t.stamp_chain(v.id, tick)
            elif r < 0.4 and v.state is WhyState.ALIVE:
                t.kill(v.id, reason="storm", tick=tick)
            elif r < 0.5 and v.state is WhyState.UNKNOWN:
                t.revive(v.id, reason="storm re-justify", tick=tick)
        t.reap(tick)
        c = t.conservation()
        assert c["invariant_ok"], f"conservation broke at tick {tick}"
    assert t.conservation()["ever_declared"] == 43  # 3 + 40: nothing deleted


# ---------------------------------------------------------------------------
# runtime integration
# ---------------------------------------------------------------------------

class _Greedy:
    """A component that always bids and always acts."""

    def __init__(self, cid, why_node, tension):
        self.id = cid
        self.why_node = why_node
        self._tension = tension

    def bid(self, ctx):
        from cognitive_ecology import AttentionBid
        yield AttentionBid(
            src=self.id, label=f"{self.id}:work",
            urgency=ctx.tensions.level(self._tension) or 0.5,
            justification=ctx.why.justification(self.why_node),
            opportunity=1.0, novelty=1.0, expected_value=1.0,
        )

    def act(self, ctx, label):
        ctx.tensions.relieve(self._tension, 0.2)
        from cognitive_ecology import Outcome
        return Outcome(True, "did the thing")


def _worker_rt(horizon):
    """An organism with one served purpose and one unserved purpose."""
    rt = Runtime(seed=3, attestation_horizon=horizon)
    rt.tensions.add("energy", growth=0.03)
    rt.declare_why("stay alive", node_id="why:root")
    rt.declare_why("forage", parent="why:root", node_id="why:forage")
    rt.declare_why("legacy archive", parent="why:root", node_id="why:legacy")
    rt.register(_Greedy("worker", "why:forage", "energy"))
    return rt


def test_runtime_stamps_chains_of_winners():
    rt = Runtime(seed=3, attestation_horizon=100)
    rt.tensions.add("energy", growth=0.03)
    rt.declare_why("stay alive", node_id="why:root")
    rt.declare_why("forage", parent="why:root", node_id="why:forage")
    rt.register(_Greedy("worker", "why:forage", "energy"))
    reports = rt.run(40)
    assert all(r.ran for r in reports)
    # running re-attested the whole chain
    assert rt.why.node("why:root").last_beat == 40
    assert rt.why.node("why:forage").last_beat == 40
    assert rt.why.justification("why:forage") == 1.0


def test_runtime_reaps_unserved_purposes_on_audit_ticks():
    rt = _worker_rt(horizon=30)
    reports = rt.run(60)
    # forage is served -> alive; legacy is unserved -> lapsed by tick 50
    assert rt.why.node("why:forage").state is WhyState.ALIVE
    assert rt.why.node("why:legacy").state is WhyState.UNKNOWN
    lapsed_ticks = [r.tick for r in reports if r.lapsed]
    assert lapsed_ticks == [50]  # first audit tick past the horizon
    assert lapsed_ticks and "why:legacy" in reports[lapsed_ticks[0] - 1].lapsed
    # the lapse was spoken into the event log
    why_events = [e for e in rt.bus.log() if e.kind is EventKind.WHY
                  and e.src == "reaper"]
    assert any(e.payload[0] == "why:legacy" for e in why_events)
    # and nothing was deleted
    c = rt.why.conservation()
    assert c["invariant_ok"] and c["ever_declared"] == 3


def test_revived_purpose_resumes_and_persistence_roundtrips():
    import tempfile
    rt = _worker_rt(horizon=30)
    rt.run(10)
    # kill the worker's purpose lineage to stop service
    rt.why.kill("why:root", reason="test: withdraw mandate", tick=10)
    rt.run(20)  # nothing runs; forage stays UNKNOWN (killed cascade)
    rt.why.resurrect("why:root", "mandate restored", tick=30)
    rt.run(5)
    assert rt.why.why_should_this_run("why:forage")
    with tempfile.TemporaryDirectory() as d:
        rt.save(d)
        rt2 = Runtime.load(d, attach=lambda r: r.register(
            _Greedy("worker", "why:forage", "energy")))
        assert rt2.why.attestation_horizon == 30
        assert rt2.why.node("why:root").last_beat == rt.why.node("why:root").last_beat
        assert rt2.why.freshness("why:forage") == rt.why.freshness("why:forage")
        assert rt2.why.justification("why:forage") == rt.why.justification("why:forage")
