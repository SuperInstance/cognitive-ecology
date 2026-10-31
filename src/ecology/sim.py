"""L3 — Simulated Futures.

Every domain owns simulators that continuously run *budgeted* futures: not
infinite what-ifs, but a handful of likely / risky / novel / high-value
scenarios. A scenario is a pure function from tick to a projected metric —
deterministic, replayable, cheap — and the engine decides which futures
deserve exploration while the budget lasts.

Simulation budget priority (Open Question #3): novelty x importance x
uncertainty. A scenario scoring zero on any axis can wait forever.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class Scenario:
    """A budgeted future: a deterministic projection of one what-if."""

    name: str
    fn: Callable[[int], dict]  # tick -> projected metrics
    horizon: int = 10
    cost_per_tick: float = 0.1
    importance: float = 0.5
    novelty: float = 0.5
    uncertainty: float = 0.5

    @property
    def priority(self) -> float:
        """Which futures deserve exploration: novelty x importance x uncertainty."""
        return self.novelty * self.importance * self.uncertainty


@dataclass
class ScenarioResult:
    name: str
    series: list[dict] = field(default_factory=list)
    cost: float = 0.0
    final: dict = field(default_factory=dict)
    trend: float = 0.0  # last - first of the primary metric, when present


class SimulationEngine:
    """Runs scenarios while the budget lasts, highest priority first."""

    def __init__(self):
        self.scenarios: dict[str, Scenario] = {}

    def add(self, scenario: Scenario) -> None:
        self.scenarios[scenario.name] = scenario

    def run(self, budget: float, primary: str = "value") -> list[ScenarioResult]:
        results: list[ScenarioResult] = []
        remaining = budget
        for scenario in sorted(self.scenarios.values(), key=lambda s: -s.priority):
            total_cost = scenario.cost_per_tick * scenario.horizon
            if scenario.priority <= 0 or remaining < total_cost:
                continue
            remaining -= total_cost
            series = [scenario.fn(t) for t in range(scenario.horizon)]
            final = series[-1] if series else {}
            trend = 0.0
            if series and primary in series[0] and primary in final:
                trend = final[primary] - series[0][primary]
            results.append(
                ScenarioResult(
                    name=scenario.name,
                    series=series,
                    cost=total_cost,
                    final=final,
                    trend=trend,
                )
            )
        return results
