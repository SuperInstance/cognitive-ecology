"""Script ecology tests: promotion, retirement, budget, learning."""

from __future__ import annotations

from ecology.events import Event, EventBus
from ecology.scripts import Script, ScriptResult, ScriptRuntime


def _ok(ctx: dict) -> ScriptResult:
    return ScriptResult(success=True, utility=0.8)


def _weak(ctx: dict) -> ScriptResult:
    return ScriptResult(success=True, utility=0.04)


def _fail(ctx: dict) -> ScriptResult:
    return ScriptResult(success=False)


def _event(ts: int = 0) -> Event:
    return Event("observation.telemetry", "environment", ts, {"sensor": "cpu"})


def test_candidate_promotes_after_two_successes() -> None:
    bus = EventBus()
    promoted = []
    bus.subscribe("script.promoted", promoted.append)
    rt = ScriptRuntime(bus)
    rt.register(Script(name="s", trigger="observation.telemetry", fn=_ok))
    assert rt.scripts["s"].status == "candidate"
    rt.handle_event(_event(), budget=10)
    rt.handle_event(_event(), budget=10)
    assert rt.scripts["s"].status == "active"
    assert [e.payload["script"] for e in promoted] == ["s"]


def test_utility_learned_as_ema() -> None:
    rt = ScriptRuntime()
    rt.register(Script(name="s", trigger="observation.telemetry", fn=_ok))
    for _ in range(10):
        rt.handle_event(_event(), budget=10)
    # EMA converges toward 0.8
    assert 0.5 < rt.scripts["s"].utility <= 0.8


def test_weak_script_retires_itself() -> None:
    bus = EventBus()
    retired = []
    bus.subscribe("script.retired", retired.append)
    rt = ScriptRuntime(bus)
    rt.register(Script(name="weak", trigger="observation.telemetry", fn=_weak))
    rt.scripts["weak"].status = "active"  # pretend it already graduated
    for _ in range(6):
        rt.handle_event(_event(), budget=10)
    assert rt.scripts["weak"].status == "retired"
    assert retired and retired[0].payload["script"] == "weak"


def test_budget_limits_how_many_scripts_run() -> None:
    rt = ScriptRuntime()
    for i in range(10):
        rt.register(Script(name=f"s{i}", trigger="observation.telemetry", fn=_ok, cost=1.0))
    ran = rt.handle_event(_event(), budget=3.5)
    assert len(ran) == 3  # 3.5 budget, cost 1.0 each


def test_expected_value_orders_execution() -> None:
    rt = ScriptRuntime()
    # low-EV script registered first; high-EV must still run when budget is tight
    rt.register(
        Script(name="low", trigger="observation.telemetry", fn=_weak, cost=1.0, utility=0.0)
    )
    rt.register(
        Script(name="high", trigger="observation.telemetry", fn=_ok, cost=1.0, utility=1.0)
    )
    ran = rt.handle_event(_event(), budget=1.0)
    assert ran == ["high"]


def test_conditions_gate_execution() -> None:
    rt = ScriptRuntime()
    rt.register(
        Script(
            name="only-cpu",
            trigger="observation.telemetry",
            fn=_ok,
            conditions=lambda ctx: ctx["payload"].get("sensor") == "cpu",
        )
    )
    assert rt.handle_event(_event(), budget=10) == ["only-cpu"]
    other = Event("observation.telemetry", "environment", 0, {"sensor": "disk"})
    assert rt.handle_event(other, budget=10) == []


def test_script_exception_does_not_kill_runtime() -> None:
    def boom(ctx: dict) -> ScriptResult:
        raise RuntimeError("script bug")

    rt = ScriptRuntime()
    rt.register(Script(name="buggy", trigger="observation.telemetry", fn=boom))
    ran = rt.handle_event(_event(), budget=10)
    assert ran == ["buggy"]
    assert rt.scripts["buggy"].failures == 1


def test_census_and_retirement_candidates() -> None:
    rt = ScriptRuntime()
    rt.register(Script(name="c", trigger="tick", fn=_ok))
    weak = Script(name="w", trigger="tick", fn=_weak, utility=0.0)
    weak.status = "active"
    weak.runs = 10
    rt.register(weak)
    assert rt.census() == {"candidate": 1, "active": 1, "retired": 0}
    assert [s.name for s in rt.retirement_candidates()] == ["w"]
