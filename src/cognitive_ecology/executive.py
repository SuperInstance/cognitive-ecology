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

The outcome-arbiter extension (ADR-0013): a ``scorecard`` scores the
 delegated judgment by realized outcomes; a benched arbiter is skipped
 silently (the fail-safe ADR-0009 guaranteed) and the benching is
 announced once as a DECISION event — paid judgment must earn its keep.

Round 17 closed the last hole in the fail-safe (found by the wave-1
red team): the arbiter's ANSWER is now validated like its exceptions
already were. Anything that is not an ordered subset of the very bids
it was shown — wrong types, a foreign look-alike bid, a single object,
duplicates — is a FAILED answer, not a crash: the deterministic shadow
stands for that tick, the count lands in ``arbiter_malformed``, and an
ERROR event records it.
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


@dataclass
class ArbiterContext:
    """What the delegated tie-break did this tick (for the scorecard)."""

    tick: int
    pick: str                    # label the arbiter put first
    confidence: Optional[float]  # client's calibrated confidence, if any
    divergent: bool              # did it override the deterministic shadow


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

    ``scorecard`` (optional, ADR-0013) scores the delegation by realized
    outcomes; when the scorecard benches the arbiter, the executive
    stops calling it (silent degradation, announced once) and
    ``last_arbiter_context`` carries what the runtime needs to score
    the pick that acts.
    """

    def __init__(self, market: AttentionMarket, bus: Optional[EventBus] = None,
                 max_actions: int = 3,
                 arbiter: Optional[Callable[[List[AttentionBid], int],
                                            List[AttentionBid]]] = None,
                 scorecard=None,
                 market_log=None) -> None:
        self.market = market
        self.bus = bus
        self.max_actions = max_actions
        self.arbiter = arbiter
        self.scorecard = scorecard
        self.market_log = market_log  # read model (round 21); never consulted
        self.last_clear: Optional[ClearResult] = None
        self.last_divergence = 0
        self.arbiter_calls = 0
        self.arbiter_malformed = 0  # answers that failed validation (round 17)
        self.last_arbiter_context: Optional[ArbiterContext] = None
        self._bench_announced = False

    def arbitrate(self, bids: List[AttentionBid], top_k: Optional[int] = None,
                  ts: int = 0) -> List[Decision]:
        """Submit all bids, clear the market, resolve conflicts among winners."""
        for b in bids:
            self.market.submit(b)
        k = top_k if top_k is not None else self.max_actions
        result = self.market.clear(k)

        # delegated tie-break: the arbiter may reorder live contenders for
        # the clearable slots; the veto law already removed the vetoed
        self.last_arbiter_context = None
        if self.arbiter is not None:
            # ADR-0013: a benched arbiter is skipped — silent degradation
            # to the deterministic shadow, announced exactly once
            if self.scorecard is not None and self.scorecard.benched:
                if not self._bench_announced:
                    self._bench_announced = True
                    if self.bus is not None:
                        self.bus.emit(
                            EventKind.DECISION,
                            ("arbiter-benched", self.scorecard.name, "yield",
                             0.0),
                            src="executive", ts=ts,
                        )
            else:
                # contenders = winners + LIVE starved only; vetoed bids
                # (attention <= 0) are never shown to the arbiter at all
                live = list(result.winners) + \
                    [b for b in result.starved if b.attention > 0.0]
                live.sort(key=lambda b: (-b.attention, b.src, b.label))
                if len(live) > k:
                    self.arbiter_calls += 1
                    if self.scorecard is not None:
                        self.scorecard.note_call()
                    try:
                        chosen = self.arbiter(live, k)
                    except Exception:
                        chosen = None  # a failing arbiter degrades, never crashes
                    if chosen is not None and \
                            self._validate_choice(chosen, live, k) is None:
                        # round 17 (wave-1 red team): a wrong-type ANSWER used
                        # to crash the organism further down (at
                        # ``chosen[0].label`` / ClearResult). Now it is a
                        # FAILED answer — same treatment as an exception:
                        # degrade to the deterministic shadow for this tick.
                        # The organism must never die because judgment
                        # misbehaved; judgment that cannot speak the
                        # protocol loses the market's ear.
                        self.arbiter_malformed += 1
                        if self.bus is not None:
                            self.bus.emit(
                                EventKind.ERROR,
                                ("arbiter", "malformed return",
                                 f"call #{self.arbiter_calls}: expected an "
                                 f"ordered subset of the {len(live)} live "
                                 f"bids"),
                                src="executive", ts=ts,
                            )
                        chosen = None
                    if chosen is not None:
                        chosen_ids = [id(b) for b in chosen]
                        default_ids = [id(b) for b in live[:k]]
                        divergent = chosen_ids != default_ids
                        self.last_divergence += divergent
                        if self.scorecard is not None and divergent:
                            self.scorecard.note_divergence()
                        self.last_arbiter_context = ArbiterContext(
                            tick=ts,
                            pick=chosen[0].label if chosen else "",
                            confidence=getattr(self.arbiter, "last_confidence", None),
                            divergent=divergent,
                        )
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

        # the observation boundary (round 21): serialize this clearing —
        # the exact bids, the exact floats, the executive's own verdicts.
        # Read-model discipline: written after every decision is final,
        # never consulted by any decision, deletable without loss.
        if self.market_log is not None:
            self.market_log.note_clear(
                ts, result, decisions, self.last_arbiter_context,
            )
        return decisions

    # ------------------------------------------------------------------
    # the arbiter's answer contract (round 17)
    # ------------------------------------------------------------------
    @staticmethod
    def _validate_choice(chosen, live, k):
        """Is the arbiter's answer a legal ordering of bids it was shown?

        Legal means: a non-empty list/tuple whose items are — by
        identity, not equality — bids from ``live``, with no duplicates.
        A foreign bid with identical fields is still foreign (it is not
        the object the market priced). Anything else is a failed answer
        and the caller degrades to the deterministic shadow for the
        tick; it is never a crash.
        """
        if not isinstance(chosen, (list, tuple)):
            return None
        if len(chosen) < 1:
            return None
        live_ids = {id(b) for b in live}
        seen: set = set()
        for b in chosen:
            if not isinstance(b, AttentionBid) or id(b) not in live_ids:
                return None
            if id(b) in seen:  # one bid cannot fill two slots
                return None
            seen.add(id(b))
        return list(chosen)
