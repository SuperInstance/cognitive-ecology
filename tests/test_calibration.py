"""Calibration and delegated arbitration (ADR-0009).

Two claims under test: (1) probabilistic claims on bids are scored
honestly against outcomes (Brier, reliability); (2) the executive's
arbiter hook delegates exactly one bounded decision — reordering live
contenders — and can never resurrect a vetoed bid or crash the organism.
"""
import pytest

from cognitive_ecology import (
    AttentionBid, AttentionMarket, CalibrationLog, Executive, Runtime,
)
from cognitive_ecology.agents import DecisionArbiter


def _bid(src, label, attention_factors, success_p=None, resource=None):
    base = dict(urgency=1.0, justification=1.0, opportunity=1.0,
                novelty=1.0, expected_value=1.0)
    base.update(attention_factors)
    return AttentionBid(src=src, label=label, success_p=success_p,
                        resource=resource, **base)


# ---------------------------------------------------------------------------
# calibration log
# ---------------------------------------------------------------------------

def test_brier_score_math_is_pinned():
    log = CalibrationLog()
    # perfect foresight
    log.record(1, "a", "x", 1.0, 1.0)
    log.record(2, "a", "x", 0.0, 0.0)
    assert log.brier() == 0.0
    # honest coin flip reported as 50/50
    log2 = CalibrationLog()
    log2.record(1, "a", "x", 0.5, 1.0)
    log2.record(2, "a", "x", 0.5, 0.0)
    assert log2.brier() == 0.25
    # confidently wrong: worse than the coin
    log3 = CalibrationLog()
    log3.record(1, "a", "x", 1.0, 0.0)
    assert log3.brier() == 1.0
    assert "MISCALIBRATED" in log3.verdict()


def test_calibration_records_are_validated_and_filterable():
    log = CalibrationLog()
    with pytest.raises(ValueError):
        log.record(1, "a", "x", 1.5, 1.0)   # not a probability
    with pytest.raises(ValueError):
        log.record(1, "a", "x", 0.5, 0.7)   # not binary
    log.record(1, "a", "x", 0.8, 1.0)
    log.record(2, "b", "y", 0.4, 0.0)
    assert len(log.records()) == 2
    assert len(log.records(claimer="a")) == 1
    assert log.brier(claimer="b") == pytest.approx(0.16)


def test_reliability_bins():
    log = CalibrationLog()
    for _ in range(6):
        log.record(1, "a", "x", 0.9, 1.0)   # bin [0.8, 1.0]
    for _ in range(4):
        log.record(1, "a", "x", 0.2, 0.0)   # bin [0.2, 0.4)
    bins = log.reliability()
    assert (0.8, 1.0, 6, 0.9, 1.0) in bins
    assert (0.2, 0.4, 4, 0.2, 0.0) in bins


def test_runtime_scores_success_p_claims_against_outcomes():
    from tests.test_reattestation import _Greedy  # a known-working component

    class Gambler(_Greedy):
        def bid(self, ctx):
            from cognitive_ecology import AttentionBid
            yield AttentionBid(
                src=self.id, label=f"{self.id}:work",
                urgency=0.9, justification=1.0, opportunity=1.0,
                novelty=1.0, expected_value=1.0, success_p=0.9,
            )

    rt = Runtime(seed=3)
    rt.tensions.add("energy", growth=0.03)
    rt.declare_why("stay alive", node_id="why:root")
    rt.declare_why("forage", parent="why:root", node_id="why:forage")
    rt.register(Gambler("gambler", "why:forage", "energy"))
    rt.run(20)
    assert len(rt.calibration) == 20
    # the gambler always succeeds, and claimed 0.9 -> small but nonzero brier
    assert 0.0 < rt.calibration.brier() < 0.25
    assert "calibrated-or-better" in rt.calibration.verdict()


# ---------------------------------------------------------------------------
# delegated arbitration
# ---------------------------------------------------------------------------

def _market_with_executive(arbiter=None):
    return Executive(AttentionMarket(), max_actions=2, arbiter=arbiter)


def test_default_arbitration_is_unchanged_without_an_arbiter():
    ex = _market_with_executive()
    bids = [_bid("a", "a:1", {"urgency": 0.9}), _bid("b", "b:1", {"urgency": 0.5}),
            _bid("c", "c:1", {"urgency": 0.1})]
    decisions = ex.arbitrate(bids, ts=1)
    assert [d.bid.label for d in decisions] == ["a:1", "b:1"]
    assert ex.arbiter_calls == 0 and ex.last_divergence == 0


def test_arbiter_reorders_contenders_and_divergence_counts():
    calls = []

    def pick_last_slot(live, k):
        calls.append([b.label for b in live])
        # contrarian: pick the LOWEST attention contender
        return sorted(live, key=lambda b: b.attention)[:k]

    ex = _market_with_executive(pick_last_slot)
    bids = [_bid("a", "a:1", {"urgency": 0.9}), _bid("b", "b:1", {"urgency": 0.5}),
            _bid("c", "c:1", {"urgency": 0.1})]
    decisions = ex.arbitrate(bids, ts=1)
    # contrarian picks the two LOWEST: c (0.1) and b (0.5)
    assert [d.bid.label for d in decisions] == ["c:1", "b:1"]
    assert ex.arbiter_calls == 1 and ex.last_divergence == 1
    assert calls == [["a:1", "b:1", "c:1"]]  # saw all live contenders, sorted


def test_vetoed_bids_never_reach_the_arbiter():
    seen = []

    def spy(live, k):
        seen.extend(b.label for b in live)
        return live[:k]

    ex = _market_with_executive(spy)
    bids = [_bid("a", "a:1", {"urgency": 0.9}), _bid("v", "v:zero", {"urgency": 0.0}),
            _bid("b", "b:1", {"urgency": 0.5}), _bid("c", "c:1", {"urgency": 0.1})]
    decisions = ex.arbitrate(bids, ts=1)
    assert "v:zero" not in seen
    assert all(d.bid.attention > 0 for d in decisions)
    # the vetoed bid starved regardless of the arbiter
    starved_labels = [b.label for b in ex.last_clear.starved]
    assert "v:zero" in starved_labels


def test_failing_arbiter_degrades_to_deterministic():
    def broken(live, k):
        raise RuntimeError("decision provider down")

    ex = _market_with_executive(broken)
    bids = [_bid("a", "a:1", {"urgency": 0.9}), _bid("b", "b:1", {"urgency": 0.5}),
            _bid("c", "c:1", {"urgency": 0.1})]
    decisions = ex.arbitrate(bids, ts=1)
    assert [d.bid.label for d in decisions] == ["a:1", "b:1"]  # deterministic shadow
    assert ex.arbiter_calls == 1 and ex.last_divergence == 0


def test_arbiter_not_consulted_when_no_contention():
    def spy(live, k):
        raise AssertionError("must not be called without contention")

    ex = _market_with_executive(spy)
    decisions = ex.arbitrate([_bid("a", "a:1", {"urgency": 0.9})], ts=1)
    assert len(decisions) == 1 and ex.arbiter_calls == 0


def test_decision_arbiter_adapter_shapes_the_question():
    captured = {}

    def fake_decide(state, questions):
        captured["state"] = state
        captured["questions"] = questions
        return {"clear": ("b:1", 0.72, {"b:1": 0.72, "a:1": 0.28})}

    arb = DecisionArbiter(fake_decide)
    live = [_bid("a", "a:1", {"urgency": 0.9}), _bid("b", "b:1", {"urgency": 0.5})]
    chosen = arb(live, 1)
    assert [b.label for b in chosen] == ["b:1", "a:1"]
    assert arb.last_choice == "b:1" and arb.last_confidence == 0.72
    # cache-stable state: sorted by label, rounded values
    assert captured["state"]["contenders"][0]["label"] == "a:1"
    assert captured["questions"]["clear"]["type"] == "choice"
    assert set(captured["questions"]["clear"]["criteria"]) == {"a:1", "b:1"}


def test_decision_arbiter_rejects_unknown_choice():
    def lying_decide(state, questions):
        return {"clear": ("nope", 0.9, {})}

    arb = DecisionArbiter(lying_decide)
    with pytest.raises(RuntimeError):
        arb([_bid("a", "a:1", {"urgency": 0.9})], 1)
    assert arb.errors == 1


def test_market_state_is_cache_stable():
    s1 = DecisionArbiter.market_state(
        [_bid("a", "a:1", {"urgency": 0.3333333}),
         _bid("b", "b:1", {"urgency": 0.6666666})], 1)
    s2 = DecisionArbiter.market_state(
        [_bid("b", "b:1", {"urgency": 0.66666666}),
         _bid("a", "a:1", {"urgency": 0.33333333})], 1)
    assert s1 == s2  # order-independent input, byte-identical output
