"""Fail-safe totality (round 17 — found by the wave-1 red team).

Six zero-shot engineers play-tested the repo as real users, judged as
users, and two holes in the documented fail-safe surfaced — both fatal
in production, both contradicting the docs:

* a component whose ``bid()`` raises (or returns junk) killed the whole
  tick loop (``runtime.py`` protected ``act()`` but not ``bid()`` — the
  documented "the body survives its organs" was half true);
* an arbiter that ANSWERED wrongly (a list of strings, a foreign
  look-alike bid, a single object) crashed the organism at
  ``chosen[0].label`` — the try/except covered exceptions, not
  malformed returns.

These tests pin the total fail-safe: every failure mode is contained,
recorded as an ERROR event with its reason, economically punished (the
broken organ starves on its own economics), never fatal — and
bit-for-bit deterministic while failing.
"""
from dataclasses import replace

import pytest

from cognitive_ecology import AttentionBid, EventKind, Outcome, Runtime


# ---------------------------------------------------------------------------
# fixtures: healthy contenders, broken organs, contended slots
# ---------------------------------------------------------------------------

def _bid(src, label, urgency=0.5):
    """One honest contender bid."""
    return AttentionBid(
        src=src, label=label, urgency=urgency, justification=1.0,
        opportunity=1.0, novelty=1.0, expected_value=1.0,
    )


class _Worker:
    """A healthy organ: bids every tick, succeeds."""

    def __init__(self, cid, why_node, label=None, fail_note=None):
        self.id, self.why_node = cid, why_node
        self.label = label or f"{cid}:work"
        self.fail_note = fail_note

    def bid(self, ctx):
        return [_bid(self.id, self.label)]

    def act(self, ctx, label):
        if self.fail_note:
            return Outcome(False, self.fail_note)
        return Outcome(True, "did it")


class _BrokenBidder:
    """Every failure mode of bid(), one per mode."""

    def __init__(self, cid, why_node, mode):
        self.id, self.why_node, self.mode = cid, why_node, mode

    def bid(self, ctx):
        if self.mode == "raise":
            raise ZeroDivisionError("bid organ fused")
        if self.mode == "non-iterable":
            return 7  # not iterable: contained at materialization
        if self.mode == "mixed":
            # one honest bid plus junk: the good bid still competes,
            # the junk is dropped, counted, and announced
            return [_bid(self.id, f"{self.id}:work"), "junk", 42]
        if self.mode == "gen-raise":
            def g():
                yield _bid(self.id, f"{self.id}:work")
                raise RuntimeError("generator blew up mid-yield")
            return g()
        raise AssertionError(f"unknown mode {self.mode}")  # pragma: no cover

    def act(self, ctx, label):
        return Outcome(True, "did it")


def _rt(components, top_k=2):
    """An organism with contended slots: every component gets its own
    living WHY so the gate never vetoes, and top_k < components."""
    rt = Runtime(seed=11, top_k=top_k, idle_window=999)
    rt.tensions.add("energy", growth=0.05)
    rt.declare_why("stay alive", node_id="why:root")
    for c in components:
        rt.declare_why(f"purpose of {c.id}", parent="why:root",
                       node_id=f"why:{c.id}")
        rt.register(c)
    return rt


def _errors(rt, who=None):
    return [e for e in rt.bus.log()
            if e.kind is EventKind.ERROR and (who is None or e.payload[0] == who)]


# ---------------------------------------------------------------------------
# the bid() seam: a broken organ must not stop the heart
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("mode", [
    "raise", "non-iterable", "mixed", "gen-raise",
])
def test_broken_bid_is_contained_and_recorded(mode):
    """Every bid() failure mode: the tick completes, the healthy organ
    keeps living, the failure is RECORDED with its reason, and the
    organism is conservation-green throughout."""
    rt = _rt([_Worker("w1", "why:w1"), _BrokenBidder("bad", "why:bad", mode)])
    reports = rt.run(20)

    # the heart never stopped — 20 ticks, law held on every audit
    assert len(reports) == 20
    assert all(r.conservation_ok is not False for r in reports)

    # the healthy organ lived its own life regardless of the sick one
    fired = [e for e in rt.bus.log()
             if e.kind is EventKind.NOTE_ON and e.payload[0] == "w1:work"]
    assert len(fired) == 20  # top_k=2, two contenders: it ran every tick

    # the failure is in the log — one ERROR per tick, with the reason
    errs = _errors(rt, "bad")
    assert len(errs) == 20
    if mode == "raise":
        assert errs[0].payload[2].startswith("ZeroDivisionError:")
    elif mode == "non-iterable":
        assert errs[0].payload[2].startswith("TypeError:")
    elif mode == "mixed":
        assert errs[0].payload[2] == "dropped 2 non-bid item(s)"
        # the junk was dropped but the honest bid still competed
        bad_fired = [e for e in rt.bus.log()
                     if e.kind is EventKind.NOTE_ON
                     and e.payload[0] == "bad:work"]
        assert len(bad_fired) == 20
    elif mode == "gen-raise":
        assert errs[0].payload[2].startswith("RuntimeError:")


def test_broken_bid_starves_only_itself():
    """The sick organ's failure never touches the healthy one's outcomes:
    same seed, with and without the broken component — w1's life is
    semantically identical (same bids, decisions, and notes; log
    positions shift because the ERROR events interleave, so compare
    content, not seq)."""
    def _sem(e):
        return (int(e.kind), e.ts, e.src, tuple(e.payload))

    rt_clean = _rt([_Worker("w1", "why:w1")])
    rt_clean.run(20)
    rt_sick = _rt([_Worker("w1", "why:w1"),
                   _BrokenBidder("bad", "why:bad", "raise")])
    rt_sick.run(20)

    w1_clean = [e for e in rt_clean.bus.log() if e.src == "w1"]
    w1_sick = [e for e in rt_sick.bus.log() if e.src == "w1"]
    assert [_sem(e) for e in w1_clean] == [_sem(e) for e in w1_sick]


def test_broken_bid_is_deterministic():
    """A failing organ is still a reproducible organ: two runs with the
    same seed produce byte-identical event logs, failures included."""
    logs = []
    for _ in range(2):
        rt = _rt([_Worker("w1", "why:w1"),
                  _BrokenBidder("bad", "why:bad", "raise")])
        rt.run(15)
        logs.append(rt.bus.to_jsonl())
    assert logs[0] == logs[1]


# ---------------------------------------------------------------------------
# the act() seam: failure reasons reach the log
# ---------------------------------------------------------------------------

def test_failed_action_reason_reaches_the_log():
    """On-call can ask WHY an action failed, not just THAT it failed:
    NOTE_ON stays a 2-tuple; the reason rides its own cause-chained
    ERROR event."""
    rt = _rt([_Worker("w1", "why:w1", fail_note="the pond dried up")])
    rt.run(10)

    notes = [e for e in rt.bus.log()
             if e.kind is EventKind.NOTE_ON and e.payload[0] == "w1:work"]
    assert len(notes) == 10
    assert all(len(e.payload) == 2 for e in notes)  # MIDI shape untouched
    assert all(e.payload[1] == 0 for e in notes)

    reasons = _errors(rt, "w1:work")
    assert len(reasons) == 10
    assert all(e.payload == ("w1:work", "act", "the pond dried up")
               for e in reasons)
    # cause-chained to the very decision that authorized the action
    decisions = {e.seq for e in rt.bus.log() if e.kind is EventKind.DECISION}
    assert all(e.cause in decisions for e in reasons)


def test_successful_actions_emit_no_error_events():
    """The reason channel is silent when there is nothing to explain."""
    rt = _rt([_Worker("w1", "why:w1"), _Worker("w2", "why:w2")])
    rt.run(10)
    assert _errors(rt) == []


# ---------------------------------------------------------------------------
# the arbiter seam: a malformed ANSWER is a failed answer, not a crash
# ---------------------------------------------------------------------------

def _foreign_lookalike(live, k):
    """Equal fields, different object: not the bid the market priced."""
    return [replace(live[0])]


_MALFORMED_ANSWERS = {
    "strings": lambda live, k: ["a", "b", "c"],
    "single-object": lambda live, k: live[0],
    "dict": lambda live, k: {"bids": live},
    "empty": lambda live, k: [],
    "duplicates": lambda live, k: [live[0], live[0]],
    "generator": lambda live, k: iter(live),
    "foreign-lookalikes": _foreign_lookalike,
}


@pytest.mark.parametrize("name", sorted(_MALFORMED_ANSWERS))
def test_malformed_arbiter_answers_degrade_never_crash(name):
    """The exact failure class that used to kill the organism (found by
    the ML-engineer persona): the answer fails validation, the
    deterministic shadow stands, the failure is counted and recorded —
    and the organism's behavior is IDENTICAL to having no arbiter."""
    arb = _MALFORMED_ANSWERS[name]
    workers = [_Worker(f"w{i}", f"why:w{i}") for i in (1, 2, 3)]
    rt = _rt(workers, top_k=2)  # 3 live contenders > 2 slots: called every tick
    rt.executive.arbiter = arb
    reports = rt.run(15)  # would raise before round 17

    # the shadow stood: behavior identical to the no-arbiter twin
    twin = _rt([_Worker(f"w{i}", f"why:w{i}") for i in (1, 2, 3)], top_k=2)
    twin_reports = twin.run(15)
    assert [r.ran for r in reports] == [r.ran for r in twin_reports]

    # a non-answer is not a divergence — nothing was overridden
    assert rt.executive.last_divergence == 0

    # counted and recorded, once per call
    assert rt.executive.arbiter_calls == 15
    assert rt.executive.arbiter_malformed == 15
    malformed_events = [e for e in rt.bus.log()
                         if e.kind is EventKind.ERROR
                         and e.payload[:2] == ("arbiter", "malformed return")]
    assert len(malformed_events) == 15
    assert all(e.src == "executive" for e in malformed_events)


def test_malformed_answers_are_deterministic():
    """Failing judgment is still reproducible judgment: two runs,
    byte-identical logs including the malformed-return ERROR events."""
    logs = []
    for _ in range(2):
        rt = _rt([_Worker(f"w{i}", f"why:w{i}") for i in (1, 2, 3)], top_k=2)
        rt.executive.arbiter = _MALFORMED_ANSWERS["strings"]
        rt.run(12)
        logs.append(rt.bus.to_jsonl())
    assert logs[0] == logs[1]


def test_malformed_arbiter_can_recover():
    """Degradation is per-tick, not a scar: an arbiter that speaks
    wrongly for 5 calls and then properly is trusted again from call 6
    — chronic badness remains the scorecard's business (benched by
    outcomes, never by protocol stumbles)."""
    class _Flaky:
        def __init__(self):
            self.calls = 0

        def __call__(self, live, k):
            self.calls += 1
            if self.calls <= 5:
                return ["a", "b", "c"]  # malformed phase
            return list(reversed(live))  # honest, divergent phase

    rt = _rt([_Worker(f"w{i}", f"why:w{i}") for i in (1, 2, 3)], top_k=2)
    flaky = _Flaky()
    rt.executive.arbiter = flaky
    rt.run(12)

    assert rt.executive.arbiter_malformed == 5
    assert rt.executive.last_divergence >= 1  # it overrode the shadow later
    # and the malformed events stopped after the recovery
    malformed = [e for e in rt.bus.log()
                 if e.kind is EventKind.ERROR
                 and e.payload[:2] == ("arbiter", "malformed return")]
    assert len(malformed) == 5
