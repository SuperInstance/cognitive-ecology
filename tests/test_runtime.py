"""Runtime tests: WHY as the scheduler, starvation-not-death, breakage events."""

from __future__ import annotations

import pytest

from conftest import _full_bid
from ecology import why
from ecology.events import JUSTIFICATION_BROKEN, EventBus
from ecology.runtime import JustificationWatch, Runtime, TickContext
from ecology.world import WorldGraph


class Ticker:
    """A boring process: counts its ticks, records the budget it got."""

    def __init__(self, name: str, requested: float = 1.0):
        self.name = name
        self.requested = requested
        self.ticks = 0
        self.budgets: list[float] = []

    def tick(self, ctx: TickContext) -> None:
        self.ticks += 1
        self.budgets.append(ctx.budget)


def _world_with_why():
    """goal:casey (root, alive) <- project:ecology <- agent:researcher."""
    bus = EventBus()
    world = WorldGraph()
    graph = why.parse_graph(
        "project:ecology -> goal:casey (explicit)\n"
        "agent:researcher -> project:ecology (explicit)\n"
        "agent:legacy -> project:old (explicit)"
    )
    att = why.parse_attestation(
        "goal:casey alive 2024-01-01 casey\nproject:old dead 2023-04-12 ci"
    )
    watch = JustificationWatch(graph, att, bus)
    return bus, world, watch


def test_dead_justification_starves_the_process() -> None:
    bus, world, watch = _world_with_why()
    rt = Runtime(bus, world, watch=watch, budget_per_tick=10.0)
    funded = Ticker("researcher", requested=5.0)
    legacy = Ticker("legacy", requested=5.0)
    rt.register(funded, why_node="agent:researcher")
    rt.register(legacy, why_node="agent:legacy")
    reports = rt.run(3)
    # the justified process ran every tick; the dead-justified one starved
    assert funded.ticks == 3
    assert legacy.ticks == 0
    assert all("legacy" in r.starved for r in reports)


def test_breaking_a_root_emits_justification_broken() -> None:
    bus, world, watch = _world_with_why()
    rt = Runtime(bus, world, watch=watch)
    researcher = Ticker("researcher", requested=5.0)
    rt.register(researcher, why_node="agent:researcher")
    rt.run(1)
    assert researcher.ticks == 1

    broken_events = []
    bus.subscribe(JUSTIFICATION_BROKEN, broken_events.append)
    # The root's attestation is REMOVED (its liveness is no longer known).
    # Dependents become questionable — unknown, not deleted — the ecology's
    # "questionable, not dead" semantics riding on the kernel's dangling rule.
    watch.attestation.roots.pop("goal:casey")
    watch._dirty = True
    rt.run(1)

    payloads = [e.payload["node"] for e in broken_events]
    assert "project:ecology" in payloads
    assert "agent:researcher" in payloads
    # Questionable, not deleted: the process keeps running — the discount
    # bites under contention (see test_unknown_bids_at_a_discount), not when
    # budget is abundant.
    assert researcher.ticks == 2


def test_unknown_bids_at_a_discount() -> None:
    """Under contention, a questionable process gets 1/4 the energy of an
    alive one (justification weight 0.25 vs 1.0 in the manifesto product)."""
    bus, world, watch = _world_with_why()
    rt = Runtime(bus, world, watch=watch, budget_per_tick=1.0)
    alive = Ticker("alive", requested=1.0)
    questionable = Ticker("questionable", requested=1.0)
    rt.register(alive, why_node="agent:researcher")
    rt.register(questionable, why_node="agent:legacy")
    # make agent:legacy dangling (unknown) rather than dead
    watch.attestation.roots.pop("project:old")
    watch._dirty = True
    rt.tick()
    assert alive.ticks == 1 and questionable.ticks == 1  # both run...
    ratio = alive.budgets[0] / questionable.budgets[0]
    assert ratio == pytest.approx(4.0)  # ...but 1.0 vs 0.25 justification weight


def test_attesting_a_root_dead_kills_explicit_dependents() -> None:
    """Attested-dead is a stronger statement than 'liveness unknown'.

    Explicit chains under a dead root are dead at any depth (the kernel's
    certainty rule, audit Finding 2) — weight 0.0, the conservation law
    fully withdrawn. Questionable-not-dead applies when the root's status
    is *unknown* (removed, stale, or inferred), not when it is attested dead.
    """
    bus, world, watch = _world_with_why()
    rt = Runtime(bus, world, watch=watch)
    researcher = Ticker("researcher", requested=5.0)
    rt.register(researcher, why_node="agent:researcher")
    rt.run(1)
    assert researcher.ticks == 1
    watch.set_attestation(why.RootAttestation(id="goal:casey", status=why.Liveness.DEAD))
    rt.run(1)
    assert watch.weight_of("agent:researcher") == 0.0
    assert researcher.ticks == 1  # starved from the second tick on


def test_bids_flow_through_the_policy() -> None:
    bus, world, watch = _world_with_why()
    rt = Runtime(bus, world, watch=watch, budget_per_tick=8.0)
    a = Ticker("a", requested=1.0)
    b = Ticker("b", requested=3.0)
    rt.register(
        a,
        why_node="agent:researcher",
        bid_fn=lambda t: _full_bid("a", 1.0),
    )
    rt.register(
        b,
        why_node="agent:researcher",
        bid_fn=lambda t: _full_bid("b", 3.0),
    )
    report = rt.tick()
    # equal scores, ample budget: each gets its request (caps respected)
    assert set(report.ran) == {"a", "b"}
    assert a.budgets[0] == 1.0
    assert b.budgets[0] == 3.0


def test_watch_weights_follow_status() -> None:
    bus, world, watch = _world_with_why()
    assert watch.weight_of("agent:researcher") == 1.0
    assert watch.weight_of("agent:legacy") == 0.0
    # liveness withdrawn (dangling root) -> questionable
    watch.attestation.roots.pop("goal:casey")
    watch._dirty = True
    assert watch.weight_of("agent:researcher") == 0.25  # unknown: questionable
