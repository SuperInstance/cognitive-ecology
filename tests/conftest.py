"""Shared test helpers."""

from __future__ import annotations

import pytest

from ecology.attention import Bid


@pytest.fixture
def full_bid():
    return _full_bid


def _full_bid(bidder: str, requested: float, justification: float = 1.0, **factors) -> Bid:
    """A bid with every manifesto factor set (defaults 1.0 unless overridden)."""
    base = dict(urgency=1.0, opportunity=1.0, novelty=1.0, expected_value=1.0)
    base.update(factors)
    return Bid(bidder=bidder, requested=requested, justification=justification, **base)
