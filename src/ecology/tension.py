"""The tension field — unresolved prediction error.

The layer closest to awareness: the system continuously reallocates toward
the gap between expectation and reality. A tension is not an error; it is a
claim on attention that stays on the books until resolved, and it bids in
the attention economy on its subject's behalf.

    expected: tests green      observed: tests failing   -> magnitude high
    expected: project moving   observed: project stalled -> magnitude grows with age

Life appears obsessed with prediction error — not because error is bad, but
because error directs attention.
"""

from __future__ import annotations

from dataclasses import dataclass

from .events import TENSION_RAISED, TENSION_RESOLVED, Event, EventBus


@dataclass
class Tension:
    """One unresolved gap between expectation and reality."""

    subject: str
    expectation: str
    reality: str
    magnitude: float
    raised_tick: int
    id: int = 0
    resolved_tick: int | None = None

    def pressure(self, now: int, decay: float = 0.95) -> float:
        """Attention pressure: magnitude, aging toward urgency.

        Old unresolved tensions get louder, not quieter (1/decay^age), until
        they resolve or the system retires the expectation itself.
        """
        age = max(0, now - self.raised_tick)
        return self.magnitude * (decay ** (-min(age, 10_000)))


class TensionField:
    """Tracks outstanding tensions and converts them into attention pressure."""

    def __init__(self, bus: EventBus | None = None):
        self._bus = bus
        self._tensions: dict[int, Tension] = {}
        self._next_id = 1
        self._now = 0

    # ---- clock ----

    def advance(self, tick: int) -> None:
        self._now = tick

    # ---- lifecycle ----

    def raise_tension(
        self,
        subject: str,
        expectation: str,
        reality: str,
        magnitude: float,
    ) -> Tension:
        tension = Tension(
            subject=subject,
            expectation=expectation,
            reality=reality,
            magnitude=max(0.0, magnitude),
            raised_tick=self._now,
            id=self._next_id,
        )
        self._next_id += 1
        self._tensions[tension.id] = tension
        if self._bus is not None:
            self._bus.publish(
                Event(
                    type=TENSION_RAISED,
                    source="tension-field",
                    ts=self._now,
                    payload={
                        "id": tension.id,
                        "subject": subject,
                        "expectation": expectation,
                        "reality": reality,
                        "magnitude": tension.magnitude,
                    },
                )
            )
        return tension

    def resolve(self, tension_id: int) -> Tension | None:
        tension = self._tensions.pop(tension_id, None)
        if tension is not None and self._bus is not None:
            self._bus.publish(
                Event(
                    type=TENSION_RESOLVED,
                    source="tension-field",
                    ts=self._now,
                    payload={"id": tension_id, "subject": tension.subject},
                )
            )
        return tension

    # ---- queries ----

    def outstanding(self) -> list[Tension]:
        return sorted(self._tensions.values(), key=lambda t: -t.pressure(self._now))

    def for_subject(self, subject: str) -> list[Tension]:
        return [t for t in self._tensions.values() if t.subject == subject]

    def attention_boost(self, subject: str, decay: float = 0.95) -> float:
        """Total attention pressure on a subject right now."""
        return sum(t.pressure(self._now, decay=decay) for t in self.for_subject(subject))
