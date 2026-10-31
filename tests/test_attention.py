"""Attention economy tests: the manifesto formula, both policies, the hybrid."""

from __future__ import annotations

import pytest

from conftest import _full_bid
from ecology.attention import Bid, CentralPolicy, HybridPolicy, MarketPolicy, justification_weight


def test_manifesto_score_formula() -> None:
    bid = _full_bid(
        "research-cell", 5, justification=1.0, urgency=0.8, opportunity=0.5, novelty=0.7,
        expected_value=0.9,
    )
    assert bid.score == pytest.approx(0.8 * 1.0 * 0.5 * 0.7 * 0.9)


def test_dead_justification_bids_zero() -> None:
    bid = _full_bid("legacy", 5, justification=0.0)
    assert bid.score == 0.0
    assert justification_weight("dead") == 0.0
    assert justification_weight("unknown") == 0.25
    assert justification_weight("alive") == 1.0


def test_market_allocates_proportionally_and_caps_at_requested() -> None:
    bids = [
        _full_bid("a", 10, justification=1),
        _full_bid("b", 1, justification=1, urgency=0.5),
    ]
    allocation = MarketPolicy().allocate(bids, budget=10.0)
    # scores 1.0 vs 0.5 -> shares 6.67 vs 3.33, but b capped at requested=1
    assert allocation.energy("a") == pytest.approx(10.0 / 1.5, rel=1e-6)
    assert allocation.energy("b") == 1.0
    assert allocation.total <= 10.0


def test_market_gives_zero_when_no_scores() -> None:
    bids = [Bid("a", requested=5, urgency=0.0)]  # urgency 0 -> score 0
    allocation = MarketPolicy().allocate(bids, budget=10.0)
    assert allocation.grants == {}


def test_central_follows_priority_order() -> None:
    bids = [Bid("low", requested=10), Bid("high", requested=10)]
    allocation = CentralPolicy(priority=["high", "low"]).allocate(bids, budget=5.0)
    assert allocation.grants == {"high": 5.0}  # high takes all; low starves


def test_hybrid_reserves_governance_slice() -> None:
    bids = [
        _full_bid("identity", 10, justification=1),
        _full_bid("market-a", 10, justification=1),
        _full_bid("market-b", 10, justification=1, urgency=0.2),
    ]
    policy = HybridPolicy(governed=["identity"], governance_share=0.3)
    allocation = policy.allocate(bids, budget=10.0)
    # identity is guaranteed its 30% even though it competes in the market too
    assert allocation.energy("identity") >= 3.0
    # market splits the remaining 7.0 by score (1.0 vs 0.2)
    assert allocation.energy("market-a") > allocation.energy("market-b")
    assert allocation.total <= 10.0


def test_hybrid_governance_reserve_rolls_over_when_unclaimed() -> None:
    bids = [
        _full_bid("market-a", 10, justification=1),
        _full_bid("market-b", 10, justification=1, urgency=0.2),
    ]
    policy = HybridPolicy(governed=["identity"], governance_share=0.3)
    allocation = policy.allocate(bids, budget=10.0)
    # no governed bidder this tick -> the full budget flows to the market
    assert allocation.energy("market-a") == 10.0 * 1.0 / 1.2
