"""L0 — the Runtime: a process, not an agent.

The runtime is the organism's BODY. It advances a clock (``tick``), wires
the organs together, and enforces the two laws of the kernel:

* nothing runs without a living WHY chain, and
* nothing is ever deleted (events, graph nodes, WHY nodes, dead scripts).

The runtime itself NEVER calls a model. It is fully functional with zero
LLMs, zero API keys, zero network — an LLM joins as a component
(agents/orchestrator.py) and is subject to the same WHY gate and the same
attention market as every foraging script. Models are citizens, not kings.

One tick, in order
------------------
 1. Tensions grow (homeostasis).
 2. Every component answers the heartbeat: ``why_should_this_run()``.
    A broken WHY chain means no bids this tick — but no deletion, ever.
 3. Eligible components submit attention bids.
 4. The executive clears top-k and resolves resource conflicts.
 5. Winners act; every event they emit is caused-chained to the decision.
 6. Memory consolidates this tick's events into the world graph.
 7. The graph decays a little (fading, never deletion).
 8. If nothing ran for `idle_window` ticks, the organism sleeps
    (replay / prune / dream).
 9. Every 25 ticks the WHY conservation law is audited; a violation raises.

Components
----------
A component is anything with ``id``, ``why_node``, ``bid(ctx)`` and
``act(ctx, label)``. It receives a ``WorldSnapshot`` (never the runtime
itself), which keeps components small, testable, and replacable.

A component that misbehaves is contained, never fatal (round 17): a
raising ``bid()``/``act()`` — or a bid returning junk — is recorded as
an ``ERROR`` event and the tick goes on. The other components keep
running; the broken one starves on its own economics. The body
survives its organs.
"""
from __future__ import annotations

import json
import os
import random
from dataclasses import asdict, dataclass, field
from typing import Callable, Iterable, Optional, Protocol, runtime_checkable

from .attention import AttentionBid, AttentionMarket
from .audit import ConservationAuditor
from .calibration import CalibrationLog
from .events import Event, EventBus, EventKind
from .executive import ArbiterContext, Executive
from .marketlog import MarketLog
from .graph import WorldGraph
from .identity import Identity
from .memory import Memory
from .scripts import Outcome, ScriptEcology
from .sleep import SleepCycle, SleepStats
from .tension import TensionField
from .why import WhyTree


@dataclass
class TickReport:
    """What happened in one tick — the telemetry unit."""

    tick: int
    ran: list = field(default_factory=list)
    yielded: list = field(default_factory=list)
    starved: list = field(default_factory=list)
    slept: bool = False
    events: int = 0
    conservation_ok: Optional[bool] = None
    lapsed: list = field(default_factory=list)  # WHY nodes lapsed this tick
    tensions: dict = field(default_factory=dict)  # levels at end of tick

    def to_row(self) -> dict:
        return {
            "tick": self.tick, "ran": self.ran, "yielded": self.yielded,
            "starved_n": len(self.starved), "slept": self.slept,
            "events": self.events, "conservation_ok": self.conservation_ok,
            "lapsed": self.lapsed, "tensions": self.tensions,
        }


@runtime_checkable
class Component(Protocol):
    """Anything that can live inside a Runtime and compete for attention."""

    id: str
    why_node: str

    def bid(self, ctx: "WorldSnapshot") -> Iterable[AttentionBid]: ...

    def act(self, ctx: "WorldSnapshot", label: str) -> Outcome: ...


class WorldSnapshot:
    """A cheap per-tick view of the organism, handed to components.

    Components never touch the Runtime directly. The snapshot exposes
    read access to the world (graph, why, tensions, recent events) plus a
    guarded ``emit`` that cause-chains anything they say back to the
    decision that authorized them.
    """

    def __init__(self, runtime: "Runtime") -> None:
        self._rt = runtime

    @property
    def tick(self) -> int:
        return self._rt.tick_no

    @property
    def why(self) -> WhyTree:
        return self._rt.why

    @property
    def graph(self) -> WorldGraph:
        return self._rt.graph

    @property
    def tensions(self) -> TensionField:
        return self._rt.tensions

    @property
    def ecology(self) -> ScriptEcology:
        return self._rt.ecology

    def emit(self, kind, payload, src: str) -> Event:
        """Say something into the event log, cause-chained to the decision."""
        return self._rt.bus.emit(
            kind, payload, src=src, ts=self._rt.tick_no,
            cause=self._rt._current_cause,
        )

    def recent(self, n: int = 8) -> list:
        return self._rt.bus.window(n)

    def novelty(self, focus) -> float:
        """How fresh is the patch of world this script watches?

        Fraction of focus nodes seen within the last 12 ticks; ids not yet
        in the graph count as maximally novel (a script that would CREATE
        its own focus is not vetoed); no focus at all -> neutral 0.3.
        """
        ids = [f for f in focus if isinstance(f, str)]
        if not ids:
            return 0.3
        fresh = 0
        for nid in ids:
            node = self._rt.graph.get(nid)
            # A focus node that does not exist yet is maximally novel —
            # scripts that would CREATE their own focus (e.g. 'search'
            # proposals) must not be novelty-vetoed out of existence.
            if node is None or (self._rt.tick_no - node.last_seen) <= 12:
                fresh += 1
        return fresh / len(ids)

    def digest(self, max_nodes: int = 24) -> str:
        return self._rt.graph.digest(max_nodes)


class Runtime:
    """L0 — the body. Ticks the organism. Never calls a model."""

    def __init__(self, seed: int = 7, top_k: int = 3, idle_window: int = 5,
                 attestation_horizon: Optional[int] = None) -> None:
        self.seed = seed
        self.top_k = top_k
        self._rng = random.Random(seed)

        self.bus = EventBus()
        self.why = WhyTree(attestation_horizon=attestation_horizon)
        self.graph = WorldGraph()
        self.tensions = TensionField()
        self.market = AttentionMarket()
        # the observation boundary (round 21): exact, non-perturbing,
        # deletable — see marketlog.py. Not organism state: a loaded
        # organism starts a fresh log (observation history is the host's).
        self.market_log = MarketLog()
        self.executive = Executive(
            self.market, bus=self.bus, max_actions=top_k,
            market_log=self.market_log,
        )
        self.ecology = ScriptEcology(bus=self.bus, rng=random.Random(seed + 1))
        self.memory = Memory(self.graph)
        self.sleeper = SleepCycle(
            self.ecology, self.memory, bus=self.bus,
            rng=random.Random(seed + 2), idle_window=idle_window,
        )
        self.identity: Optional[Identity] = None
        self.simulator = None  # optional Simulator; inject for forecast-based EV
        self.calibration = CalibrationLog()  # probabilistic claims vs outcomes

        self._components: dict = {}
        self.tick_no = 0
        self._idle = 0
        self._current_cause: Optional[int] = None
        self._last_audit_ok: Optional[bool] = None
        # persistence watermark (round 20a): how many events the events
        # file at ``_persisted_to`` already contains. save() appends only
        # the delta — the events file is never rewritten whole again.
        self._persisted = 0
        self._persisted_to: Optional[str] = None
        # round 20b: the receipt of the last event-log compaction, if any.
        # It rides in every state.json until the next compaction replaces
        # it — the anchor is the dropped prefix's fold and stays valid
        # across any number of later plain saves.
        self._last_truncation: Optional[dict] = None

    # ------------------------------------------------------------------
    # assembly
    # ------------------------------------------------------------------
    def declare_why(self, statement: str, parent: Optional[str] = None,
                    tick: Optional[int] = None, node_id: Optional[str] = None,
                    parents: Optional[list] = None):
        return self.why.declare(
            statement, parent=parent, tick=self.tick_no if tick is None else tick,
            node_id=node_id, parents=parents,
        )

    def ensure_why(self, statement: str, parent: Optional[str] = None,
                   tick: Optional[int] = None, node_id: Optional[str] = None,
                   parents: Optional[list] = None):
        """Idempotent declare (round 23 — the attach rite, de-rited).

        Re-attaching an organism (after load, or a dev hot-reload) used
        to mean has()-guards before every declare. Now: if the node
        exists it is returned as-is — but a statement MISMATCH raises,
        because an id means one purpose, forever. Without a node_id,
        this is a plain declare (statements may repeat legitimately
        across branches; only ids are load-bearing).
        """
        if node_id is not None and self.why.has(node_id):
            node = self.why.node(node_id)
            if node.statement != statement:
                raise ValueError(
                    f"WHY node {node_id!r} already means "
                    f"{node.statement!r}, not {statement!r}"
                )
            return node
        return self.declare_why(statement, parent=parent, tick=tick,
                                node_id=node_id, parents=parents)

    def ensure_tension(self, name: str, growth: float = 0.02,
                       level: float = 0.0, description: str = ""):
        """Idempotent tension add: never resets a saved drive's level."""
        return self.tensions.ensure(name, growth=growth, level=level,
                                    description=description)

    def ensure_component(self, comp) -> bool:
        """Register unless already registered. True if newly registered;
        False if the id was already attached (state untouched)."""
        if comp.id in self._components:
            return False
        self.register(comp)
        return True

    def ensure_script(self, script, tick: Optional[int] = None):
        """Idempotent script adopt (delegates to the ecology; kept as a
        Runtime method so attach rites read uniformly). If a live script
        with this name exists it is returned; otherwise the script is
        adopted with any saved track record rehydrated."""
        return self.ecology.ensure_script(
            script, self.tick_no if tick is None else tick)

    def register(self, comp) -> None:
        """A component joins the organism. Its WHY node must already exist.

        Registering against a nonexistent WHY node is a hard error —
        nothing runs without a reason, not even by accident.
        """
        if not self.why.has(comp.why_node):
            raise KeyError(
                f"component {comp.id!r} references unknown WHY node "
                f"{comp.why_node!r}: declare the WHY first"
            )
        if comp.id in self._components:
            raise ValueError(f"duplicate component id: {comp.id}")
        self._components[comp.id] = comp

    def component(self, cid: str):
        return self._components.get(cid)

    def components(self) -> list:
        return list(self._components.values())

    def snapshot(self) -> WorldSnapshot:
        return WorldSnapshot(self)

    # ------------------------------------------------------------------
    # the heartbeat
    # ------------------------------------------------------------------
    def tick(self) -> TickReport:
        """One heartbeat of the organism. See module docstring for the order."""
        self.tick_no += 1
        t = self.tick_no
        self.why.now = t  # the WHY clock advances with the organism
        start_len = len(self.bus)

        # 1. drives grow
        for name, old, new in self.tensions.tick():
            self.bus.emit(EventKind.TENSION, (name, round(new, 3)),
                          src="tensions", ts=t)

        ctx = WorldSnapshot(self)

        # 2 + 3. heartbeat gate, then bids.
        #
        # Fail-safe totality (round 17, wave-1 red team): a broken organ
        # must not stop the heart. ``bid()`` is contained exactly like
        # ``act()``: a raising bid, or a bid returning junk, is recorded
        # as an ERROR event and the component simply proposed nothing
        # this tick — its scripts then starve on their own economics
        # (fail -> EMA drops -> loses the market -> dies into the
        # necrology with its record). The log says WHY, not just THAT.
        all_bids: list = []
        for comp in self._components.values():
            if not self.why.why_should_this_run(comp.why_node):
                continue
            try:
                offered = comp.bid(ctx)
                if not isinstance(offered, (list, tuple)):
                    offered = list(offered)  # generators OK; junk raises here
            except Exception as exc:  # the body survives its organs
                self.bus.emit(
                    EventKind.ERROR,
                    (comp.id, "bid", f"{exc.__class__.__name__}: {exc}"),
                    src=comp.id, ts=t,
                )
                continue
            # protocol check: only real bids enter the market — a
            # component returning look-alikes (dicts, strings, ...) gets
            # them dropped, counted, and announced. Never fatal.
            bad = [b for b in offered if not isinstance(b, AttentionBid)]
            if bad:
                self.bus.emit(
                    EventKind.ERROR,
                    (comp.id, "bid", f"dropped {len(bad)} non-bid item(s)"),
                    src=comp.id, ts=t,
                )
            all_bids.extend(
                b for b in offered if isinstance(b, AttentionBid))

        # 4 + 5. arbitrate and act
        decisions = self.executive.arbitrate(all_bids, top_k=self.top_k, ts=t)
        starved_labels = []
        if self.executive.last_clear is not None:
            starved_labels = [b.label for b in self.executive.last_clear.starved]
        ran: list = []
        yielded: list = []
        for d in decisions:
            if d.status != "run":
                yielded.append(d.bid.label)
                continue
            comp = self._components[d.bid.src]
            self._current_cause = d.event_seq
            try:
                out = comp.act(ctx, d.bid.label)
            except Exception as exc:  # a crashing component must not kill the body
                out = Outcome(False, f"component error: {exc.__class__.__name__}: {exc}")
            ran.append(d.bid.label)
            # running under a purpose re-attests it — use it or lose it —
            # and the winner's identity becomes the attestation's provenance
            self.why.stamp_chain(comp.why_node, t, by=comp.id)
            # a bid that claimed a success probability gets scored on it
            if d.bid.success_p is not None:
                self.calibration.record(
                    t, d.bid.src, d.bid.label, d.bid.success_p,
                    1.0 if out.ok else 0.0,
                )
            # the delegated tie-break gets scored by realized outcomes
            # (ADR-0013): the arbiter's pick that acted is a claim
            sc = self.executive.scorecard
            ac = self.executive.last_arbiter_context
            if sc is not None and ac is not None and ac.tick == t:
                sc.note_action_outcome(out.ok)  # base rate on arbiter ticks
                if d.bid.label == ac.pick:
                    sc.record_outcome(
                        t, ac.pick, ac.confidence, out.ok, ac.divergent)
            self.bus.emit(
                EventKind.NOTE_ON, (d.bid.label, 1 if out.ok else 0),
                src=d.bid.src, ts=t, cause=d.event_seq,
            )
            if not out.ok and out.note:
                # the failure's REASON belongs in the log (round 17: on-call
                # could see THAT an action failed, never WHY). NOTE_ON stays
                # a 2-tuple — the reason is its own ERROR event, cause-chained
                # to the same decision.
                self.bus.emit(
                    EventKind.ERROR, (d.bid.label, "act", out.note),
                    src=d.bid.src, ts=t, cause=d.event_seq,
                )
        self._current_cause = None

        # 6. ecology bookkeeping (starvation counts, deaths)
        self.ecology.bookkeeping(t, ran, starved_labels)

        # 7. this tick's events consolidate into world structure
        self.memory.consolidate(self.bus.log()[start_len:], t)

        # 8. the world fades a little (never deletes)
        self.graph.decay(t)

        # 9. idle -> sleep (replay / prune / dream)
        slept = False
        if not ran:
            self._idle += 1
            if self.sleeper.should_sleep(self._idle):
                self.sleeper.cycle(t, events=self.bus.window(200))
                slept = True
                self._idle = 0
        else:
            self._idle = 0

        # 10. periodic conservation audit — the law must hold, always.
        #     With an attestation horizon, the audit is also the reaper:
        #     unserved purposes lapse to UNKNOWN (never deleted).
        audit: Optional[bool] = None
        lapsed_ids: list = []
        if t % 25 == 0 or t == 1:
            for n in self.why.reap(t):
                lapsed_ids.append(n.id)
                self.bus.emit(
                    EventKind.WHY, (n.id, "alive", "unknown", "lapsed"),
                    src="reaper", ts=t,
                )
            audit = self.why.conservation()["invariant_ok"]
            self._last_audit_ok = audit
            if not audit:
                raise RuntimeError(
                    "WHY CONSERVATION VIOLATED: nodes disappeared. "
                    "This is a kernel bug — please report it."
                )

        return TickReport(
            tick=t, ran=ran, yielded=yielded, starved=starved_labels,
            slept=slept, events=len(self.bus) - start_len,
            conservation_ok=audit, lapsed=lapsed_ids,
            tensions=self.tensions.snapshot(),
        )

    def run(self, n: int, on_tick: Optional[Callable[[TickReport], None]] = None) -> list:
        reports = []
        for _ in range(n):
            r = self.tick()
            reports.append(r)
            if on_tick is not None:
                on_tick(r)
        return reports

    # ------------------------------------------------------------------
    # persistence: the organism survives its process
    # ------------------------------------------------------------------
    def save(self, path: str) -> None:
        """Write the organism's state. Behavior lives in code; state lives here.

        Trust at the door (round 20a — the wave-1 backend persona's top
        one; before this, a torn write destroyed the only checkpoint and
        load() never verified anything):

        * ATOMIC — state.json is written whole to a temp file and
          os.replace()d into place. A crash mid-write leaves the previous
          checkpoint untouched; a torn state.json cannot come from us.
        * APPEND-MODE EVENTS — events.jsonl is never rewritten whole;
          each save appends only the events since the last one. The state
          records the watermark and the event chain head, so load() can
          prove the file was never edited, truncated, or spliced.
        * SELF-VOUCHING — the state carries its conservation receipt
          (ADR-0008); load() re-verifies it rather than trusting it.
        """
        receipt = ConservationAuditor().verify(self.why)
        os.makedirs(path, exist_ok=True)
        state = {
            "format": "cognitive-ecology/state",
            "version": "0.4.0",
            "tick": self.tick_no,
            "seed": self.seed,
            "top_k": self.top_k,
            "attestation_horizon": self.why.attestation_horizon,
            "idle": self._idle,
            "idle_window": self.sleeper.idle_window,
            "sleeper": asdict(self.sleeper.stats),
            "events_watermark": len(self.bus),
            "event_chain_head": self.bus.chain_head,
            "event_truncation": self._last_truncation,
            "conservation_receipt": {
                "ok": receipt.ok,
                "live_digest": receipt.live_digest,
                "replay_digest": receipt.replay_digest,
                "chain_head": receipt.chain_head,
                "genesis_records": receipt.genesis_records,
                "transition_records": receipt.transition_records,
                "journal_records": receipt.journal_records,
                "summary": receipt.summary(),
            },
            "why": self.why.to_json(),
            "graph": self.graph.to_json(),
            "tensions": self.tensions.to_dict(),
            "ecology": self.ecology.to_json(),
            "identity": self.identity.to_dict() if self.identity else None,
            "market": self.market.stats(),
            "calibration": self.calibration.to_json(),
            "arbiter_scorecard": self.executive.scorecard.to_json()
            if self.executive.scorecard is not None else None,
        }
        tmp = os.path.join(path, "state.json.tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=1, sort_keys=True)
        except BaseException:
            os.unlink(tmp)  # never leave a torn temp behind
            raise
        os.replace(tmp, os.path.join(path, "state.json"))

        # events: append only the delta since the last save to THIS path.
        # A first save, or a save to a different path, writes the whole
        # log once — and never again on subsequent saves to that path.
        ev_path = os.path.join(path, "events.jsonl")
        same_file = (
            self._persisted_to == os.path.abspath(ev_path)
            and self._persisted <= len(self.bus)
        )
        if not same_file:
            with open(ev_path, "w", encoding="utf-8") as f:
                f.write(self.bus.to_jsonl())
                if len(self.bus):
                    f.write("\n")
            self._persisted = len(self.bus)
            self._persisted_to = os.path.abspath(ev_path)
        elif len(self.bus) > self._persisted:
            new = self.bus.log()[self._persisted:]
            with open(ev_path, "a", encoding="utf-8") as f:
                f.write("\n".join(
                    json.dumps(e.row(), separators=(",", ":")) for e in new
                ) + "\n")
            self._persisted = len(self.bus)

    @classmethod
    def load(cls, path: str, attach: Callable[["Runtime"], None]) -> "Runtime":
        """Rebuild the organism from disk — and refuse what cannot vouch.

        ``attach(rt)`` re-registers your components IN CODE (closures are
        code, not data) and calls ``rt.ecology.adopt(script)`` to give each
        code-defined script its saved track record back. See
        examples/04_game_npc for the full pattern.

        The door checks (round 20a) — a save that cannot prove itself
        never becomes a running organism:

        * state.json must be valid JSON (a torn or corrupt file raises
          with context, never a stack-trace surprise);
        * events.jsonl must fold to exactly the chain head recorded at
          save time and hold exactly the recorded watermark — any edit,
          drop, splice, or interrupted save is refused by name;
        * the WHY tree must replay its own basis: the conservation
          receipt is RECOMPUTED, not trusted (a flipped state inside
          valid JSON used to boot silently — found by the wave-1
          backend persona probing with a tampered state).
        """
        try:
            with open(os.path.join(path, "state.json"), encoding="utf-8") as f:
                state = json.load(f)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"state.json is not valid JSON — truncated or corrupted? ({exc})"
            ) from exc
        with open(os.path.join(path, "events.jsonl"), encoding="utf-8") as f:
            trunc = state.get("event_truncation")
            anchor = trunc["anchor"] if trunc else "genesis"
            bus = EventBus.from_jsonl(f.read(), anchor=anchor)

        # door check 1: the event chain + watermark. Saves written before
        # round 20a carry no head/watermark — they are checked by the
        # conservation door only (compat: old saves still load).
        # The watermark is checked first: it is the cheaper check and it
        # names the interrupted-save window precisely; the chain check
        # then catches any edit/drop/splice that preserves the count.
        expected_head = state.get("event_chain_head")
        expected_mark = state.get("events_watermark")
        if expected_mark is not None and len(bus) != expected_mark:
            raise ValueError(
                f"events.jsonl holds {len(bus)} events; the save recorded "
                f"{expected_mark} — a save was interrupted, or the file "
                "was changed after the fact"
            )
        if expected_head is not None and bus.chain_head != expected_head:
            raise ValueError(
                "events.jsonl fails its chain check at the door: it was "
                "edited, truncated, or spliced after the save"
            )

        rt = cls(seed=state["seed"], top_k=state["top_k"],
                 attestation_horizon=state.get("attestation_horizon"))
        rt.tick_no = state["tick"]
        rt._idle = state.get("idle", 0)
        rt.why = WhyTree.from_json(state["why"])
        rt.graph = WorldGraph.from_json(state["graph"])
        rt.tensions = TensionField.from_dict(state["tensions"])
        rt.ecology = ScriptEcology.from_json(
            state["ecology"], bus=rt.bus, rng=random.Random(state["seed"] + 1)
        )
        rt.memory = Memory(rt.graph)
        rt.market_log = MarketLog()
        rt.executive = Executive(
            rt.market, bus=rt.bus, max_actions=rt.top_k,
            market_log=rt.market_log,
        )
        rt.sleeper = SleepCycle(
            rt.ecology, rt.memory, bus=rt.bus,
            rng=random.Random(state["seed"] + 2),
            idle_window=state.get("idle_window", 5),
        )
        if state.get("sleeper"):
            rt.sleeper.stats = SleepStats(**state["sleeper"])
        if state.get("identity"):
            rt.identity = Identity.from_dict(state["identity"])
        if state.get("arbiter_scorecard"):
            # the scorecard persists; the arbiter callable itself is code
            # (attach it in your `attach` callback, like any component)
            from .scorecard import ArbiterScorecard
            rt.executive.scorecard = ArbiterScorecard.from_json(
                state["arbiter_scorecard"])
        rt.bus = bus

        # door check 2, the one that matters most: recompute, never trust.
        # A state.json edited after the save (a flipped WHY state inside
        # valid JSON) fails its own replay here instead of booting a
        # silently-wrong organism.
        door = ConservationAuditor().verify(rt.why)
        if not door.ok:
            raise ValueError(
                "state.json fails its conservation check at the door: "
                + door.summary()
            )

        rt._persisted = len(bus)
        rt._persisted_to = os.path.abspath(os.path.join(path, "events.jsonl"))
        rt._last_truncation = state.get("event_truncation")
        attach(rt)
        return rt

    def compact_events(self, path: str, keep: int = 200) -> dict:
        """Snapshot+delta event retention (round 20b — live round 015's
        verdict: NOT a ring buffer, which silently discards causality;
        NOT plain truncation, which loses the chain unless every delta
        is anchored).

        Bounded retention without lying about history: the events file
        is truncated to the most recent ``keep`` events, but ONLY after
        this call saves a full snapshot that proves the state at this
        tick — you never truncate an unverified basis. The dropped
        prefix is folded into an anchor recorded in the state; the
        chain still covers the FULL history, so a truncated file
        verifies at the door exactly as a full one does. What went
        away is a receipt, not a resurrection: pre-snapshot events are
        recoverable only via that anchor, never by rebuilding.

        Compaction is storage-only — the organism's running life is
        untouched (pinned: a compacted run is bit-identical to an
        un-compacted twin). Hosts should call this on epoch boundaries
        or sleep, like journal compaction.
        """
        # 1. the snapshot must vouch before anything is dropped —
        #    never truncate on a basis that cannot prove itself.
        receipt = ConservationAuditor().verify(self.why)
        if not receipt.ok:
            raise RuntimeError(
                "refusing to compact events on a broken conservation basis: "
                + receipt.summary()
            )
        # 2. drop under receipt, then force ONE whole write of the retained
        #    delta (this is the compaction moment, amortized like journal
        #    compaction — later saves append again from here).
        self._last_truncation = self.bus.compact(keep)
        self._persisted = 0
        self._persisted_to = None
        self.save(path)
        return self._last_truncation

    # ------------------------------------------------------------------
    # reporting
    # ------------------------------------------------------------------
    def audit(self):
        """Full conservation receipt: replay basis vs the living tree."""
        return ConservationAuditor().verify(self.why)

    def report(self) -> str:
        c = self.why.conservation()
        return "\n".join([
            f"organism @ tick {self.tick_no}",
            f"  components   : {[c_.id for c_ in self._components.values()]}",
            f"  live scripts : {self.ecology.population()}"
            f"  dead scripts : {len(self.ecology.necrology())}",
            f"  graph        : {self.graph.node_count()} nodes /"
            f" {self.graph.edge_count()} edges",
            f"  events       : {len(self.bus)}",
            f"  why          : alive={c['alive']} dead={c['dead']}"
            f" unknown={c['unknown']} absent={c['absent']}"
            f" ever={c['ever_declared']} invariant_ok={c['invariant_ok']}",
            f"  tensions     : {self.tensions.snapshot()}",
        ])
