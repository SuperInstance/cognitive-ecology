"""L1 — the event substrate.

MIDI inspired. In MIDI, a *note on* is one status byte plus two data bytes:
tiny, immutable, ordered, and meaningless alone — meaning comes from the
sequence. Same idea here. Every observable change in the organism is an
``Event``: a frozen, slots-packed record of roughly ~100 bytes serialized,
chained to its cause by ``seq``.

Design rules
------------
* Events are APPEND-ONLY. There is no API to edit or delete an event.
* ``payload`` is a small tuple of JSON primitives. If you need structure,
  emit more events, not bigger ones.
* ``cause`` links an event to the decision (or event) that produced it,
  giving every effect a causal chain you can walk backwards.

Payload conventions used across the kernel
------------------------------------------
* ``STATE``    -> (entity_id, props_dict)          world changed for one entity
* ``SIGNAL``   -> (target, text)                   a message between components
* ``TENSION``  -> (name, level)                    a drive's new level
* ``DECISION`` -> (label, src, status, attention)  the executive spoke
* ``WHY``      -> (node_id, from, to, reason)      purpose changed state
* ``BIRTH`` / ``DEATH`` -> (script_name, why_node, detail)
* ``EXCHANGE`` -> (treaty_id, what, provider, beneficiary, detail)
  society-level receipts: service routed between organisms, treaties
  established / broken / revoked (society.py, ADR-0011)
"""
from __future__ import annotations

import json
from dataclasses import dataclass, replace
from enum import IntEnum
from typing import Callable, Iterable, Optional, Union

from .util import stable_hash


class EventKind(IntEnum):
    NOTE_ON = 1    # an action fired
    NOTE_OFF = 2   # a phase ended (e.g. the organism slept)
    STATE = 3      # world-state delta for one entity
    SIGNAL = 4     # a message between components
    TENSION = 5    # a homeostatic drive changed level
    DECISION = 6   # the executive cleared or vetoed a bid
    WHY = 7        # a WHY node changed state
    BIRTH = 8      # a script was spawned into the ecology
    DEATH = 9      # a script starved out (necrology entry follows)
    ERROR = 10     # something failed; the organism continues
    EXCHANGE = 11  # a treaty routed something between organisms (society.py)


@dataclass(frozen=True, slots=True)
class Event:
    """One immutable, MIDI-sized happening."""

    kind: EventKind
    ts: int                      # tick, not wall-clock: reproducible worlds
    src: str                     # component id that emitted it
    payload: tuple = ()
    cause: Optional[int] = None  # seq of the event/decision that caused this
    seq: int = -1                # assigned by the bus at emit time

    def row(self) -> list:
        """Compact serialization: [seq, kind, ts, src, cause, payload]."""
        return [self.seq, int(self.kind), self.ts, self.src, self.cause, list(self.payload)]

    @staticmethod
    def from_row(row: list) -> "Event":
        seq, kind, ts, src, cause, payload = row
        return Event(
            kind=EventKind(int(kind)), ts=int(ts), src=str(src),
            payload=tuple(payload), cause=cause, seq=int(seq),
        )

    def size(self) -> int:
        """Serialized size in bytes — the MIDI-size budget check."""
        return len(json.dumps(self.row(), separators=(",", ":")))


class EventBus:
    """Append-only log + fan-out. The organism's nervous system."""

    def __init__(self) -> None:
        self._log: list[Event] = []
        self._subs: list = []
        self._seq = 0
        # Tamper-evidence for the WHOLE log (round 20a): a fold of every
        # event row in seq order, maintained incrementally on emit and
        # rebuilt on from_jsonl. One sha256 per event (~19/tick) and zero
        # bytes added to any event — the chain lives on the bus, not in
        # the rows. save() records the head; load() refuses a file that
        # folds to anything else (edits, drops, splices — all caught).
        self.chain_head: str = "genesis"
        # Round 20b: after compact(), the dropped prefix is summarized by
        # this anchor — the fold of everything that was ever dropped, in
        # order. The invariant is: chain_head == fold(anchor, retained
        # rows...) == fold("genesis", ALL rows ever emitted). The anchor
        # lets the door verify a truncated file without resurrecting the
        # dropped events — they are a receipt, not a resurrection.
        self.chain_anchor: str = "genesis"

    @staticmethod
    def _fold(head: str, ev: "Event") -> str:
        row = json.dumps(ev.row(), separators=(",", ":"))
        return stable_hash(f"{head}:{row}")

    # -- emission -------------------------------------------------------
    @property
    def seq(self) -> int:
        return self._seq

    def emit(
        self,
        kind: Union[EventKind, int],
        payload: Iterable = (),
        src: str = "?",
        ts: int = 0,
        cause: Optional[int] = None,
    ) -> Event:
        """Append an event; returns it with its assigned seq."""
        self._seq += 1
        ev = Event(
            kind=EventKind(int(kind)), ts=int(ts), src=str(src),
            payload=tuple(payload), cause=cause, seq=self._seq,
        )
        self._log.append(ev)
        self.chain_head = self._fold(self.chain_head, ev)
        # Subscribers are best-effort: a broken listener must never
        # stop the organism's heartbeat. Failures are swallowed by design.
        for fn, kinds in self._subs:
            if kinds is None or ev.kind in kinds:
                try:
                    fn(ev)
                except Exception:
                    pass
        return ev

    def subscribe(
        self, fn: Callable[[Event], None], kinds: Optional[Iterable] = None
    ) -> int:
        """Get called for every event (or a filtered set). Best-effort."""
        sub = (fn, tuple(kinds) if kinds is not None else None)
        self._subs.append(sub)
        return len(self._subs) - 1

    # -- reading --------------------------------------------------------
    def log(self) -> tuple:
        return tuple(self._log)

    def __len__(self) -> int:
        return len(self._log)

    def window(self, n: int) -> list:
        """The most recent ``n`` events (n <= 0 -> [])."""
        return self._log[-n:] if n and n > 0 else []

    def since(self, seq: int) -> list:
        return [e for e in self._log if e.seq > seq]

    def compact(self, keep: int) -> dict:
        """Receipted truncation (round 20b): drop the oldest events.

        Keeps the most recent ``keep`` events in memory and on disk; the
        dropped prefix is folded into ``chain_anchor`` so the chain keeps
        covering the FULL history — the head still summarizes everything
        ever emitted, and a truncated file still verifies at the door.
        Nothing is deleted silently: the caller records the returned
        receipt (dropped/kept/anchor) wherever it keeps state, and the
        events that went are recoverable only via that receipt, never by
        resurrection. History is compacted, not rewritten.
        """
        keep = max(0, int(keep))
        n = len(self._log)
        if n <= keep:
            return {"dropped": 0, "kept": n, "anchor": self.chain_anchor}
        dropped_rows = self._log[: n - keep]
        anchor = self.chain_anchor
        for ev in dropped_rows:
            anchor = self._fold(anchor, ev)
        self._log = self._log[n - keep:]
        self.chain_anchor = anchor
        # chain_head is deliberately NOT recomputed: it already covers
        # the dropped prefix — that is the whole point of the anchor.
        return {"dropped": len(dropped_rows), "kept": keep, "anchor": anchor}

    # -- persistence ----------------------------------------------------
    def to_jsonl(self) -> str:
        return "\n".join(
            json.dumps(e.row(), separators=(",", ":")) for e in self._log
        )

    @classmethod
    def from_jsonl(cls, text: str, anchor: str = "genesis") -> "EventBus":
        """Rebuild the bus from a (possibly truncated) log.

        ``anchor`` is the fold of the prefix that was compacted away
        (round 20b): the chain resumes from it, so a truncated file folds
        to exactly the head the full history would have produced.
        """
        bus = cls()
        bus.chain_anchor = anchor
        head = anchor
        for line in text.splitlines():
            if not line.strip():
                continue
            ev = Event.from_row(json.loads(line))
            bus._log.append(ev)
            head = bus._fold(head, ev)
            if ev.seq > bus._seq:
                bus._seq = ev.seq
        bus.chain_head = head
        return bus
