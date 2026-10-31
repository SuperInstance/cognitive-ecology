"""L0 — the Runtime.

Law 1: time is the substrate. Nothing is event-driven internally — events
perturb ongoing processes. Every component registers as a long-lived process
with a ``tick()``; the world never "starts", it is always running, and user
interaction is merely one event stream.

Each tick:
1. the clock advances (tensions age),
2. processes bid for attention (their bids are multiplied by the WHY weight
   of their justification chain — Law 3 as the scheduler),
3. the attention policy allocates the tick budget,
4. processes with granted energy run; processes granted nothing starve for
   a tick — they are not killed. The economy is not a hierarchy.

The runtime is deliberately boring. Very boring, very important: life is
mostly boring, and the runtime must keep working with zero LLMs (Law 4).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from . import why
from .attention import Allocation, AllocationPolicy, Bid, HybridPolicy, justification_weight
from .events import JUSTIFICATION_BROKEN, Event, EventBus
from .tension import TensionField
from .world import WorldGraph


@runtime_checkable
class Process(Protocol):
    """A long-lived citizen of the ecology."""

    name: str

    def tick(self, ctx: TickContext) -> None: ...  # pragma: no cover


@dataclass
class TickContext:
    """What a process may touch during its slice of a tick."""

    tick: int
    budget: float
    world: WorldGraph
    bus: EventBus
    tensions: TensionField


@dataclass
class ProcessHandle:
    process: Process
    #: the WHY node that justifies this process's existence ("why_node")
    why_node: str | None = None
    #: produces the bid each tick; None -> a minimal keep-alive bid
    bid_fn: Callable[[int], Bid] | None = None
    starved_ticks: int = 0
    ticks_run: int = 0


@dataclass
class TickReport:
    tick: int
    allocation: Allocation = field(default_factory=Allocation)
    ran: list[str] = field(default_factory=list)
    starved: list[str] = field(default_factory=list)


class JustificationWatch:
    """The conservation law, enforced per tick.

    Holds the WHY graph + attestations, re-evaluates on demand, and emits
    ``justification.broken`` when a node that was alive loses its last live
    root — the moment the manifesto calls *questionable, not deleted*.
    """

    def __init__(self, graph: why.Graph, attestation: why.Attestation, bus: EventBus | None = None):
        self.graph = graph
        self.attestation = attestation
        self.bus = bus
        self._last: dict[str, why.Status] = {}
        self._evaluation: why.Evaluation | None = None
        self._dirty = True

    # ---- maintenance ----

    def set_attestation(self, root: why.RootAttestation) -> None:
        self.attestation.insert(root)
        self._dirty = True

    def add_edge(self, child: str, parent: str, provenance: why.Provenance) -> None:
        self.graph.add_edge(child, parent, provenance)
        self._dirty = True

    # ---- queries ----

    @property
    def evaluation(self) -> why.Evaluation:
        if self._evaluation is None or self._dirty:
            self._evaluation = why.evaluate(self.graph, self.attestation)
            self._dirty = False
        return self._evaluation

    def status_of(self, node_id: str) -> why.Status:
        return self.evaluation.status_of(node_id)

    def weight_of(self, node_id: str) -> float:
        """How much a bid backed by this node's justification counts."""
        return justification_weight(self.status_of(node_id).value)

    # ---- the night job (also called eagerly by the runtime) ----

    def recheck(self, tick: int) -> list[str]:
        """Re-evaluate and report nodes that lost their justification.

        Returns the ids that transitioned alive -> dead|unknown this pass,
        and publishes ``justification.broken`` for each. Dependents become
        questionable, not deleted.
        """
        self._dirty = True
        current = self.evaluation.status
        broken: list[str] = []
        for node_id, status in current.items():
            previous = self._last.get(node_id)
            if previous is why.Status.ALIVE and status is not why.Status.ALIVE:
                broken.append(node_id)
                if self.bus is not None:
                    self.bus.publish(
                        Event(
                            type=JUSTIFICATION_BROKEN,
                            source="why-watch",
                            ts=tick,
                            payload={"node": node_id, "from": "alive", "to": status.value},
                        )
                    )
        self._last = dict(current)
        return broken


class Runtime:
    """The heartbeat. The world exists before the player logs in."""

    def __init__(
        self,
        bus: EventBus,
        world: WorldGraph,
        *,
        tensions: TensionField | None = None,
        watch: JustificationWatch | None = None,
        policy: AllocationPolicy | None = None,
        budget_per_tick: float = 10.0,
        min_energy: float = 1e-9,
        dt: float = 1.0,
    ):
        self.bus = bus
        self.world = world
        self.tensions = tensions or TensionField(bus)
        self.watch = watch
        self.policy: AllocationPolicy = policy or HybridPolicy()
        self.budget_per_tick = budget_per_tick
        self.min_energy = min_energy
        self.dt = dt
        self.handles: dict[str, ProcessHandle] = {}
        self.tick_count = 0

    # ---- registration ----

    def register(
        self,
        process: Process,
        why_node: str | None = None,
        bid_fn: Callable[[int], Bid] | None = None,
    ) -> ProcessHandle:
        handle = ProcessHandle(process=process, why_node=why_node, bid_fn=bid_fn)
        self.handles[process.name] = handle
        return handle

    def unregister(self, name: str) -> None:
        self.handles.pop(name, None)

    # ---- the loop ----

    def tick(self) -> TickReport:
        tick = self.tick_count
        self.tick_count += 1
        self.tensions.advance(tick)
        report = TickReport(tick=tick)

        # WHY recheck: justification breakage becomes events + bid weights.
        if self.watch is not None:
            self.watch.recheck(tick)

        # 1. collect bids, justified by WHY (Law 3 as the scheduler)
        bids: list[Bid] = []
        for handle in self.handles.values():
            if handle.bid_fn is not None:
                bid = handle.bid_fn(tick)
            else:
                # A process that claims nothing else still bids with its
                # justification (all factors at 1.0 -> score == WHY weight).
                bid = Bid.keepalive(handle.process.name)
            bid.bidder = handle.process.name
            if handle.why_node is not None and self.watch is not None:
                bid.justification = self.watch.weight_of(handle.why_node)
            bids.append(bid)

        # 2. allocate the tick budget (Law 2)
        report.allocation = self.policy.allocate(bids, self.budget_per_tick)

        # 3. run the funded processes; starve the rest
        for handle in self.handles.values():
            energy = report.allocation.energy(handle.process.name)
            if energy >= self.min_energy:
                ctx = TickContext(
                    tick=tick,
                    budget=energy,
                    world=self.world,
                    bus=self.bus,
                    tensions=self.tensions,
                )
                handle.process.tick(ctx)
                handle.ticks_run += 1
                report.ran.append(handle.process.name)
            else:
                handle.starved_ticks += 1
                report.starved.append(handle.process.name)

        return report

    def run(self, ticks: int) -> list[TickReport]:
        return [self.tick() for _ in range(ticks)]
