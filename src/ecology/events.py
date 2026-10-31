"""L1 — the Event Fabric.

The nervous system. Everything publishes, nothing polls. Messages are tiny
and strongly typed: a ``type`` string (dot-namespaced), a small payload dict,
a source, and the tick at which they occurred — MIDI-like, not prose.

95% of cognition should occur without language; these events carry state
changes, not essays. The bounded history is the observation stream that the
sleep cycle (L7) consolidates.
"""

from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass, field

Subscriber = Callable[["Event"], None]


@dataclass(frozen=True)
class Event:
    """A tiny, strongly-contracted message.

    ``ts`` is tick time (the world's clock), not wall time — deterministic
    worlds replay exactly.
    """

    type: str
    source: str
    ts: int
    payload: dict = field(default_factory=dict)

    def __str__(self) -> str:
        return f"[t={self.ts}] {self.source} :: {self.type} {self.payload}"


class EventBus:
    """Synchronous publish/subscribe with bounded history and metrics."""

    def __init__(self, history_size: int = 10_000):
        self._subs: dict[str, list[Subscriber]] = defaultdict(list)
        self._history: deque[Event] = deque(maxlen=history_size)
        self.counters: dict[str, int] = defaultdict(int)
        self.published_total = 0

    def subscribe(self, topic: str, fn: Subscriber) -> None:
        """Subscribe to a topic; ``*`` hears everything (audit, sleep)."""
        self._subs[topic].append(fn)

    def publish(self, event: Event) -> None:
        self._history.append(event)
        self.counters[event.type] += 1
        self.published_total += 1
        for fn in self._subs.get(event.type, ()):  # exact topic
            fn(event)
        for fn in self._subs.get("*", ()):  # wildcard observers
            fn(event)

    def history(self, since_tick: int = 0) -> list[Event]:
        """The observation stream since a tick — sleep's raw material."""
        return [e for e in self._history if e.ts >= since_tick]

    def snapshot_counters(self) -> dict[str, int]:
        return dict(self.counters)


# Well-known event types — the fabric's shared contract.
OBSERVATION_RECORDED = "observation.recorded"
TENSION_RAISED = "tension.raised"
TENSION_RESOLVED = "tension.resolved"
JUSTIFICATION_BROKEN = "justification.broken"  # a why-node lost its live root
SCRIPT_PROMOTED = "script.promoted"
SCRIPT_RETIRED = "script.retired"
ROUTINE_CANDIDATE = "routine.candidate"
SLEEP_CYCLE_COMPLETED = "sleep.completed"
BRIEFING_GENERATED = "briefing.generated"
