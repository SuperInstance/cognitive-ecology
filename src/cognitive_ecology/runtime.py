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
"""
from __future__ import annotations

import json
import os
import random
from dataclasses import dataclass, field
from typing import Callable, Iterable, Optional, Protocol, runtime_checkable

from .attention import AttentionBid, AttentionMarket
from .audit import ConservationAuditor
from .events import Event, EventBus, EventKind
from .executive import Executive
from .graph import WorldGraph
from .identity import Identity
from .memory import Memory
from .scripts import Outcome, ScriptEcology
from .sleep import SleepCycle
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
        self.executive = Executive(self.market, bus=self.bus, max_actions=top_k)
        self.ecology = ScriptEcology(bus=self.bus, rng=random.Random(seed + 1))
        self.memory = Memory(self.graph)
        self.sleeper = SleepCycle(
            self.ecology, self.memory, bus=self.bus,
            rng=random.Random(seed + 2), idle_window=idle_window,
        )
        self.identity: Optional[Identity] = None
        self.simulator = None  # optional Simulator; inject for forecast-based EV

        self._components: dict = {}
        self.tick_no = 0
        self._idle = 0
        self._current_cause: Optional[int] = None
        self._last_audit_ok: Optional[bool] = None

    # ------------------------------------------------------------------
    # assembly
    # ------------------------------------------------------------------
    def declare_why(self, statement: str, parent: Optional[str] = None,
                    tick: Optional[int] = None, node_id: Optional[str] = None):
        return self.why.declare(
            statement, parent=parent, tick=self.tick_no if tick is None else tick,
            node_id=node_id,
        )

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

        # 2 + 3. heartbeat gate, then bids
        all_bids: list = []
        for comp in self._components.values():
            if not self.why.why_should_this_run(comp.why_node):
                continue
            all_bids.extend(comp.bid(ctx))

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
            self.bus.emit(
                EventKind.NOTE_ON, (d.bid.label, 1 if out.ok else 0),
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

        The state file carries its own conservation receipt (ADR-0008):
        genesis + necrology + attestation journal replay to exactly this
        state, or the save refuses to vouch for it.
        """
        receipt = ConservationAuditor().verify(self.why)
        os.makedirs(path, exist_ok=True)
        state = {
            "format": "cognitive-ecology/state",
            "version": "0.2.0",
            "tick": self.tick_no,
            "seed": self.seed,
            "top_k": self.top_k,
            "attestation_horizon": self.why.attestation_horizon,
            "idle": self._idle,
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
        }
        with open(os.path.join(path, "state.json"), "w", encoding="utf-8") as f:
            json.dump(state, f, indent=1, sort_keys=True)
        with open(os.path.join(path, "events.jsonl"), "w", encoding="utf-8") as f:
            f.write(self.bus.to_jsonl())

    @classmethod
    def load(cls, path: str, attach: Callable[["Runtime"], None]) -> "Runtime":
        """Rebuild the organism from disk.

        ``attach(rt)`` re-registers your components IN CODE (closures are
        code, not data) and calls ``rt.ecology.adopt(script)`` to give each
        code-defined script its saved track record back. See
        examples/04_game_npc for the full pattern.
        """
        with open(os.path.join(path, "state.json"), encoding="utf-8") as f:
            state = json.load(f)
        with open(os.path.join(path, "events.jsonl"), encoding="utf-8") as f:
            events_text = f.read()

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
        rt.executive = Executive(rt.market, bus=rt.bus, max_actions=rt.top_k)
        rt.sleeper = SleepCycle(
            rt.ecology, rt.memory, bus=rt.bus,
            rng=random.Random(state["seed"] + 2),
        )
        if state.get("identity"):
            rt.identity = Identity.from_dict(state["identity"])
        rt.bus = EventBus.from_jsonl(events_text)
        attach(rt)
        return rt

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
