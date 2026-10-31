"""Host drivers: the seam between wall-clock and tick time (round 22).

The contract underneath every recipe in docs/10:

    A DRIVER OWNS *WHEN*. IT MUST NEVER INFLUENCE *WHAT*.

These tests pin that contract with injected clocks (no real sleeping
in a test suite), plus the receipt, the stop conditions, the
checkpoint cadence, and the graceful endings — everything the wave-1
hosts rebuilt by hand and got wrong in the same three ways.
"""
from __future__ import annotations

import json

import pytest

from cognitive_ecology import Runtime, WallClockDriver
from cognitive_ecology.scripts import Outcome, Script

from experiments.minimal_world import build_world


class FakeClock:
    """Deterministic wall time: sleeping advances the clock, nothing else."""

    def __init__(self, start: float = 1000.0):
        self.t = start
        self.slept: list = []

    def monotonic(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.t += seconds


def _desk(seed: int = 5) -> Runtime:
    rt = Runtime(seed=seed, top_k=2)
    rt.declare_why("serve the user", node_id="why:desk")
    rt.tensions.add("questions", growth=0.3)

    class Desk:
        id = "desk"
        why_node = "why:desk"

        def bid(self, ctx):
            return ctx.ecology.bids(ctx, owner="desk")

        def act(self, ctx, label):
            return ctx.ecology.fire(label, ctx)

    rt.register(Desk())
    rt.ecology.spawn(Script(
        name="answer", why_node="why:desk", owner="desk",
        relieves=("questions",),
        act=lambda ctx: Outcome(True, "ok"),
    ), tick=0)
    return rt


class TestContract:
    def test_driven_life_is_the_plain_life_bit_for_bit(self):
        """WHEN must not influence WHAT: a driven run and rt.run(n)
        produce byte-identical event streams."""
        driven, plain = _desk(9), _desk(9)
        clock = FakeClock()
        report = WallClockDriver(0.01, sleep_fn=clock.sleep,
                                 monotonic_fn=clock.monotonic).run(
            driven, max_ticks=30)
        assert report.ticks == 30
        plain.run(30)
        assert driven.bus.to_jsonl() == plain.bus.to_jsonl()

    def test_pacing_is_drift_free(self):
        """Absolute-slot scheduling: like a metronome, the FIRST tick
        lands at t=0, so 3.0 s at 0.05 s intervals is 61 ticks spanning
        60 intervals — no cumulative sleep error."""
        clock = FakeClock()
        rt = _desk(3)
        report = WallClockDriver(0.05, sleep_fn=clock.sleep,
                                 monotonic_fn=clock.monotonic).run(
            rt, seconds=3.0)
        assert report.ticks == 61
        assert report.wall_seconds == pytest.approx(3.0)
        assert report.stopped_by == "duration"
        # every sleep aimed at an absolute slot: exactly 0.05, no drift
        assert all(s == pytest.approx(0.05) for s in clock.slept)
        assert len(clock.slept) == 60


class TestStopConditions:
    def test_max_ticks(self):
        clock = FakeClock()
        report = WallClockDriver(0.1, sleep_fn=clock.sleep,
                                 monotonic_fn=clock.monotonic).run(
            _desk(), max_ticks=7)
        assert report.ticks == 7 and report.stopped_by == "max_ticks"

    def test_host_stop_on_false(self):
        clock = FakeClock()
        report = WallClockDriver(0.1, sleep_fn=clock.sleep,
                                 monotonic_fn=clock.monotonic).run(
            _desk(), max_ticks=100,
            on_tick=lambda r: r.tick < 4,   # "the player quit" at 4
        )
        assert report.ticks == 4 and report.stopped_by == "host"

    def test_keyboard_interrupt_is_graceful(self):
        clock = FakeClock()

        def explode(seconds: float) -> None:
            raise KeyboardInterrupt("^C during a sleep")

        report = WallClockDriver(0.1, sleep_fn=explode,
                                 monotonic_fn=clock.monotonic).run(
            _desk(), max_ticks=10)
        # tick 1 happens at t=0 (before any sleep); the ^C lands on the
        # first sleep: one tick lived, the session ended cleanly
        assert report.ticks == 1 and report.stopped_by == "keyboard"
        assert report.error is None

    def test_tick_error_is_reported_never_raised(self):
        clock = FakeClock()

        class Boom:
            def tick(self):
                raise RuntimeError("the body broke")

        report = WallClockDriver(0.1, sleep_fn=clock.sleep,
                                 monotonic_fn=clock.monotonic).run(
            Boom(), max_ticks=5)
        assert report.stopped_by == "error"
        assert "RuntimeError" in report.error


class TestCheckpoints:
    def test_save_every_cadence_and_final_save(self, tmp_path):
        clock = FakeClock()
        path = str(tmp_path / "organism")
        report = WallClockDriver(0.01, sleep_fn=clock.sleep,
                                 monotonic_fn=clock.monotonic).run(
            _desk(), max_ticks=25, save_every=10, save_path=path)
        # saves at 10, 20 + a final save for the tick-25 tail
        assert report.saves == 3
        with open(path + "/state.json", encoding="utf-8") as f:
            state = json.load(f)
        assert state["tick"] == 25

    def test_exact_multiple_saves_no_double_write(self, tmp_path):
        clock = FakeClock()
        path = str(tmp_path / "organism")
        report = WallClockDriver(0.01, sleep_fn=clock.sleep,
                                 monotonic_fn=clock.monotonic).run(
            _desk(), max_ticks=30, save_every=10, save_path=path)
        assert report.saves == 3  # 10, 20, 30 — no redundant final save


class TestReceipt:
    def test_report_carries_the_session_facts(self):
        clock = FakeClock()
        report = WallClockDriver(0.1, sleep_fn=clock.sleep,
                                 monotonic_fn=clock.monotonic).run(
            _desk(), max_ticks=10)
        assert report.ticks == 10
        # 10 ticks span 9 intervals (first lands at t=0, metronome-style)
        assert report.wall_seconds == pytest.approx(0.9)
        assert report.mean_tps() == pytest.approx(10 / 0.9)
        assert report.stopped_by == "max_ticks"

    def test_on_stop_receives_the_report(self):
        clock = FakeClock()
        seen = []
        WallClockDriver(0.1, sleep_fn=clock.sleep,
                        monotonic_fn=clock.monotonic).run(
            _desk(), max_ticks=3, on_stop=seen.append)
        assert seen and seen[0].ticks == 3

    def test_bad_interval_is_rejected(self):
        with pytest.raises(ValueError):
            WallClockDriver(0)


class TestRealOrganism:
    def test_drive_the_demo_organism(self):
        """minimal_world under the driver: same life as rt.run()."""
        driven, plain = build_world(4), build_world(4)
        clock = FakeClock()
        WallClockDriver(0.02, sleep_fn=clock.sleep,
                        monotonic_fn=clock.monotonic).run(
            driven, max_ticks=40)
        plain.run(40)
        assert driven.bus.to_jsonl() == plain.bus.to_jsonl()
        assert driven.why.conservation()["invariant_ok"]
