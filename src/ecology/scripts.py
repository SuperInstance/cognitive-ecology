"""L4 — the Script Ecology.

Agents are not LLMs. Agents are script collections (the zMUD insight): most
are deterministic, most never invoke a model, and the runtime stays cheap.
Every script carries a trigger, conditions, a cost, a *learned* utility, and
a success rate — and must answer, in aggregate, why it remains part of the
organism.

Lifecycle (the promotion pipeline):

    candidate --(2+ successes)--> active --(utility collapse)--> retired

Candidates are born from the sleep cycle (patterns noticed while nobody was
watching) or seeded by teachers. Retirement is not deletion: the script and
its metrics remain in the ledger as institutional memory.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field

from .events import (
    SCRIPT_PROMOTED,
    SCRIPT_RETIRED,
    Event,
    EventBus,
)

#: after this many successes a candidate is promoted to active
PROMOTE_AFTER_SUCCESSES = 2
#: a script that has run at least this often and still sits below this
#: utility is a retirement candidate — "why should I remain part of the organism?"
RETIRE_AFTER_RUNS = 5
RETIRE_BELOW_UTILITY = 0.1
#: utility tracks recent performance with this exponential moving average
UTILITY_EMA = 0.3


@dataclass
class ScriptResult:
    success: bool
    note: str = ""
    utility: float = 0.0  # immediate utility realized by this run


@dataclass
class Script:
    name: str
    trigger: str  # an event type, or "tick"
    fn: Callable[[dict], ScriptResult]
    owner: str = "kernel"
    conditions: Callable[[dict], bool] = field(default=lambda ctx: True)
    cost: float = 1.0
    utility: float = 0.0  # learned, EMA
    runs: int = 0
    successes: int = 0
    failures: int = 0
    status: str = "candidate"  # candidate | active | retired
    born_tick: int = 0
    generation: int = 0
    origin: str = "seeded"  # seeded | sleep-promoted | taught

    @property
    def success_rate(self) -> float:
        return self.successes / self.runs if self.runs else 0.0

    @property
    def expected_value(self) -> float:
        """Utility per unit cost — the script economy's exchange rate.

        Before any run there is no success rate, so the seeded utility acts
        as the prior (sleep seeds it from replay gain; teachers seed it from
        judgment). After runs, realized performance takes over.
        """
        if self.cost <= 0:
            return self.utility
        if self.runs == 0:
            return self.utility / self.cost
        return (self.utility * self.success_rate) / self.cost


class ScriptRuntime:
    """Runs scripts on events and ticks, within budget, learning utility."""

    def __init__(self, bus: EventBus | None = None):
        self.bus = bus
        self.scripts: dict[str, Script] = {}
        self._recent: deque[str] = deque(maxlen=256)

    # ---- registry ----

    def register(self, script: Script) -> Script:
        self.scripts[script.name] = script
        return script

    def retire(self, name: str, reason: str = "") -> Script | None:
        script = self.scripts.get(name)
        if script is None or script.status == "retired":
            return script
        script.status = "retired"
        if self.bus is not None:
            self.bus.publish(
                Event(
                    type=SCRIPT_RETIRED,
                    source="script-runtime",
                    ts=0,
                    payload={"script": name, "reason": reason, "runs": script.runs},
                )
            )
        return script

    # ---- execution ----

    def handle_event(self, event: Event, budget: float) -> list[str]:
        """Run every non-retired script whose trigger matches this event,
        highest expected value first, while budget lasts."""
        ctx = {"event": event.type, "source": event.source, "payload": event.payload}
        return self._execute(ctx, event.ts, budget, trigger=event.type)

    def handle_tick(self, tick: int, budget: float) -> list[str]:
        ctx = {"event": "tick", "tick": tick}
        return self._execute(ctx, tick, budget, trigger="tick")

    def _execute(self, ctx: dict, tick: int, budget: float, trigger: str) -> list[str]:
        matching = [
            s
            for s in self.scripts.values()
            if s.trigger == trigger and s.status != "retired" and s.conditions(ctx)
        ]
        matching.sort(key=lambda s: -s.expected_value)
        ran: list[str] = []
        remaining = budget
        for script in matching:
            if remaining < script.cost:
                break  # budget exhausted; the rest wait for the next event
            remaining -= script.cost
            script.runs += 1
            try:
                result = script.fn(ctx)
            except Exception as exc:  # a script failure never kills the runtime
                result = ScriptResult(success=False, note=f"error: {exc}")
            if result.success:
                script.successes += 1
            else:
                script.failures += 1
            # learned utility: EMA of realized utility, decaying on failure
            target = result.utility if result.success else 0.0
            script.utility = (1 - UTILITY_EMA) * script.utility + UTILITY_EMA * target
            self._lifecycle(script, tick)
            ran.append(script.name)
        return ran

    def _lifecycle(self, script: Script, tick: int) -> None:
        if script.status == "candidate":
            if script.successes >= PROMOTE_AFTER_SUCCESSES:
                script.status = "active"
                if self.bus is not None:
                    self.bus.publish(
                        Event(
                            type=SCRIPT_PROMOTED,
                            source="script-runtime",
                            ts=tick,
                            payload={"script": script.name, "origin": script.origin},
                        )
                    )
            elif (
                script.failures >= RETIRE_AFTER_RUNS
                and script.utility < RETIRE_BELOW_UTILITY
            ):
                # a candidate that keeps failing never proved itself: reject
                self.retire(script.name, reason="candidate never proved itself")
        elif (
            script.status == "active"
            and script.runs >= RETIRE_AFTER_RUNS
            and script.utility < RETIRE_BELOW_UTILITY
        ):
            self.retire(script.name, reason="utility below threshold")

    # ---- queries (the "why do you still deserve energy?" ledger) ----

    def census(self) -> dict[str, int]:
        counts = {"candidate": 0, "active": 0, "retired": 0}
        for script in self.scripts.values():
            counts[script.status] = counts.get(script.status, 0) + 1
        return counts

    def retirement_candidates(self) -> list[Script]:
        return [
            s
            for s in self.scripts.values()
            if (
                s.status == "active"
                and s.runs >= RETIRE_AFTER_RUNS
                and s.utility < RETIRE_BELOW_UTILITY
            )
        ]
