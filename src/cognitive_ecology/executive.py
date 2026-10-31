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
from typing import Callable, List, Optional

from .attention import AttentionBid, AttentionMarket, ClearResult
from .events import EventBus, EventKind


@dataclass
class Decision:
    """What the executive decided about one winning bid."""

    bid: AttentionBid
    status: str          # "run" | "yield"
    event_seq: int = -1  # seq of the DECISION event (the cause for actions)


class Executive:
    """Clears the market, resolves conflicts, records decisions.

    ``arbiter`` (optional) delegates ONE bounded decision: which of the
    live contenders fill the k clearable slots. The veto law is applied
    BEFORE the arbiter sees anything — a delegated tie-break can reorder
    contenders, never resurrect vetoed bids. With ``arbiter=None`` the
    deterministic top-k stands (the default; the organism stays keyless
    and reproducible). ``last_divergence`` counts how often the arbiter
    disagreed with the deterministic shadow — the honest cost of handing
    judgment to a model.
    """

    def __init__(self, market: AttentionMarket, bus: Optional[EventBus] = None,
                 max_actions: int = 3,
                 arbiter: Optional[Callable[[List[AttentionBid], int],
                                            List[AttentionBid]]] = None) -> None:
        self.market = market
        self.bus = bus
        self.max_actions = max_actions
        self.arbiter = arbiter
        self.last_clear: Optional[ClearResult] = None
        self.last_divergence = 0
        self.arbiter_calls = 0

    def arbitrate(self, bids: List[AttentionBid], top_k: Optional[int] = None,
                  ts: int = 0) -> List[Decision]:
        """Submit all bids, clear the market, resolve conflicts among winners."""
        for b in bids:
            self.market.submit(b)
        k = top_k if top_k is not None else self.max_actions
        result = self.market.clear(k)

        # delegated tie-break: the arbiter may reorder live contenders for
        # the clearable slots; the veto law already removed the vetoed
        if self.arbiter is not None:
            # contenders = winners + LIVE starved only; vetoed bids
            # (attention <= 0) are never shown to the arbiter at all
            live = list(result.winners) + \
                [b for b in result.starved if b.attention > 0.0]
            live.sort(key=lambda b: (-b.attention, b.src, b.label))
            if len(live) > k:
                self.arbiter_calls += 1
                try:
                    chosen = self.arbiter(live, k)
                except Exception:
                    chosen = None  # a failing arbiter degrades, never crashes
                if chosen is not None:
                    chosen_ids = [id(b) for b in chosen]
                    default_ids = [id(b) for b in live[:k]]
                    self.last_divergence += (chosen_ids != default_ids)
                    result = ClearResult(
                        winners=list(chosen[:k]),
                        starved=list(chosen[k:]) + [b for b in result.starved
                                                    if id(b) not in chosen_ids],
                    )
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
