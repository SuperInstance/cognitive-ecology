"""L5b — the Executive: the market's clearing house.

The attention market ranks; the executive decides. After the market clears
top-k, the executive:

* resolves RESOURCE CONFLICTS — two winners claiming the same exclusive
  resource (e.g. ``body`` or ``mic``) cannot both act; the higher-attention
  bid wins, the other *yields* (recorded, not punished);
* emits one DECISION event per winner, which becomes the ``cause`` of every
  event the winner's action produces — so the causal chain from decision to
  effect is always walkable;
* leaves everyone else starving this tick, which the ecology counts.

The executive has no intelligence of its own. It is a procedure — the
smarts live in the market (economics) and the WHY tree (purpose).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .attention import AttentionBid, AttentionMarket, ClearResult
from .events import EventBus, EventKind


@dataclass
class Decision:
    """What the executive decided about one winning bid."""

    bid: AttentionBid
    status: str          # "run" | "yield"
    event_seq: int = -1  # seq of the DECISION event (the cause for actions)


class Executive:
    """Clears the market, resolves conflicts, records decisions."""

    def __init__(self, market: AttentionMarket, bus: Optional[EventBus] = None,
                 max_actions: int = 3) -> None:
        self.market = market
        self.bus = bus
        self.max_actions = max_actions
        self.last_clear: Optional[ClearResult] = None

    def arbitrate(self, bids: List[AttentionBid], top_k: Optional[int] = None,
                  ts: int = 0) -> List[Decision]:
        """Submit all bids, clear the market, resolve conflicts among winners."""
        for b in bids:
            self.market.submit(b)
        k = top_k if top_k is not None else self.max_actions
        result = self.market.clear(k)
        self.last_clear = result

        held: dict = {}
        decisions: list = []
        for b in result.winners:
            if b.resource is not None and b.resource in held:
                status = "yield"  # lost the resource to a stronger bid
            else:
                status = "run"
                if b.resource is not None:
                    held[b.resource] = b
            seq = -1
            if self.bus is not None:
                ev = self.bus.emit(
                    EventKind.DECISION,
                    (b.label, b.src, status, round(b.attention, 4)),
                    src="executive", ts=ts,
                )
                seq = ev.seq
            decisions.append(Decision(bid=b, status=status, event_seq=seq))
        return decisions
