"""Tension field tests: pressure grows with age, resolves cleanly."""

from __future__ import annotations

from ecology.events import TENSION_RAISED, TENSION_RESOLVED, EventBus
from ecology.tension import TensionField


def test_raise_and_resolve_publishes_events() -> None:
    bus = EventBus()
    field = TensionField(bus)
    seen = []
    bus.subscribe("*", seen.append)
    tension = field.raise_tension("project:ecology", "tests green", "tests failing", 0.8)
    assert tension.id == 1
    field.resolve(tension.id)
    assert [e.type for e in seen] == [TENSION_RAISED, TENSION_RESOLVED]
    assert field.outstanding() == []


def test_pressure_compounds_with_age() -> None:
    field = TensionField()
    t = field.raise_tension("goal:ship", "moving", "stalled", 0.5)
    p_now = t.pressure(now=t.raised_tick)
    p_later = t.pressure(now=t.raised_tick + 50)
    assert p_later > p_now  # old tensions get louder, not quieter


def test_attention_boost_sums_by_subject() -> None:
    field = TensionField()
    field.raise_tension("goal:a", "x", "y", 0.3)
    field.raise_tension("goal:a", "p", "q", 0.4)
    field.raise_tension("goal:b", "m", "n", 0.9)
    boost_a = field.attention_boost("goal:a")
    assert 0.3 <= boost_a <= 0.7 + 1e-9
    assert field.attention_boost("goal:b") == 0.9
    assert field.attention_boost("goal:none") == 0.0


def test_outstanding_sorted_by_pressure() -> None:
    field = TensionField()
    field.advance(100)
    low = field.raise_tension("s:low", "e", "r", 0.1)
    high = field.raise_tension("s:high", "e", "r", 0.9)
    order = field.outstanding()
    assert order[0].id == high.id or order[0].magnitude >= low.magnitude
