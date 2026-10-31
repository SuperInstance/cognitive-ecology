"""L7 — Sleep.

Not idle mode, and not "summarize the day". Sleep is infrastructure
evolution: the pipeline that converts experience into reusable machinery.

    observations -> episodes -> patterns -> candidate scripts
        -> replay validation -> promotion -> capability accumulation

The most important activity is *convert experiences into scripts*, because
that is where capability accumulates (Open Question #6: experts don't
remember — experts compile). This v1 pipeline is entirely mechanical — no
LLM anywhere — which is exactly the point: it tests how far adaptation gets
before any model is involved (Open Question #8).
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field

from .events import OBSERVATION_RECORDED, ROUTINE_CANDIDATE, SLEEP_CYCLE_COMPLETED, Event, EventBus
from .runtime import JustificationWatch
from .scripts import Script, ScriptResult, ScriptRuntime
from .tension import TensionField
from .world import WorldGraph


@dataclass
class SleepReport:
    since_tick: int = 0
    observations: int = 0
    episodes: dict[str, int] = field(default_factory=dict)  # signature -> count
    patterns: list[str] = field(default_factory=list)  # signatures above frequency
    candidates: list[str] = field(default_factory=list)  # candidate script names
    validated: list[str] = field(default_factory=list)  # candidates that survived replay
    promoted_nodes: list[str] = field(default_factory=list)  # world nodes graduated
    retired_scripts: list[str] = field(default_factory=list)
    why_broken: list[str] = field(default_factory=list)
    tensions_outstanding: int = 0

    def summary(self) -> list[str]:
        lines = [
            f"sleep[{self.since_tick}+]: {self.observations} observations, "
            f"{len(self.episodes)} episode signatures, {len(self.patterns)} patterns",
            f"  candidate scripts: {len(self.candidates)} proposed, "
            f"{len(self.validated)} validated by replay",
            f"  memory graduated: {len(self.promoted_nodes)} nodes; "
            f"scripts retired: {len(self.retired_scripts)}",
        ]
        if self.why_broken:
            lines.append(f"  why: {len(self.why_broken)} justifications broken")
        lines.append(f"  tensions outstanding: {self.tensions_outstanding}")
        return lines


class SleepCycle:
    """One night: consolidate the observation stream into machinery."""

    def __init__(
        self,
        bus: EventBus,
        world: WorldGraph,
        scripts: ScriptRuntime,
        watch: JustificationWatch | None = None,
        tensions: TensionField | None = None,
        *,
        min_pattern_freq: int = 3,
        min_replay_gain: float = 1.0,
    ):
        self.bus = bus
        self.world = world
        self.scripts = scripts
        self.watch = watch
        self.tensions = tensions
        self.min_pattern_freq = min_pattern_freq
        self.min_replay_gain = min_replay_gain

    # ---- the pipeline ----

    def run(self, since_tick: int, now_tick: int) -> SleepReport:
        report = SleepReport(since_tick=since_tick)

        # 1-2. observations -> episodes (grouped by signature)
        history = self.bus.history(since_tick)
        report.observations = len(history)
        episodes: dict[str, list[Event]] = defaultdict(list)
        for event in history:
            if not event.type.startswith("observation."):
                continue
            signature = self._signature(event)
            episodes[signature].append(event)
        report.episodes = {sig: len(events) for sig, events in episodes.items()}

        # 3. patterns: signatures with enough repetition to be worth compiling
        report.patterns = sorted(
            sig for sig, count in report.episodes.items() if count >= self.min_pattern_freq
        )

        # 4. memory graduates in the world graph: observation -> episode -> pattern
        for signature, count in report.episodes.items():
            node_id = f"memory:{signature}"
            node = self.world.node(node_id)
            if node is None:
                node = self.world.add_node(
                    node_id, "memory", {"maturity": "observation", "count": 0}, tick=since_tick
                )
            node.attrs["count"] = node.attrs.get("count", 0) + count
            if count >= 2:
                self.world.graduate(node_id, "episode")
            if count >= self.min_pattern_freq and self.world.graduate(node_id, "pattern"):
                report.promoted_nodes.append(node_id)

        # 5-6. candidate scripts, validated by replaying the window
        for signature in report.patterns:
            events = episodes[signature]
            handled = len(events)  # the candidate would have run on each
            gain = handled * 1.0  # utility proxy: one handled observation per run
            name = f"routine:{signature}"
            report.candidates.append(name)
            if gain < self.min_replay_gain:
                continue  # frequent enough to notice, not useful enough to keep
            if name in self.scripts.scripts:
                continue  # already compiled — sleep does not duplicate machinery
            trigger = events[0].type
            script = Script(
                name=name,
                trigger=trigger,
                fn=self._make_handler(signature, trigger),
                conditions=self._make_condition(signature),
                owner="sleep",
                cost=0.05,
                utility=min(1.0, 0.2 + 0.02 * handled),  # seeded from replay, then learned
                born_tick=now_tick,
                origin="sleep-promoted",
            )
            self.scripts.register(script)
            report.validated.append(name)
            self.world.graduate(f"memory:{signature}", "routine")
            self.bus.publish(
                Event(
                    type=ROUTINE_CANDIDATE,
                    source="sleep",
                    ts=now_tick,
                    payload={"script": name, "replay_gain": gain},
                )
            )

        # 7. WHY recheck — justification breakage surfaces at night
        if self.watch is not None:
            report.why_broken = self.watch.recheck(now_tick)

        # 8. prune: retire scripts that no longer justify their cost
        for script in self.scripts.retirement_candidates():
            self.scripts.retire(script.name, reason="sleep prune: utility below threshold")
            report.retired_scripts.append(script.name)

        # 9. tensions carry over to the morning briefing
        if self.tensions is not None:
            self.tensions.advance(now_tick)
            report.tensions_outstanding = len(self.tensions.outstanding())

        self.bus.publish(
            Event(
                type=SLEEP_CYCLE_COMPLETED,
                source="sleep",
                ts=now_tick,
                payload={"patterns": len(report.patterns), "validated": len(report.validated)},
            )
        )
        return report

    # ---- helpers ----

    @staticmethod
    def _signature(event: Event) -> str:
        sensor = event.payload.get("sensor") or event.payload.get("subject") or "general"
        return f"{event.type}/{sensor}"

    @staticmethod
    def _make_condition(signature: str):
        """A compiled routine only responds to its own signature: the cpu
        routine must not fire on disk events."""

        def condition(ctx: dict) -> bool:
            sensor = ctx.get("payload", {}).get("sensor") or "general"
            return f"{ctx.get('event')}/{sensor}" == signature

        return condition

    def _make_handler(self, signature: str, trigger: str) -> callable:
        """The compiled behavior: acknowledge a known signature cheaply.

        In a richer ecology this is where a teacher (LLM) could propose a
        *better* handler; here the mechanical one must stand on its own.
        """

        def handler(ctx: dict) -> ScriptResult:
            node = self.world.node(f"memory:{signature}")
            if node is not None:
                node.attrs["handled"] = node.attrs.get("handled", 0) + 1
                node.updated_tick = ctx.get("tick", node.updated_tick)
            return ScriptResult(success=True, note=f"handled {signature}", utility=0.3)

        return handler


# re-exported for the observer pattern
OBSERVATION = OBSERVATION_RECORDED


def count_signatures(events: list[Event]) -> Counter:
    """Utility: signature counts over an event window."""
    return Counter(SleepCycle._signature(e) for e in events if e.type.startswith("observation."))
