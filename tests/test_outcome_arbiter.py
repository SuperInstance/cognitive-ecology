"""The outcome-arbiter: paid judgment must earn its keep (ADR-0013).

ADR-0009 counted divergences; a divergence count is not a value. These
tests pin the scorecard that scores the delegated tie-break by REALIZED
outcomes: the calibration immune system reused for the arbiter's own
claims, the base-rate comparison for its overrides, and the benching
that silently degrades the organism back to its deterministic shadow —
announced once, with a receipt that says why.
"""
import pytest

from cognitive_ecology import (
    ArbiterScorecard, AttentionBid, EventKind, Executive, Outcome,
    Runtime, WhyState,
)
from cognitive_ecology.attention import AttentionMarket


# ---------------------------------------------------------------------------
# fixtures: an organism with contended slots and a scriptable arbiter
# ---------------------------------------------------------------------------

class _Worker:
    """Bids every tick; succeeds or fails exactly as scripted."""

    def __init__(self, cid, why_node, tension, fail=False):
        self.id, self.why_node = cid, why_node
        self._tension, self.fail = tension, fail

    def bid(self, ctx):
        yield AttentionBid(
            src=self.id, label=f"{self.id}:work",
            urgency=max(0.3, ctx.tensions.level(self._tension)),
            justification=ctx.why.justification(self.why_node),
            opportunity=1.0, novelty=1.0, expected_value=1.0,
        )

    def act(self, ctx, label):
        if self.fail:
            return Outcome(False, "scripted failure")
        return Outcome(True, "did it")


def _rt():
    """Three workers contending for two slots (top_k=2): the arbiter
    always has a live tie to break."""
    rt = Runtime(seed=3, top_k=2, idle_window=999)
    rt.tensions.add("energy", growth=0.05)
    rt.declare_why("stay alive", node_id="why:root")
    rt.declare_why("forage", parent="why:root", node_id="why:a")
    rt.declare_why("map", parent="why:root", node_id="why:b")
    rt.declare_why("rest", parent="why:root", node_id="why:c")
    rt.register(_Worker("w1", "why:a", "energy"))
    rt.register(_Worker("w2", "why:b", "energy"))
    rt.register(_Worker("w3", "why:c", "energy"))
    return rt


class _FakeArbiter:
    """Always promotes a specific label, with a scripted confidence."""

    last_confidence = None

    def __init__(self, label, confidence=None):
        self.label = label
        self.confidence = confidence
        self.calls = 0

    def __call__(self, live, k):
        self.calls += 1
        self.last_confidence = self.confidence
        by = {b.label: b for b in live}
        pick = by.get(self.label, live[0])
        return [pick] + [b for b in live if b.label != pick.label]


def _wire(rt, arbiter, **kw):
    rt.executive.arbiter = arbiter
    rt.executive.scorecard = ArbiterScorecard(**kw)
    return rt.executive.scorecard


# ---------------------------------------------------------------------------
# the scorecard itself
# ---------------------------------------------------------------------------

def test_confident_and_wrong_arbiter_is_benched():
    """The arbiter claims 0.9 confidence on picks that always fail:
    Brier 0.81 >> 0.25 over the window -> benched with the reason."""
    rt = _rt()
    rt.component("w3").fail = True  # fails from the very first tick
    arb = _FakeArbiter("w3:work", confidence=0.9)
    sc = _wire(rt, arb, window=10)
    rt.run(20)
    assert sc.benched, sc.summary()
    assert "miscalibrated" in sc.bench.reason
    assert sc.calibration.brier("arbiter:arbiter") > 0.25


def test_calibrated_arbiter_keeps_its_job():
    rt = _rt()
    arb = _FakeArbiter("w3:work", confidence=0.8)
    sc = _wire(rt, arb, window=10)
    rt.run(40)  # w3 succeeds when it runs; 0.8 claimed vs ~1.0 realized
    assert not sc.benched
    assert sc.divergences > 0
    assert sc.divergent_picks > 0
    # the receipt reads like an honest scorecard
    assert "earning its keep" in sc.summary()


def test_value_destroying_overrides_are_benched():
    """Confidence is honest (0.5) but the overrides systematically pick
    the failing worker while everyone else succeeds: the base-rate test
    catches what calibration alone would not."""
    rt = _rt()
    rt.component("w3").fail = True
    arb = _FakeArbiter("w3:work", confidence=0.5)
    sc = _wire(rt, arb, window=10)
    rt.run(40)
    assert sc.benched
    assert "value-destroying" in sc.bench.reason
    # the receipt names the numbers
    assert sc.divergent_rate is not None and sc.divergent_rate < sc.base_rate


def test_benching_degrades_to_the_deterministic_shadow():
    rt = _rt()
    rt.component("w3").fail = True
    arb = _FakeArbiter("w3:work", confidence=0.9)
    sc = _wire(rt, arb, window=5)
    rt.run(25)
    assert sc.benched
    calls_when_benched = arb.calls
    diverged_when_benched = rt.executive.last_divergence
    rt.run(10)  # the benched arbiter is never consulted again
    assert arb.calls == calls_when_benched
    assert rt.executive.last_divergence == diverged_when_benched
    # the benching was announced exactly once, as a DECISION event
    bench_events = [e for e in rt.bus.log()
                    if e.kind is EventKind.DECISION
                    and e.payload[0] == "arbiter-benched"]
    assert len(bench_events) == 1
    assert bench_events[0].payload[1] == "arbiter"


def test_no_scorecard_keeps_v03_behavior():
    """arbiter without scorecard: divergence still counted, nothing scored."""
    rt = _rt()
    arb = _FakeArbiter("w3:work")
    rt.executive.arbiter = arb
    rt.run(20)
    assert rt.executive.last_divergence > 0
    assert rt.executive.scorecard is None


def test_scorecard_persistence_roundtrip():
    rt = _rt()
    rt.component("w3").fail = True
    arb = _FakeArbiter("w3:work", confidence=0.9)
    sc = _wire(rt, arb, window=5)
    rt.run(25)
    assert sc.benched
    import json, os, tempfile
    with tempfile.TemporaryDirectory() as td:
        rt.save(td)
        with open(os.path.join(td, "state.json")) as f:
            state = json.load(f)
        assert state["arbiter_scorecard"]["benched"] is True
        loaded = ArbiterScorecard.from_json(state["arbiter_scorecard"])
        assert loaded.benched and loaded.bench.reason == sc.bench.reason
        assert loaded.calls == sc.calls


def test_window_prevents_snap_judgments():
    """A few early failures do not bench a possibly-lucky arbiter."""
    rt = _rt()
    rt.component("w3").fail = True
    arb = _FakeArbiter("w3:work", confidence=0.9)
    sc = _wire(rt, arb, window=50)  # far larger than the run
    rt.run(10)
    assert not sc.benched  # not enough evidence yet


# ---------------------------------------------------------------------------
# the executive contract, unchanged where it was already pinned
# ---------------------------------------------------------------------------

def test_arbiter_never_sees_vetoed_bids():
    """ADR-0009's veto-guard survives the scorecard wiring."""
    market = AttentionMarket()
    ex = Executive(market)
    seen = {}

    def spy(live, k):
        seen["live"] = live
        return live[:k]

    ex.arbiter = spy
    bids = [
        AttentionBid(src="a", label="a:x", urgency=1.0, justification=1.0,
                     opportunity=1.0, novelty=1.0, expected_value=1.0),
        AttentionBid(src="c", label="c:z", urgency=0.9, justification=1.0,
                     opportunity=1.0, novelty=1.0, expected_value=1.0),
        AttentionBid(src="b", label="b:y", urgency=0.0, justification=1.0,
                     opportunity=1.0, novelty=1.0, expected_value=1.0),  # vetoed
    ]
    ex.arbitrate(bids, top_k=1, ts=1)
    labels = [b.label for b in seen["live"]]
    assert "b:y" not in labels  # the vetoed bid never reached the arbiter
    assert set(labels) == {"a:x", "c:z"}  # both LIVE contenders did
