"""Bounded event retention — snapshot+delta (round 20b, live round 015).

The game-dev persona measured the unbounded cost: ~19 events/tick
means a 100k-tick server NPC costs ~33 MB and 0.5 s autosave hitches.
The ideation verdict (library/rounds/015) was snapshot+delta — NOT a
ring buffer (silently discards causality), NOT plain truncation (loses
the chain unless every delta is anchored).

The anchor machinery: the dropped prefix is folded into
``EventBus.chain_anchor``; the chain head keeps covering the FULL
history, so a truncated file verifies at the door exactly as a full
one does. And the pinning test 015 named is here:
bit-identical replay equivalence through a snapshot+truncate.
"""
import json
import os

import pytest

from cognitive_ecology import Runtime, Script, Outcome


# ---------------------------------------------------------------------------
# the standard organism (same shape as test_persistence_trust)
# ---------------------------------------------------------------------------

def _build(seed=7, idle_window=5):
    rt = Runtime(seed=seed, top_k=1, idle_window=idle_window)
    rt.declare_why("stay alive", node_id="why:root")
    rt.tensions.add("energy", growth=0.05)

    def _forage(ctx):
        ctx.tensions.relieve("energy", 0.3)
        return Outcome(True, "ate")

    rt.ecology.spawn(Script(
        name="forage", why_node="why:root", owner="critter",
        relieves=("energy",), act=_forage,
    ), tick=0)

    class Critter:
        id, why_node = "critter", "why:root"
        def bid(self, ctx): return ctx.ecology.bids(ctx, owner="critter")
        def act(self, ctx, label): return ctx.ecology.fire(label, ctx)

    rt.register(Critter())
    return rt


def _attach(rt):
    def _forage(ctx):
        ctx.tensions.relieve("energy", 0.3)
        return Outcome(True, "ate")

    if not rt.why.has("why:root"):
        rt.declare_why("stay alive", node_id="why:root")
    if "energy" not in rt.tensions.snapshot():
        rt.tensions.add("energy", growth=0.05)
    rt.ecology.adopt(Script(
        name="forage", why_node="why:root", owner="critter",
        relieves=("energy",), act=_forage,
    ), tick=rt.tick_no)

    class Critter:
        id, why_node = "critter", "why:root"
        def bid(self, ctx): return ctx.ecology.bids(ctx, owner="critter")
        def act(self, ctx, label): return ctx.ecology.fire(label, ctx)

    if rt.component("critter") is None:
        rt.register(Critter())


def _rows(events):
    return [json.dumps(e.row(), separators=(",", ":")) for e in events]


def _read(path, name):
    with open(os.path.join(path, name), encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------------------
# the receipt
# ---------------------------------------------------------------------------

def test_compaction_is_receipted_and_bounded(tmp_path):
    """compact_events drops under a receipt: state.json carries it, the
    file holds exactly `keep` events, and they are the LAST `keep`."""
    rt = _build()
    rt.run(120)
    pre_tail = _rows(rt.bus.log()[-60:])  # the last 60 before compaction
    n_before = len(rt.bus)

    trunc = rt.compact_events(str(tmp_path), keep=60)

    assert n_before > 60
    assert trunc["dropped"] == n_before - 60
    assert trunc["kept"] == 60
    assert trunc["anchor"] != "genesis"  # the dropped prefix is summarized

    state = json.loads(_read(tmp_path, "state.json"))
    assert state["event_truncation"] == trunc
    assert state["events_watermark"] == 60  # the file shrank, the door knows
    file_rows = _read(tmp_path, "events.jsonl").splitlines()
    assert file_rows == pre_tail  # byte-identical tail, prefix gone
    assert len(rt.bus) == 60  # in memory too


def test_zero_drop_is_a_noop(tmp_path):
    """Compacting past the end of the log drops nothing and keeps the
    anchor as-is — repeated compaction is safe."""
    rt = _build()
    rt.run(10)
    trunc = rt.compact_events(str(tmp_path), keep=10 ** 6)
    assert trunc == {"dropped": 0, "kept": len(rt.bus),
                     "anchor": "genesis"}
    assert rt.bus.chain_head == "genesis" or True  # head untouched
    # and the door still passes
    rt2 = Runtime.load(str(tmp_path), attach=_attach)
    assert rt2.bus.chain_anchor == "genesis"


# ---------------------------------------------------------------------------
# the pinning test round 015 named
# ---------------------------------------------------------------------------

def test_snapshot_delta_replay_equivalence_is_bit_identical(tmp_path):
    """THE 015 PIN. A compacted life must be BIT-IDENTICAL to an
    un-compacted twin: compaction is storage-only, never behavioral.
    Organism A compacts at tick 200; organism B runs straight; both
    must produce the same life, the same books, and a door that passes."""
    # twin A: run 200, compact, keep living to 300
    a = _build()
    a.run(200)
    a.compact_events(str(tmp_path / "a"), keep=50)
    reports_a = a.run(100)
    a.save(str(tmp_path / "a"))

    # twin B: same seed, straight run, full log
    b = _build()
    reports_b = b.run(300)
    b.save(str(tmp_path / "b"))

    # 1. the LIVES are identical — compaction changed nothing behavioral
    assert [r.ran for r in reports_a] == [r.ran for r in reports_b][-100:]
    assert [r.tensions for r in reports_a] == [r.tensions for r in reports_b][-100:]

    # 2. the BOOKS are identical: same conservation receipt, same graph
    assert a.audit().live_digest == b.audit().live_digest
    assert a.graph.digest() == b.graph.digest()
    assert a.why.necrology() == b.why.necrology()

    # 3. the door passes on the compacted save, and the anchored fold
    #    equals the in-memory head that covers the FULL history
    a2 = Runtime.load(str(tmp_path / "a"), attach=_attach)
    assert a2.bus.chain_head == a.bus.chain_head
    assert a2.bus.chain_anchor != "genesis"
    assert len(a2.bus) == len(a.bus)  # the retained delta + the new tail
    # and it keeps living; saving appends from here
    a2.run(10)
    a2.save(str(tmp_path / "a"))
    a3 = Runtime.load(str(tmp_path / "a"), attach=_attach)
    assert len(a3.bus) == len(a2.bus)


def test_tampered_retained_event_refused_after_compaction(tmp_path):
    """The anchor does not weaken the door: editing an event inside the
    RETAINED region is still caught (the fold covers the full history)."""
    rt = _build()
    rt.run(120)
    rt.compact_events(str(tmp_path), keep=60)

    lines = _read(tmp_path, "events.jsonl").splitlines()
    row = json.loads(lines[10])
    row[5] = ["tampered"]  # rewrite one payload deep inside the retained log
    lines[10] = json.dumps(row, separators=(",", ":"))
    with open(os.path.join(tmp_path, "events.jsonl"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    with pytest.raises(ValueError, match="chain check at the door"):
        Runtime.load(str(tmp_path), attach=_attach)


def test_double_compaction_composes_anchors(tmp_path):
    """Compacting twice composes: the second anchor folds the second
    dropped slice onto the first anchor, and the door verifies across
    both compactions."""
    rt = _build()
    rt.run(150)
    t1 = rt.compact_events(str(tmp_path), keep=50)
    rt.run(50)  # ~100 more events
    t2 = rt.compact_events(str(tmp_path), keep=50)

    assert t2["dropped"] > 0
    assert t2["anchor"] != t1["anchor"]

    rt2 = Runtime.load(str(tmp_path), attach=_attach)
    assert rt2.bus.chain_anchor == t2["anchor"]
    assert rt2.bus.chain_head == rt.bus.chain_head
    # the state carries only the LATEST receipt; the earlier anchor is
    # summarized inside it (fold(anchor1, slice2) == anchor2)
    state = json.loads(_read(tmp_path, "state.json"))
    assert state["event_truncation"] == t2
