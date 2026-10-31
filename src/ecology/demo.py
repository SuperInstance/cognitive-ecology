"""The tiny MUD — the smallest persistent world that improves itself.

Five processes, ~20 seeded scripts, one WHY graph, one sleep cycle. The
question this demo exists to answer (from the manifesto):

    What is the smallest persistent world that can improve itself
    while nobody is watching?

Run a week with :class:`WeekInABox` (``ecology week`` on the CLI). Nobody
prompts anything: the environment keeps emitting, the reflex layer keeps
handling, sleep keeps compiling repeated observations into routines, the WHY
graph keeps score of what still deserves energy — and at the end the world
is measurably more capable than the world that started, or the experiment
has taught you something even more valuable.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from . import why
from .attention import Bid
from .briefing import format_briefing, morning_briefing
from .events import Event, EventBus
from .runtime import JustificationWatch, Runtime, TickContext
from .scripts import Script, ScriptResult, ScriptRuntime
from .sleep import SleepCycle
from .tension import TensionField
from .world import WorldGraph

DAY_LEN = 30  # ticks per day
WEEK_DAYS = 7

WHY_GRAPH_TEXT = """
project:ecology -> goal:casey (explicit)
capability:telemetry -> project:ecology (explicit)
agent:reflex -> project:ecology (explicit)
agent:observer -> project:ecology (explicit)
agent:sleeper -> project:ecology (explicit)
agent:reporter -> project:ecology (explicit)
"""

WHY_LEGACY_TEXT = """
script:seed-good-11 -> goal:legacy-demo (explicit)
script:seed-good-12 -> goal:legacy-demo (explicit)
script:seed-mediocre-1 -> goal:legacy-demo (explicit)
script:seed-mediocre-2 -> goal:legacy-demo (explicit)
script:seed-mediocre-3 -> goal:legacy-demo (explicit)
script:seed-flaky-1 -> goal:legacy-demo (explicit)
script:seed-flaky-2 -> goal:legacy-demo (explicit)
"""

WHY_ATTESTATION_TEXT = """
goal:casey alive 2024-01-01 casey
goal:legacy-demo alive 2024-01-01 casey
"""


# ---------------------------------------------------------------- processes


class Environment:
    """The world outside: emits recurring telemetry and rare anomalies.

    Not a registered process — the environment is the world, not a citizen.
    Three recurring signatures (cpu every tick, disk every 2, net every 3)
    are what sleep should compile into routines; anomalies (~5% of ticks)
    raise tensions. Fully deterministic under a seed.
    """

    def __init__(self, bus: EventBus, rng: random.Random):
        self.bus = bus
        self.rng = rng
        self.tick_no = 0

    def emit(self) -> None:
        t = self.tick_no
        self._observe("cpu", round(self.rng.uniform(0.2, 0.9), 2))
        if t % 2 == 0:
            self._observe("disk", round(self.rng.uniform(0.1, 0.7), 2))
        if t % 3 == 0:
            self._observe("net", round(self.rng.uniform(0.0, 1.0), 2))
        if self.rng.random() < 0.05:
            self._observe("anomaly", self.rng.randint(1000, 9999))
        self.tick_no += 1

    def _observe(self, sensor: str, value) -> None:
        self.bus.publish(
            Event(
                type="observation.telemetry",
                source="environment",
                ts=self.tick_no,
                payload={"sensor": sensor, "value": value},
            )
        )


class Observer:
    """Records observations as world memory; anomalies raise tensions."""

    name = "observer"

    def __init__(self, world: WorldGraph, tensions: TensionField):
        self.world = world
        self.tensions = tensions

    def on_event(self, event: Event) -> None:
        if not event.type.startswith("observation."):
            return
        signature = f"{event.type}/{event.payload.get('sensor', 'general')}"
        node_id = f"memory:{signature}"
        node = self.world.node(node_id)
        if node is None:
            self.world.add_node(
                node_id, "memory", {"maturity": "observation", "count": 0}, tick=event.ts
            )
            node = self.world.node(node_id)
        node.attrs["count"] = node.attrs.get("count", 0) + 1
        node.updated_tick = event.ts
        if event.payload.get("sensor") == "anomaly":
            self.tensions.raise_tension(
                subject=node_id,
                expectation="known signatures only",
                reality=f"novel anomaly {event.payload.get('value')}",
                magnitude=0.6,
            )

    def tick(self, ctx: TickContext) -> None:  # cheap: memory is world state
        pass


class ReflexLayer:
    """Where scripts run. Most cognition happens here, with zero LLMs."""

    name = "reflex"

    def __init__(self, scripts: ScriptRuntime, event_budget: float = 2.0):
        self.scripts = scripts
        self.event_budget = event_budget
        self.handled = 0

    def on_event(self, event: Event) -> None:
        self.handled += len(self.scripts.handle_event(event, self.event_budget))

    def tick(self, ctx: TickContext) -> None:
        self.scripts.handle_tick(ctx.tick, ctx.budget)


class Sleeper:
    """Runs the sleep cycle at the end of each day; habituates old tensions."""

    name = "sleeper"

    def __init__(
        self,
        cycle: SleepCycle,
        *,
        day_len: int = DAY_LEN,
        habituate_after: int = 2 * DAY_LEN,
    ):
        self.cycle = cycle
        self.day_len = day_len
        self.habituate_after = habituate_after
        self.last_slept = 0
        self.reports: list = []

    def tick(self, ctx: TickContext) -> None:
        if ctx.tick > 0 and (ctx.tick + 1) % self.day_len == 0:
            report = self.cycle.run(self.last_slept, ctx.tick)
            self.reports.append(report)
            self.last_slept = ctx.tick + 1
            # habituation: tensions that outlived their novelty budget
            for tension in self.cycle.tensions.outstanding():
                if ctx.tick - tension.raised_tick > self.habituate_after:
                    self.cycle.tensions.resolve(tension.id)


class Reporter:
    """Prints the morning briefing at the start of each day."""

    name = "reporter"

    def __init__(self, demo: TinyMud, *, day_len: int = DAY_LEN, quiet: bool = False):
        self.demo = demo
        self.day_len = day_len
        self.quiet = quiet
        self.briefings: list[dict] = []

    def tick(self, ctx: TickContext) -> None:
        if ctx.tick > 0 and ctx.tick % self.day_len == 0:
            day = ctx.tick // self.day_len
            briefing = self.demo.briefing(since_tick=ctx.tick - self.day_len)
            self.briefings.append(briefing)
            if not self.quiet:
                print(f"\n--- day {day} ---")
                print(format_briefing(briefing))


# ---------------------------------------------------------------- the world


class TinyMud:
    """Assembles the smallest persistent world and runs it."""

    def __init__(self, *, seed: int = 42, day_len: int = DAY_LEN, quiet: bool = True):
        self.seed = seed
        self.day_len = day_len
        self.quiet = quiet

        self.bus = EventBus()
        self.world = WorldGraph()
        self.tensions = TensionField(self.bus)
        self.scripts = ScriptRuntime(self.bus)

        graph = why.parse_graph(WHY_GRAPH_TEXT + WHY_LEGACY_TEXT)
        attestation = why.parse_attestation(WHY_ATTESTATION_TEXT)
        self.watch = JustificationWatch(graph, attestation, self.bus)

        self._seed_scripts()

        self.runtime = Runtime(
            self.bus,
            self.world,
            tensions=self.tensions,
            watch=self.watch,
            budget_per_tick=12.0,
        )
        self._register_processes()

        self.environment = Environment(self.bus, random.Random(seed))
        self.sleep_cycle = self.sleeper.cycle

    # ---- construction ----

    def _seed_scripts(self) -> None:
        """~20 seeded scripts with different fates.

        12 good (thrive), 6 mediocre (retire by their own utility),
        2 flaky (fail and retire). The mediocre/flaky ones hang off
        goal:legacy-demo, which dies on day 4 — the WHY graph then
        reports them dead too: capability without justification is noise.
        """

        def good_fn(sensor: str):
            def fn(ctx: dict) -> ScriptResult:
                return ScriptResult(success=True, note=f"{sensor} ok", utility=0.8)

            return fn

        def mediocre_fn(sensor: str):
            def fn(ctx: dict) -> ScriptResult:
                return ScriptResult(success=True, note=f"{sensor} meh", utility=0.04)

            return fn

        def flaky_fn(ctx: dict) -> ScriptResult:
            return ScriptResult(success=False, note="flaky failure")

        for i in range(1, 11):  # 10 good on telemetry
            self.scripts.register(
                Script(
                    name=f"script:seed-good-{i}",
                    trigger="observation.telemetry",
                    fn=good_fn("telemetry"),
                    owner="seed",
                    cost=0.05,
                )
            )
        for i in (11, 12):  # 2 good on tick
            self.scripts.register(
                Script(
                    name=f"script:seed-good-{i}",
                    trigger="tick",
                    fn=good_fn("tick"),
                    owner="seed",
                    cost=0.05,
                )
            )
        for i in (1, 2, 3):  # 3 mediocre on telemetry
            self.scripts.register(
                Script(
                    name=f"script:seed-mediocre-{i}",
                    trigger="observation.telemetry",
                    fn=mediocre_fn("telemetry"),
                    owner="seed",
                    cost=0.05,
                )
            )
        for i in (1, 2):  # 2 flaky on telemetry
            self.scripts.register(
                Script(
                    name=f"script:seed-flaky-{i}",
                    trigger="observation.telemetry",
                    fn=flaky_fn,
                    owner="seed",
                    cost=0.05,
                )
            )

    def _register_processes(self) -> None:
        self.observer = Observer(self.world, self.tensions)
        self.reflex = ReflexLayer(self.scripts)
        self.sleeper = Sleeper(
            SleepCycle(
                self.bus, self.world, self.scripts, self.watch, self.tensions, min_pattern_freq=3
            ),
            day_len=self.day_len,
        )
        self.reporter = Reporter(self, day_len=self.day_len, quiet=self.quiet)
        # the bus wires subscribers; the runtime wires tick energy
        self.bus.subscribe("*", self.observer.on_event)
        self.bus.subscribe("*", self.reflex.on_event)
        self.runtime.register(
            self.reflex, why_node="agent:reflex", bid_fn=lambda t: _bid("reflex", 6.0)
        )
        self.runtime.register(
            self.observer, why_node="agent:observer", bid_fn=lambda t: _bid("observer", 2.0)
        )
        self.runtime.register(
            self.sleeper, why_node="agent:sleeper", bid_fn=lambda t: _bid("sleeper", 2.0)
        )
        self.runtime.register(
            self.reporter, why_node="agent:reporter", bid_fn=lambda t: _bid("reporter", 1.0)
        )

    # ---- running ----

    def step(self) -> None:
        self.environment.emit()
        self.runtime.tick()

    def briefing(self, since_tick: int = 0) -> dict:
        return morning_briefing(
            tick=self.runtime.tick_count,
            world=self.world,
            scripts=self.scripts,
            tensions=self.tensions,
            watch=self.watch,
            since_tick=since_tick,
            bus=self.bus,
        )


def _bid(name: str, requested: float) -> Bid:
    return Bid.keepalive(name, requested)


# ---------------------------------------------------------------- the week


@dataclass
class DayReport:
    day: int
    tick: int
    scripts: dict
    necessity: dict
    sleep_summary: list[str] = field(default_factory=list)


@dataclass
class WeekReport:
    days: list[DayReport] = field(default_factory=list)
    sleep_born_scripts: list[str] = field(default_factory=list)
    promoted: list[str] = field(default_factory=list)
    retired: list[str] = field(default_factory=list)
    observations_handled_by_sleep_born: int = 0
    total_utility: float = 0.0
    tension_events: int = 0
    why_broken: list[str] = field(default_factory=list)

    def leverage_lines(self) -> list[str]:
        promoted_note = ""
        if self.promoted:
            head = ", ".join(self.promoted[:6])
            tail = "..." if len(self.promoted) > 6 else ""
            promoted_note = f" ({head}{tail})"
        return [
            "=== the week in a box: what happened while nobody was watching ===",
            f"observations compiled into routines by sleep: "
            f"{len(self.sleep_born_scripts)} scripts born, "
            f"{self.observations_handled_by_sleep_born} observations handled by them",
            f"scripts promoted to active: {len(self.promoted)}{promoted_note}",
            f"scripts retired by their own utility: {len(self.retired)}",
            f"tensions raised (novelty encountered): {self.tension_events}",
            f"justifications broken: {len(self.why_broken)}",
            f"total learned utility in the script ecology: {self.total_utility:.2f}",
        ]


class WeekInABox:
    """Runs the tiny MUD for a week and reports capability accumulation."""

    def __init__(
        self,
        *,
        seed: int = 42,
        days: int = WEEK_DAYS,
        day_len: int = DAY_LEN,
        quiet: bool = False,
    ):
        self.seed = seed
        self.days = days
        self.day_len = day_len
        self.quiet = quiet

    def run(self) -> WeekReport:
        mud = TinyMud(seed=self.seed, day_len=self.day_len, quiet=self.quiet)
        report = WeekReport()

        for tick in range(self.days * self.day_len):
            day = tick // self.day_len
            # day 4: the legacy demo goal dies — its dependents must show as dead
            if tick == 4 * self.day_len and "goal:legacy-demo" in mud.watch.attestation.roots:
                mud.watch.set_attestation(
                    why.RootAttestation(id="goal:legacy-demo", status=why.Liveness.DEAD, by="owner")
                )
            mud.step()

            if (tick + 1) % self.day_len == 0:
                day_report = DayReport(
                    day=day + 1,
                    tick=tick + 1,
                    scripts=mud.scripts.census(),
                    necessity=mud.watch.evaluation.summary(),
                )
                if mud.sleeper.reports:
                    day_report.sleep_summary = mud.sleeper.reports[-1].summary()
                report.days.append(day_report)

        # final accounting
        all_scripts = mud.scripts.scripts.values()
        report.sleep_born_scripts = sorted(
            s.name for s in all_scripts if s.origin == "sleep-promoted" and s.status != "retired"
        )
        report.promoted = sorted(
            s.name for s in all_scripts if s.origin == "sleep-promoted" and s.status == "active"
        )
        report.retired = sorted(s.name for s in all_scripts if s.status == "retired")
        report.total_utility = sum(s.utility for s in all_scripts)
        report.tension_events = mud.bus.counters.get("tension.raised", 0)
        report.why_broken = sorted(
            {
                e.payload["node"]
                for e in mud.bus.history()
                if e.type == "justification.broken"
            }
        )
        for signature_script in report.sleep_born_scripts:
            node = mud.world.node(f"memory:{signature_script.removeprefix('routine:')}")
            if node is not None:
                report.observations_handled_by_sleep_born += node.attrs.get("handled", 0)
        return report
