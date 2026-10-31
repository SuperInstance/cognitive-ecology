"""Sleep cycle tests: the mechanical learning pipeline (no LLM anywhere)."""

from __future__ import annotations

from ecology import why
from ecology.events import Event, EventBus
from ecology.runtime import JustificationWatch
from ecology.scripts import ScriptRuntime
from ecology.sleep import SleepCycle
from ecology.tension import TensionField
from ecology.world import WorldGraph


def _world_and_cycle(min_pattern_freq: int = 3):
    bus = EventBus()
    world = WorldGraph()
    scripts = ScriptRuntime(bus)
    tensions = TensionField(bus)
    graph = why.parse_graph("routine:telemetry -> goal:casey (explicit)")
    att = why.parse_attestation("goal:casey alive 2024-01-01 casey")
    watch = JustificationWatch(graph, att, bus)
    cycle = SleepCycle(
        bus, world, scripts, watch, tensions, min_pattern_freq=min_pattern_freq
    )
    return bus, world, scripts, tensions, watch, cycle


def _observe(bus: EventBus, tick: int, sensor: str = "cpu") -> None:
    bus.publish(
        Event("observation.telemetry", "environment", tick, {"sensor": sensor, "value": 0.5})
    )


def test_repetition_becomes_a_routine() -> None:
    bus, world, scripts, tensions, watch, cycle = _world_and_cycle()
    for tick in range(5):
        _observe(bus, tick)
    report = cycle.run(since_tick=0, now_tick=5)
    # telemetry/cpu repeated 5 times: pattern -> candidate -> validated
    assert "observation.telemetry/cpu" in report.patterns
    assert "routine:observation.telemetry/cpu" in report.validated
    assert scripts.scripts["routine:observation.telemetry/cpu"].origin == "sleep-promoted"
    # memory graduated observation -> episode -> pattern -> routine
    assert world.node("memory:observation.telemetry/cpu").attrs["maturity"] == "routine"


def test_rare_events_do_not_become_routines() -> None:
    bus, world, scripts, tensions, watch, cycle = _world_and_cycle()
    _observe(bus, 0, sensor="cpu")
    _observe(bus, 1, sensor="disk")
    _observe(bus, 2, sensor="net")
    report = cycle.run(0, 3)
    assert report.validated == []  # nothing repeated enough
    assert report.patterns == []


def test_sleep_does_not_duplicate_machinery() -> None:
    bus, world, scripts, tensions, watch, cycle = _world_and_cycle()
    for tick in range(4):
        _observe(bus, tick)
    first = cycle.run(0, 4)
    for tick in range(4, 8):
        _observe(bus, tick)
    second = cycle.run(4, 8)
    assert len(first.validated) == 1
    assert second.validated == []  # already compiled


def test_born_routine_handles_future_events() -> None:
    bus, world, scripts, tensions, watch, cycle = _world_and_cycle()
    for tick in range(3):
        _observe(bus, tick)
    cycle.run(0, 3)
    routine = scripts.scripts["routine:observation.telemetry/cpu"]
    # the compiled routine runs on the next observation and learns
    _observe(bus, 10)
    ran = scripts.handle_event(
        Event("observation.telemetry", "environment", 10, {"sensor": "cpu"}), budget=1.0
    )
    assert routine.name in ran
    node = world.node("memory:observation.telemetry/cpu")
    assert node.attrs.get("handled", 0) >= 1


def test_why_breakage_surfaces_at_night() -> None:
    bus, world, scripts, tensions, watch, cycle = _world_with_breakage()
    report = cycle.run(0, 1)
    assert "routine:telemetry" in report.why_broken


def _world_with_breakage():
    bus = EventBus()
    world = WorldGraph()
    scripts = ScriptRuntime(bus)
    tensions = TensionField(bus)
    graph = why.parse_graph("routine:telemetry -> goal:casey (explicit)")
    att = why.parse_attestation("goal:casey alive 2024-01-01 casey")
    watch = JustificationWatch(graph, att, bus)
    watch.recheck(0)  # establish the alive baseline
    # the root's liveness is withdrawn -> routine becomes questionable
    att.roots.pop("goal:casey")
    watch._dirty = True
    cycle = SleepCycle(bus, world, scripts, watch, tensions)
    return bus, world, scripts, tensions, watch, cycle


def test_sleep_report_carries_tension_count() -> None:
    bus, world, scripts, tensions, watch, cycle = _world_and_cycle()
    tensions.raise_tension("memory:x", "known", "novel", 0.5)
    report = cycle.run(0, 1)
    assert report.tensions_outstanding == 1
