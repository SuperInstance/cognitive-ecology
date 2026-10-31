"""L4 — script ecology: fire, learn, starve, die, mutate, remember."""
import random
from types import SimpleNamespace

from cognitive_ecology import (
    EventBus, EventKind, Outcome, Script, ScriptEcology,
)


class _Ctx(SimpleNamespace):
    """A fake snapshot — ecology only needs why/tensions/novelty/tick."""

    def __init__(self, tick=1, just=None, level=0.5, novelty=0.5):
        justmap = just if just is not None else {"why:root": 1.0}
        why = SimpleNamespace(justification=lambda nid: justmap.get(nid, 0.0))
        tensions = SimpleNamespace(level=lambda name: level)
        super().__init__(tick=tick, why=why, tensions=tensions,
                         novelty=lambda focus: novelty)


def _ecology():
    bus = EventBus()
    return ScriptEcology(bus=bus, rng=random.Random(3))


def test_fire_updates_ema_and_counts():
    eco = _ecology()
    s = eco.spawn(Script(
        name="forage", why_node="why:root", owner="critter",
        act=lambda ctx: Outcome(True, "yum"),
    ), tick=0)
    for t in range(1, 9):  # eight successes pull the EMA (alpha=0.3) high
        out = s.fire(_Ctx(tick=t))
        assert out.ok
    assert s.fires == 8
    assert s.success_rate > 0.9


def test_crashing_script_does_not_kill_the_organism():
    eco = _ecology()
    s = eco.spawn(Script(
        name="boom", why_node="why:root",
        act=lambda ctx: 1 / 0,
    ), tick=0)
    out = s.fire(_Ctx(tick=1))
    assert not out.ok and "ZeroDivisionError" in out.note
    assert s.success_rate < 0.5


def test_bids_respect_why_and_opportunity_gates():
    eco = _ecology()
    eco.spawn(Script(name="ok", why_node="why:root", owner="critter",
                     relieves=("energy",)), tick=0)
    eco.spawn(Script(name="dead-why", why_node="why:dead", owner="critter"), tick=0)
    eco.spawn(Script(name="not-now", why_node="why:root", owner="critter",
                     when=lambda ctx: False), tick=0)
    ctx = _Ctx(just={"why:root": 1.0, "why:dead": 0.0}, level=0.8, novelty=0.6)
    bids = eco.bids(ctx, owner="critter")
    labels = [b.label for b in bids]
    assert "ok" in labels
    assert "dead-why" not in labels   # WHY gate: dead purpose -> no bid
    assert "not-now" not in labels    # opportunity gate: trigger false -> no bid
    b = bids[0]
    assert b.urgency == 0.8 and b.expected_value == 0.5
    # with the whole WHY chain broken, nothing bids at all
    assert eco.bids(_Ctx(just={}), owner="critter") == []


def test_starving_never_fired_script_dies_into_necrology():
    eco = _ecology()
    eco.spawn(Script(name="loser", why_node="why:root"), tick=0)
    eco.spawn(Script(name="winner", why_node="why:root"), tick=0)
    deaths_total = []
    for t in range(1, 46):
        # every tick: winner fired, loser bid-but-starved
        deaths_total += eco.bookkeeping(
            t, fired_labels=["winner"], starved_labels=["loser"]
        )
    assert any(d.name == "loser" for d in deaths_total)
    assert eco.get("loser") is None             # gone from the living...
    assert eco.necrology()[-1].name == "loser"  # ...but recorded forever
    assert eco.population() == 1
    # a DEATH event was emitted
    death_events = [e for e in eco.bus.log() if e.kind is EventKind.DEATH]
    assert death_events and death_events[0].payload[0] == "loser"


def test_mutate_jitters_params_and_lineage():
    eco = ScriptEcology(bus=EventBus(), rng=random.Random(5))
    parent = eco.spawn(Script(
        name="forage", why_node="why:root", params={"radius": 3, "care": 0.7},
        act=lambda ctx: Outcome(True),
    ), tick=0)
    child = eco.mutate(parent, tick=10)
    assert child.name == "forage~1"
    assert child.parent == parent.id and child.generation == 1
    assert child.params["radius"] != 3 or child.params["care"] != 0.7
    assert child.success_rate == 0.5  # newborns start even
    # dreaming the same parent twice must not collide on names
    second = eco.mutate(parent, tick=11)
    third = eco.mutate(parent, tick=12)
    assert len({child.name, second.name, third.name}) == 3


def test_save_and_adopt_round_trip():
    eco = _ecology()
    s = eco.spawn(Script(name="forage", why_node="why:root", owner="critter",
                         params={"radius": 2}), tick=0)
    s.fires = 12
    s.success_rate = 0.83
    data = eco.to_json()
    # "load" into a fresh ecology: live scripts become saved stats
    eco2 = ScriptEcology.from_json(data, bus=EventBus())
    assert eco2.population() == 0            # closures are code, not data
    assert eco2.necrology() == eco.necrology()
    # the app re-declares the script in code and adopts its record
    rebuilt = Script(name="forage", why_node="why:root", owner="critter",
                     params={"radius": 2},
                     act=lambda ctx: Outcome(True))
    adopted = eco2.adopt(rebuilt, tick=99)
    assert adopted.fires == 12 and adopted.success_rate == 0.83
    assert adopted.last_fire == s.last_fire
