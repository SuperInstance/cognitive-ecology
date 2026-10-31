"""Example 09 — Hosting an organism: three shapes, one contract.

Run:  python examples/09_host_drivers/main.py   (keyless, offline, ~2s)

The kernel's time is TICKS; wall-clock time is the host's problem.
The contract underneath every recipe in docs/10_host_integration.md:

    A DRIVER OWNS *WHEN*. IT MUST NEVER INFLUENCE *WHAT*.
    Same seed + same code + same ingested events = the same life,
    whether it ran in 2 seconds or 2 weeks.

Three hosting shapes, demonstrated live:

  SHAPE 1  the game loop — fixed-timestep accumulator (frame-rate
           independent: 300 fps or 30 fps, the organism sees the same
           tick stream);
  SHAPE 2  the wall-clock session — WallClockDriver with drift-free
           pacing, a checkpoint cadence, a host stop, and a receipt;
  SHAPE 3  the cron tick — load, tick a budget, save, exit (the
           shape behind every scheduler entry and systemd timer);

plus the checkpoint rotation recipe (keep the last K saves; a corrupt
newest never orphans you — the previous checkpoint is one hop away).
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from cognitive_ecology import (  # noqa: E402
    Outcome, Runtime, Script, WallClockDriver,
)

SAVE = Path(__file__).resolve().parents[2] / "runs" / "hosted"


# ---------------------------------------------------------------------------
# the organism: a desk that answers questions when they pile up
# ---------------------------------------------------------------------------
def build(seed: int = 21) -> Runtime:
    rt = Runtime(seed=seed, top_k=2)
    rt.declare_why("the desk serves its user", node_id="why:desk")
    rt.tensions.add("questions", growth=0.30)
    rt.ecology.spawn(Script(
        name="answer", why_node="why:desk", owner="desk",
        relieves=("questions",),
        act=lambda ctx: (
            ctx.tensions.relieve("questions", 0.9),
            Outcome(True, "answered"),
        )[1],
    ), tick=0)

    class Desk:
        id = "desk"
        why_node = "why:desk"

        def bid(self, ctx):
            return ctx.ecology.bids(ctx, owner="desk")

        def act(self, ctx, label):
            return ctx.ecology.fire(label, ctx)

    rt.register(Desk())
    return rt


def banner(text: str) -> None:
    print(f"\n{'=' * 64}\n  {text}\n{'=' * 64}")


# ---------------------------------------------------------------------------
# SHAPE 1: the game loop — fixed-timestep accumulator
# ---------------------------------------------------------------------------
def shape_game_loop() -> None:
    banner("SHAPE 1 — the game loop (fixed-timestep accumulator)")
    rt = build(seed=21)

    # a "frame" is whatever the render loop gives us; the organism only
    # ever sees whole ticks. accumulator turns variable frame times into
    # a fixed tick rate — the standard game-physics pattern, reused.
    # The EPSILON is not decoration: summing 1/30 ninety times gives
    # 2.9999999999999994, and an epsilon-free accumulator silently
    # drops the third tick. (This demo caught itself doing exactly that
    # — see docs/10, "the accumulator's epsilon".)
    TICK_DT = 1.0        # one organism tick per simulated second
    EPS = 1e-9           # float undershoot guard

    def run_frames(frame_times: list) -> Runtime:
        rt = build(seed=21)
        acc = 0.0
        for dt in frame_times:
            acc += dt
            while acc + EPS >= TICK_DT:
                rt.tick()
                acc -= TICK_DT
        return rt

    rt = run_frames([1 / 60] * 180)      # 180 frames of a 60 fps game (3 s)
    ticks = rt.tick_no
    print(f"frames simulated : 180 (60 fps for 3 seconds)")
    print(f"organism ticks   : {ticks} (accumulator ate the frame jitter)")
    print(f"conservation     : {rt.why.conservation()['invariant_ok']}")
    # frame-rate independence: 30 fps frames produce the same life
    rt30 = run_frames([1 / 30] * 90)     # 30 fps for 3 seconds — half the frames
    same = rt.bus.to_jsonl() == rt30.bus.to_jsonl()
    print(f"30 fps twin      : identical life = {same} (the contract holds)")


# ---------------------------------------------------------------------------
# SHAPE 2: the wall-clock session — WallClockDriver
# ---------------------------------------------------------------------------
def shape_wall_clock() -> None:
    banner("SHAPE 2 — the wall-clock session (WallClockDriver)")
    rt = build(seed=22)

    class FakeClock:
        """Deterministic wall time: tests (and this demo) inject their
        own clock so a '60 second session' runs in microseconds."""

        def __init__(self):
            self.t = 1000.0

        def monotonic(self) -> float:
            return self.t

        def sleep(self, seconds: float) -> None:
            self.t += seconds   # sleeping simply advances the fake clock

    clock = FakeClock()
    driver = WallClockDriver(
        interval=0.05,                    # aim for 20 ticks/second
        sleep_fn=clock.sleep,
        monotonic_fn=clock.monotonic,
    )
    stopped_at = []
    report = driver.run(
        rt,
        seconds=3.0,                      # stop condition: 3 s of wall time
        max_ticks=10_000,                 # (and never more than 10k ticks)
        save_every=20, save_path=str(SAVE),   # checkpoint every 20 ticks
        on_tick=lambda r: stopped_at.append(r.tick) if r.tick % 20 == 0 else None,
    )
    print(f"ticks driven     : {report.ticks}")
    print(f"wall seconds     : {report.wall_seconds:.2f} (fake clock)")
    print(f"stopped by       : {report.stopped_by}")
    print(f"checkpoints      : {report.saves}")
    print(f"mean tps         : {report.mean_tps():.1f}")
    print(f"drift check      : {report.ticks} ticks / 0.05s = "
          f"{report.ticks * 0.05:.2f}s == wall {report.wall_seconds:.2f}s")
    # a host-initiated stop is first-class too:
    rt2 = build(seed=22)
    clock2 = FakeClock()
    rep2 = WallClockDriver(0.05, sleep_fn=clock2.sleep,
                           monotonic_fn=clock2.monotonic).run(
        rt2, max_ticks=100,
        on_tick=lambda r: r.tick < 7,      # False means "the player quit"
    )
    print(f"host stop        : stopped_by={rep2.stopped_by} at tick {rep2.ticks}")


# ---------------------------------------------------------------------------
# SHAPE 3: the cron tick — load, tick, save, exit
# ---------------------------------------------------------------------------
def shape_cron() -> None:
    banner("SHAPE 3 — the cron tick (load -> tick a budget -> save -> exit)")
    # the cron entry is one line:
    #   * * * * * cd /srv/app && python -m app.tick_organism
    # and app.tick_organism is the six lines below. The organism advances
    # 5 ticks per minute, forever, across machines and restarts.
    if (SAVE / "state.json").exists():
        rt = Runtime.load(str(SAVE), attach=lambda r: _attach_desk(r))
        print(f"loaded           : tick {rt.tick_no} (continuing a saved life)")
    else:
        rt = build(seed=23)
        _attach_desk(rt)
        print("fresh organism   : tick 0")
    before = rt.tick_no
    rt.run(5)                 # the tick budget for this invocation
    rt.save(str(SAVE))
    print(f"ticked           : {before} -> {rt.tick_no}, saved, exiting")
    print("questions relief : "
          f"{rt.tensions.snapshot()['questions']:.2f} (homeostasis, minute by minute)")


def _attach_desk(rt: Runtime) -> None:
    """The cron attach rite: rebuild behavior in code, adopt saved stats.

    Closures are code, not data — load() restores state, and this
    function restores behavior: the Desk component plus the 'answer'
    script, whose track record comes back via adopt(). (The ergonomic
    version of this rite — idempotent ensure_* builders — is the
    round-23 work; see docs/10 § The attach rite.)
    """

    class Desk:
        id = "desk"
        why_node = "why:desk"

        def bid(self, ctx):
            return ctx.ecology.bids(ctx, owner="desk")

        def act(self, ctx, label):
            return ctx.ecology.fire(label, ctx)

    rt.register(Desk())
    rt.ecology.adopt(Script(
        name="answer", why_node="why:desk", owner="desk",
        relieves=("questions",),
        act=lambda ctx: (
            ctx.tensions.relieve("questions", 0.9),
            Outcome(True, "answered"),
        )[1],
    ), tick=rt.tick_no)


# ---------------------------------------------------------------------------
# the checkpoint rotation recipe
# ---------------------------------------------------------------------------
def recipe_rotation() -> None:
    banner("RECIPE — rotating checkpoints (keep the last K)")
    base = SAVE.parent / "hosted-rot"
    if base.exists():
        shutil.rmtree(base)
    base.mkdir(parents=True)

    rt = build(seed=24)
    for i in range(1, 4):                    # three "sessions"
        rt.run(10)
        # rotate: newest is always `current`, older ones shift back
        for k in range(2, 0, -1):            # keep K=2
            src = base / f"checkpoint.{k - 1}" if k > 1 else base / "current"
            dst = base / f"checkpoint.{k}"
            if src.exists():
                if dst.exists():
                    shutil.rmtree(dst)
                src.rename(dst)
        rt.save(str(base / "current"))
        print(f"session {i}: saved; checkpoints on disk = "
              f"{sorted(p.name for p in base.iterdir())}")
    print("a corrupt 'current' costs at most one session: the previous")
    print("checkpoint is one rename away — and save() is atomic, so a")
    print("crash mid-write leaves the previous state byte-intact (round 20a).")


def main() -> None:
    if SAVE.exists():
        shutil.rmtree(SAVE)
    shape_game_loop()
    shape_wall_clock()
    shape_cron()
    recipe_rotation()
    banner("ONE CONTRACT")
    print("the driver owns WHEN; the organism decides WHAT. Every recipe")
    print("in docs/10_host_integration.md is this contract wearing a")
    print("different harness. Ticks, not wall-clock — reproducible lives.")
    # cleanup the demo's runs dir so the repo stays tidy
    shutil.rmtree(SAVE, ignore_errors=True)
    shutil.rmtree(SAVE.parent / "hosted-rot", ignore_errors=True)


if __name__ == "__main__":
    main()
