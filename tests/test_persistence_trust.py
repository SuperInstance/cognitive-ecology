"""Persistence trustworthiness — trust at the door (round 20a).

The wave-1 backend persona (Priya) probed the persistence path as a
production integrator and found it untrustworthy end-to-end:

* save was non-atomic (a torn write destroyed the only checkpoint);
* load() never verified ANYTHING — a tampered state.json (a flipped
  WHY state inside valid JSON) booted silently, a tampered
  events.jsonl was never checked at all;
* events.jsonl was rewritten whole on every save (linear cost, autosave
  hitches — the game-dev persona measured 94 ms at only 19k events);
* failure reasons were dropped (fixed in round 17);
* sleeper stats were never persisted; a tick-0-born script came back
  re-stamped at the load tick (the game-dev persona's save-compat bug).

These tests pin the door: atomic writes, append-mode events with a
chain head and watermark, recomputed conservation receipts, sleeper
stats, and born=0 surviving load.
"""
import json
import os

import pytest

from cognitive_ecology import Runtime, Script, Outcome


# ---------------------------------------------------------------------------
# a small standard organism used by every test below
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
    ), tick=0)  # born=0 on purpose: the bug this round fixes

    class Critter:
        id, why_node = "critter", "why:root"
        def bid(self, ctx): return ctx.ecology.bids(ctx, owner="critter")
        def act(self, ctx, label): return ctx.ecology.fire(label, ctx)

    rt.register(Critter())
    return rt


def _attach(rt):
    """Re-declare behavior in code, adopt saved track records.

    Guards everything (the attach() rite of passage, finding 6: re-declaring
    existing state raises on a loaded organism — until the ensure_* API
    lands, this is the documented workaround)."""

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


def _read(path, name):
    with open(os.path.join(path, name), encoding="utf-8") as f:
        return f.read()


def _write(path, name, text):
    with open(os.path.join(path, name), "w", encoding="utf-8") as f:
        f.write(text)


# ---------------------------------------------------------------------------
# atomic state writes
# ---------------------------------------------------------------------------

def test_state_write_is_atomic(tmp_path):
    """A crash mid-write leaves the previous checkpoint untouched and no
    torn temp file behind (the torn-write scenario that used to destroy
    the only checkpoint)."""
    rt = _build()
    rt.run(10)
    rt.save(str(tmp_path))
    good = _read(tmp_path, "state.json")

    # second save explodes while writing the temp file
    rt.run(5)
    real_dump = json.dump

    def exploding_dump(obj, fp, **kw):
        fp.write('{"torn')  # simulate a partial write...
        raise OSError("disk exploded")  # ...then the crash

    json.dump = exploding_dump
    try:
        with pytest.raises(OSError):
            rt.save(str(tmp_path))
    finally:
        json.dump = real_dump

    # the previous checkpoint is intact, byte-for-byte; no tmp residue
    assert _read(tmp_path, "state.json") == good
    assert not os.path.exists(os.path.join(str(tmp_path), "state.json.tmp"))


# ---------------------------------------------------------------------------
# the door checks
# ---------------------------------------------------------------------------

def test_tampered_state_is_refused_at_the_door(tmp_path):
    """The wave-1 probe that used to boot silently: flip a WHY node's
    state inside VALID JSON. The door recomputes the conservation
    receipt and refuses to build the organism."""
    rt = _build()
    rt.run(10)
    rt.save(str(tmp_path))

    state = json.loads(_read(tmp_path, "state.json"))
    # flip a live node to dead inside the tree (valid JSON, lying books)
    for node in state["why"]["nodes"]:
        if node.get("state") == "alive":
            node["state"] = "dead"
            break
    _write(tmp_path, "state.json", json.dumps(state))

    with pytest.raises(ValueError, match="conservation check at the door"):
        Runtime.load(str(tmp_path), attach=_attach)


def test_corrupt_state_raises_a_clear_error(tmp_path):
    """A truncated state.json raises with context, not a stack-trace
    surprise."""
    rt = _build()
    rt.run(5)
    rt.save(str(tmp_path))
    _write(tmp_path, "state.json", _read(tmp_path, "state.json")[: len(_read(tmp_path, "state.json")) // 3])

    with pytest.raises(ValueError, match="not valid JSON"):
        Runtime.load(str(tmp_path), attach=_attach)


def test_tampered_events_are_refused_at_the_door(tmp_path):
    """Editing one payload anywhere in events.jsonl (the file that was
    never checked at all before round 20a) changes the chain fold."""
    rt = _build()
    rt.run(10)
    rt.save(str(tmp_path))

    lines = _read(tmp_path, "events.jsonl").splitlines()
    assert lines
    row = json.loads(lines[0])
    row[3] = "mallory"  # rewrite the src of the first event
    lines[0] = json.dumps(row, separators=(",", ":"))
    _write(tmp_path, "events.jsonl", "\n".join(lines) + "\n")

    with pytest.raises(ValueError, match="chain check at the door"):
        Runtime.load(str(tmp_path), attach=_attach)


def test_interrupted_save_is_refused_by_name(tmp_path):
    """The crash window between appending events and replacing
    state.json leaves events.jsonl AHEAD of the watermark. The door
    refuses it by name instead of booting a wrong organism."""
    rt = _build()
    rt.run(10)
    rt.save(str(tmp_path))

    # simulate "events were appended, state.json never replaced"
    rt.run(3)
    rows = [json.dumps(e.row(), separators=(",", ":")) for e in rt.bus.log()]
    _write(tmp_path, "events.jsonl", "\n".join(rows) + "\n")

    with pytest.raises(ValueError, match="interrupted"):
        Runtime.load(str(tmp_path), attach=_attach)


# ---------------------------------------------------------------------------
# append-mode events
# ---------------------------------------------------------------------------

def test_events_file_is_append_mode(tmp_path):
    """Save twice: the second save appends only the delta. The first
    save's bytes are a byte-identical prefix — the file is never
    rewritten whole (the 94 ms autosave hitch the game-dev measured)."""
    rt = _build()
    rt.run(10)
    rt.save(str(tmp_path))
    first = _read(tmp_path, "events.jsonl")
    n_first = len(rt.bus)

    rt.run(10)  # ~2 events/tick + audits
    rt.save(str(tmp_path))
    second = _read(tmp_path, "events.jsonl")

    assert second.startswith(first)  # prefix byte-identical
    assert len(second.splitlines()) == len(rt.bus)
    assert len(rt.bus) > n_first  # the delta was actually appended


def test_save_to_a_different_path_writes_whole_once(tmp_path):
    """A save to a new path writes the full log once (checkpoint
    directories are independent files, not shared watermarks)."""
    rt = _build()
    rt.run(10)
    a = tmp_path / "a"
    b = tmp_path / "b"
    rt.save(str(a))
    rt.run(5)
    rt.save(str(b))
    text_b = _read(b, "events.jsonl")
    assert len(text_b.splitlines()) == len(rt.bus)  # everything, once
    rt.save(str(a))  # back to a: whole write again (a is behind)
    assert len(_read(a, "events.jsonl").splitlines()) == len(rt.bus)


# ---------------------------------------------------------------------------
# what persistence now carries
# ---------------------------------------------------------------------------

def test_sleeper_stats_and_idle_window_survive_save_load(tmp_path):
    """The dials docs/07 promises must survive a restart (the researcher
    persona found sleeper stats were live-API only, never persisted)."""
    rt = _build(idle_window=1)
    rt._components.clear()  # nothing runs -> the organism sleeps
    rt.run(12)
    assert rt.sleeper.stats.cycles > 0  # it really slept
    rt.save(str(tmp_path))

    rt2 = Runtime.load(str(tmp_path), attach=_attach)
    assert rt2.sleeper.stats == rt.sleeper.stats
    assert rt2.sleeper.idle_window == 1  # not silently reset to default


def test_born_zero_survives_load(tmp_path):
    """The game-dev persona's save-compat bug: a script spawned at tick 0
    came back re-stamped at the load tick, resetting its starvation
    grace window. An adopted script keeps its saved biography."""
    rt = _build()
    rt.run(12)
    assert rt.ecology.get("forage").born == 0
    rt.save(str(tmp_path))

    rt2 = Runtime.load(str(tmp_path), attach=_attach)
    s = rt2.ecology.get("forage")
    assert s is not None and s.born == 0  # not re-stamped to tick 12
    assert s.fires == rt.ecology.get("forage").fires


def test_persistence_roundtrip_is_still_exact(tmp_path):
    """The whole door apparatus must not change what a healthy
    save/load roundtrip carries: same state fields, same chain."""
    rt = _build()
    rt.run(20)
    rt.save(str(tmp_path))
    before = json.loads(_read(tmp_path, "state.json"))

    rt2 = Runtime.load(str(tmp_path), attach=_attach)
    rt2.save(str(tmp_path))  # re-save from the loaded organism
    after = json.loads(_read(tmp_path, "state.json"))

    assert after["event_chain_head"] == before["event_chain_head"]
    assert after["events_watermark"] == before["events_watermark"]
    assert after["sleeper"] == before["sleeper"]
    assert rt2.bus.chain_head == rt.bus.chain_head
    # and the loaded organism keeps living deterministically
    a = [r.ran for r in rt.run(5)]
    b = [r.ran for r in rt2.run(5)]
    assert a == b
