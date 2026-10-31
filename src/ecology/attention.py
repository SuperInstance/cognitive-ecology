"""The attention economy.

Law 2: attention — not compute — is the scarce resource. Every process
competes for budget by bidding. The manifesto formula:

    attention = urgency * justification * opportunity * novelty * expected_value

``justification`` comes from the WHY kernel: a process whose justification
chain is dead bids with zero weight; questionable (unknown) bids at a
discount. This is Open Question #5 made real — WHY as the scheduler.

Two policies, because Open Question #1 ("market or government?") is
unsettled, and the working hypothesis is: **markets locally, governance
globally**. :class:`HybridPolicy` reserves a slice of the budget for
identity-level (governance) bidders and lets the market allocate the rest.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Protocol

#: WHY weights: how much a bid counts when its justification chain is
#: alive / unknown / dead / absent. Dead and absent bid at zero — that is
#: the conservation law biting.
JUSTIFICATION_WEIGHTS: dict[str, float] = {
    "alive": 1.0,
    "unknown": 0.25,
    "dead": 0.0,
    "absent": 0.0,
}


@dataclass
class Bid:
    """A process's claim on attention, scored by the manifesto formula.

    Factor defaults are 0.0 — a bid claims nothing it does not state. Use
    :meth:`keepalive` for the minimal "I exist and I'm justified" bid.
    """

    bidder: str
    requested: float
    urgency: float = 0.0
    justification: float = 1.0
    opportunity: float = 0.0
    novelty: float = 0.0
    expected_value: float = 0.0
    reason: str = ""

    @classmethod
    def keepalive(cls, bidder: str, requested: float = 1.0, justification: float = 1.0) -> Bid:
        """All factors at 1.0: the score collapses to the justification
        weight alone — a process that claims nothing else still bids with
        its WHY chain."""
        return cls(
            bidder=bidder,
            requested=requested,
            urgency=1.0,
            justification=justification,
            opportunity=1.0,
            novelty=1.0,
            expected_value=1.0,
        )

    @property
    def score(self) -> float:
        return (
            self.urgency
            * self.justification
            * self.opportunity
            * self.novelty
            * self.expected_value
        )


@dataclass
class Allocation:
    """The result of one allocation round — the tick's energy assignment."""

    grants: dict[str, float] = field(default_factory=dict)
    policy: str = ""

    def energy(self, bidder: str) -> float:
        return self.grants.get(bidder, 0.0)

    @property
    def total(self) -> float:
        return sum(self.grants.values())


class AllocationPolicy(Protocol):
    name: str

    def allocate(self, bids: Sequence[Bid], budget: float) -> Allocation:
        """Decide who runs. A process granted 0 starves this tick — it is
        not killed; the economy is not a hierarchy."""
        ...  # pragma: no cover


@dataclass
class MarketPolicy:
    """Proportional allocation by score — emergent, scalable, unaccountable."""

    name: str = "market"

    def allocate(self, bids: Sequence[Bid], budget: float) -> Allocation:
        scored = [(b, b.score) for b in bids if b.score > 0 and b.requested > 0]
        if not scored:
            return Allocation(policy=self.name)
        total_score = sum(s for _, s in scored)
        grants: dict[str, float] = {}
        remaining = budget
        # Highest score first so budget exhaustion hits the weakest claims.
        for bid, score in sorted(scored, key=lambda x: -x[1]):
            share = budget * score / total_score
            grant = min(bid.requested, share, remaining)
            if grant > 0:
                grants[bid.bidder] = grant
                remaining -= grant
            if remaining <= 0:
                break
        return Allocation(grants=grants, policy=self.name)


@dataclass
class CentralPolicy:
    """Fixed priority order — understandable, debuggable, bottlenecked."""

    name: str = "central"
    priority: list[str] = field(default_factory=list)

    def allocate(self, bids: Sequence[Bid], budget: float) -> Allocation:
        by_bidder = {b.bidder: b for b in bids}
        grants: dict[str, float] = {}
        remaining = budget
        for bidder in self.priority:
            bid = by_bidder.get(bidder)
            if bid is None or remaining <= 0:
                continue
            grant = min(bid.requested, remaining)
            if grant > 0:
                grants[bidder] = grant
                remaining -= grant
        return Allocation(grants=grants, policy=self.name)


@dataclass
class HybridPolicy:
    """Governance reserve + open market.

    ``governance_share`` of the budget goes to bidders named in ``governed``
    (identity-level concerns that must never starve); the rest is allocated
    by score. Markets locally, governance globally.
    """

    governed: list[str] = field(default_factory=list)
    governance_share: float = 0.3
    name: str = "hybrid"

    def allocate(self, bids: Sequence[Bid], budget: float) -> Allocation:
        if not bids:
            return Allocation(policy=self.name)
        governed_bids = [b for b in bids if b.bidder in self.governed]
        # No governed bidders this tick: the governance reserve rolls over
        # to the market (a reserved slice nobody can claim is just waste).
        governed_budget = budget * self.governance_share if governed_bids else 0.0
        market_budget = budget - governed_budget
        central = CentralPolicy(priority=self.governed).allocate(governed_bids, governed_budget)
        market = MarketPolicy().allocate(
            [b for b in bids if b.bidder not in self.governed], market_budget
        )
        grants = dict(market.grants)
        for bidder, grant in central.grants.items():
            grants[bidder] = grants.get(bidder, 0.0) + grant
        return Allocation(grants=grants, policy=self.name)


def justification_weight(status_value: str) -> float:
    """Map a WHY status to the multiplier it lends to a bid."""
    return JUSTIFICATION_WEIGHTS.get(status_value, 0.0)
