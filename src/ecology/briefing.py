"""The morning briefing (Open Question #9: what is the user actually looking at?).

Not 500 notifications. The executive's view of a world that worked through
the night:

    things that changed
    recommended review
    urgent decisions
    the necessity census

The user is the executive, not the laborer — the interface should feel like
stewardship, not a chat prompt.
"""

from __future__ import annotations

from typing import Any

from .events import JUSTIFICATION_BROKEN, EventBus
from .identity import Identity
from .runtime import JustificationWatch
from .scripts import ScriptRuntime
from .tension import TensionField
from .world import WorldGraph


def morning_briefing(
    *,
    tick: int,
    world: WorldGraph,
    scripts: ScriptRuntime,
    tensions: TensionField,
    watch: JustificationWatch | None = None,
    identity: Identity | None = None,
    since_tick: int = 0,
    bus: EventBus | None = None,
) -> dict[str, Any]:
    """Assemble the briefing as data; :func:`format_briefing` renders it."""
    changed = sorted(
        (n.id, n.type)
        for n in world.nodes.values()
        if n.updated_tick >= since_tick and n.type == "memory"
    )

    urgent = [
        {
            "subject": t.subject,
            "expectation": t.expectation,
            "reality": t.reality,
            "magnitude": round(t.magnitude, 2),
            "age": tick - t.raised_tick,
        }
        for t in tensions.outstanding()[:3]
    ]

    recommendations: list[dict[str, Any]] = []
    for script in scripts.retirement_candidates():
        recommendations.append(
            {
                "action": "retire-script",
                "target": script.name,
                "reason": f"utility {script.utility:.2f} below threshold after {script.runs} runs",
            }
        )
    if watch is not None:
        for node_id, status in sorted(watch.evaluation.status.items()):
            if status.value == "dead":
                recommendations.append(
                    {
                        "action": "review-necessity",
                        "target": node_id,
                        "reason": "justification chain is dead — delete or re-justify",
                    }
                )

    briefing: dict[str, Any] = {
        "tick": tick,
        "things_changed": len(changed),
        "changed_samples": changed[:8],
        "urgent": urgent,
        "recommendations": recommendations[:6],
        "scripts": scripts.census(),
        "world_census": world.census(),
    }
    if watch is not None:
        briefing["necessity_census"] = watch.evaluation.summary()
        if bus is not None:
            briefing["why_broken_recently"] = [
                e.payload["node"] for e in bus.history(since_tick) if e.type == JUSTIFICATION_BROKEN
            ]
        else:
            briefing["why_broken_recently"] = []
    if identity is not None:
        briefing["identity"] = identity.snapshot()
    return briefing


def format_briefing(briefing: dict[str, Any]) -> str:
    """Render the briefing as the short text an executive reads first."""
    lines = [
        f"=== morning briefing (t={briefing['tick']}) ===",
        f"things that changed: {briefing['things_changed']}",
    ]
    if briefing.get("necessity_census"):
        census = briefing["necessity_census"]
        lines.append(
            "necessity: "
            + ", ".join(f"{k}={v}" for k, v in sorted(census.items()) if v)
        )
    lines.append(
        "scripts: "
        + ", ".join(f"{k}={v}" for k, v in briefing["scripts"].items() if v)
    )
    if briefing["urgent"]:
        lines.append("urgent decisions:")
        for tension in briefing["urgent"]:
            lines.append(
                f"  - {tension['subject']}: expected '{tension['expectation']}', "
                f"observed '{tension['reality']}' (age {tension['age']})"
            )
    if briefing["recommendations"]:
        lines.append("recommended review:")
        for rec in briefing["recommendations"]:
            lines.append(f"  - [{rec['action']}] {rec['target']}: {rec['reason']}")
    identity = briefing.get("identity")
    if identity:
        top = ", ".join(f"{name}={weight:.2f}" for name, weight in identity["top"])
        lines.append(f"identity: {top} (stability {identity['stability']})")
    return "\n".join(lines)
