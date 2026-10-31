"""L1 — events: tiny, immutable, append-only, causally chained."""
import json

from cognitive_ecology import Event, EventBus, EventKind


def test_emit_assigns_seq_and_subscribers_hear():
    bus = EventBus()
    seen = []
    bus.subscribe(lambda e: seen.append(e))
    e1 = bus.emit(EventKind.STATE, ("berry:1", {"food": 0}), src="critter", ts=1)
    e2 = bus.emit(EventKind.NOTE_ON, ("forage", 1), src="critter", ts=1, cause=e1.seq)
    assert e1.seq == 1 and e2.seq == 2
    assert e2.cause == 1
    assert len(seen) == 2


def test_subscribe_filter_and_broken_listener_survives():
    bus = EventBus()
    tension_events = []
    bus.subscribe(lambda e: tension_events.append(e), kinds=[EventKind.TENSION])
    bus.subscribe(lambda e: 1 / 0)  # broken listeners must not stop the bus
    bus.emit(EventKind.TENSION, ("energy", 0.3), src="tensions", ts=1)
    bus.emit(EventKind.STATE, ("x", {}), src="x", ts=1)
    assert len(tension_events) == 1


def test_window_and_since():
    bus = EventBus()
    for i in range(10):
        bus.emit(EventKind.STATE, (f"n{i}", {}), src="s", ts=i)
    assert [e.payload[0] for e in bus.window(3)] == ["n7", "n8", "n9"]
    assert len(bus.since(8)) == 2


def test_jsonl_round_trip():
    bus = EventBus()
    bus.emit(EventKind.STATE, ("berry:1", {"food": 0, "ripe": True}), src="critter", ts=3)
    bus.emit(EventKind.SIGNAL, ("journal", "hello world"), src="agent", ts=3, cause=1)
    text = bus.to_jsonl()
    bus2 = EventBus.from_jsonl(text)
    assert len(bus2) == 2
    e = bus2.log()[1]
    assert e.kind is EventKind.SIGNAL and e.cause == 1 and e.payload == ("journal", "hello world")
    # and the bus continues from the right seq
    e3 = bus2.emit(EventKind.STATE, ("x", {}), src="x", ts=4)
    assert e3.seq == 3


def test_midi_size_budget():
    """The design promise: a typical event serializes to ~100-160 bytes."""
    bus = EventBus()
    e = bus.emit(EventKind.STATE, ("berry:3", {"food": 1, "ripe": True}), src="critter", ts=42, cause=17)
    assert e.size() < 160, f"event too fat: {e.size()} bytes"
    e2 = bus.emit(EventKind.DECISION, ("forage", "critter", "run", 0.7312), src="executive", ts=42)
    assert e2.size() < 160


def test_events_are_frozen():
    bus = EventBus()
    e = bus.emit(EventKind.STATE, ("x", {}), src="s", ts=1)
    try:
        e.src = "hacker"
        raise AssertionError("events must be immutable")
    except AttributeError:
        pass
