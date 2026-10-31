"""Simulation engine and identity tests."""

from __future__ import annotations

import pytest

from ecology.identity import Identity
from ecology.sim import Scenario, SimulationEngine

# ---- L3: budgeted futures ----


def test_scenarios_run_while_budget_lasts() -> None:
    engine = SimulationEngine()
    engine.add(Scenario("likely", fn=lambda t: {"value": t}, horizon=10, cost_per_tick=0.1))
    engine.add(Scenario("risky", fn=lambda t: {"value": -t}, horizon=10, cost_per_tick=0.1))
    results = engine.run(budget=2.0)  # each costs 1.0 -> both run
    assert [r.name for r in results] == ["likely", "risky"]


def test_priority_decides_which_futures_run() -> None:
    engine = SimulationEngine()
    engine.add(
        Scenario("boring", fn=lambda t: {"value": 1}, horizon=10, cost_per_tick=0.1,
                 novelty=0.1, importance=0.5, uncertainty=0.1)
    )
    engine.add(
        Scenario("crucial", fn=lambda t: {"value": 2}, horizon=10, cost_per_tick=0.1,
                 novelty=1.0, importance=1.0, uncertainty=1.0)
    )
    results = engine.run(budget=1.0)  # only one fits
    assert [r.name for r in results] == ["crucial"]


def test_zero_priority_never_runs() -> None:
    engine = SimulationEngine()
    engine.add(Scenario("known", fn=lambda t: {"value": 1}, uncertainty=0.0))
    assert engine.run(budget=100.0) == []


def test_trend_computed_from_primary_metric() -> None:
    engine = SimulationEngine()
    engine.add(Scenario("growth", fn=lambda t: {"value": t * 2}, horizon=5, cost_per_tick=0.1))
    (result,) = engine.run(budget=1.0)
    assert result.trend == pytest.approx(8.0)  # final 8 - first 0


# ---- identity as a stable attractor ----


def test_reinforce_moves_the_attractor_slowly() -> None:
    identity = Identity()
    before = dict(identity.values)
    identity.reinforce("truth", 1.0, rate=0.2)
    assert identity.values["truth"] > before["truth"]
    assert sum(identity.values.values()) == pytest.approx(1.0)  # stays a distribution


def test_stability_of_a_decided_identity() -> None:
    identity = Identity(values={"truth": 0.98, "usefulness": 0.01, "exploration": 0.01})
    assert identity.stability() > 0.8
    uniform = Identity(values={"truth": 1 / 3, "usefulness": 1 / 3, "exploration": 1 / 3})
    assert uniform.stability() == pytest.approx(0.0, abs=1e-9)


def test_sustained_pressure_settles_identity() -> None:
    identity = Identity()
    for _ in range(50):
        identity.reinforce("exploration", 1.0, rate=0.1)
    assert identity.top_values(1)[0][0] == "exploration"
    assert identity.stability() > 0.3
