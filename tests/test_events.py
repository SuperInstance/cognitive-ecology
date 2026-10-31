"""L1 event fabric tests."""

from __future__ import annotations

from ecology.events import Event, EventBus


def test_publish_subscribe_exact_topic() -> None:
    bus = EventBus()
    seen = []
    bus.subscribe("observation.recorded", seen.append)
    bus.publish(Event("observation.recorded", "sensor", 1, {"value": 3}))
    bus.publish(Event("tension.raised", "tension-field", 1, {}))
    assert len(seen) == 1
    assert seen[0].payload == {"value": 3}


def test_wildcard_hears_everything() -> None:
    bus = EventBus()
    seen = []
    bus.subscribe("*", seen.append)
    bus.publish(Event("a.b", "x", 1))
    bus.publish(Event("c.d", "y", 2))
    assert len(seen) == 2


def test_history_and_counters() -> None:
    bus = EventBus(history_size=4)
    for i in range(6):
        bus.publish(Event("tick", "rt", i))
    assert bus.published_total == 6
    assert bus.counters["tick"] == 6
    # bounded: only the last 4 survive
    assert [e.ts for e in bus.history()] == [2, 3, 4, 5]
    assert [e.ts for e in bus.history(since_tick=4)] == [4, 5]
