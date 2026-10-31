"""Host drivers: the bridge between wall-clock time and tick time.

The kernel's time is TICKS — an integer the organism advances itself.
That is what makes a life reproducible: same seed, same code, same
sequence of decisions, forever. Wall-clock time is the HOST's problem:
when to tick, how often, for how long.

This module is the honest seam between the two. A driver owns WHEN;
it must never influence WHAT. Ticking the same organism at different
wall-clock rates produces the same life, tick for tick — that
contract is pinned by test (a driven run and a plain ``rt.run(n)``
must produce byte-identical event streams).

The wave-1 play-tests found every host rebuilding this seam by hand
and getting the same three things wrong: cumulative sleep drift (never
schedule ``sleep(interval)`` in a loop — schedule against a monotonic
``next_at``), lost work on Ctrl-C (the driver must stop gracefully and
give the host its report), and silent state loss (periodic save hooks
that never fire because the process died between them).

Usage
-----
    from cognitive_ecology import Runtime, WallClockDriver

    rt = build_my_organism()
    driver = WallClockDriver(interval=0.1)          # seconds per tick
    report = driver.run(
        rt, seconds=60,                              # any two of these
        max_ticks=600,                               # three stop
        save_every=100, save_path="runs/organism",   # conditions
    )                                                 # are optional
    print(report.stopped_by, report.ticks, report.mean_tps())

The other hosting shapes — a fixed-timestep game loop, a web-app
lifespan task, cron — are recipes built on this same contract:
``docs/10_host_integration.md``.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class DriverReport:
    """What one driving session did — the host's receipt."""

    ticks: int = 0
    wall_seconds: float = 0.0
    stopped_by: str = "none"   # duration | max_ticks | keyboard | error
    error: Optional[str] = None
    saves: int = 0

    def mean_tps(self) -> float:
        """Mean ticks per wall-clock second (0 when nothing ran)."""
        return self.ticks / self.wall_seconds if self.wall_seconds > 0 else 0.0


class WallClockDriver:
    """Ticks an organism on a fixed wall-clock interval, drift-free.

    Scheduling is against ``monotonic()`` (``next_at = start + n *
    interval``), so sleeps never accumulate error — a 10 Hz driver
    still does 600 ticks in a minute, not 600-minus-sleep-jitter.
    ``sleep_fn``/``monotonic_fn`` are injectable so tests (and hosts
    with their own clocks) can drive time exactly.

    The determinism contract: the driver calls ``rt.tick()`` and
    NOTHING else that touches organism state. Wall time never enters
    the organism — not in events, not in seeds, not in decisions.
    """

    def __init__(self, interval: float,
                 sleep_fn: Callable[[float], None] = time.sleep,
                 monotonic_fn: Callable[[], float] = time.monotonic) -> None:
        if interval <= 0:
            raise ValueError("interval must be positive (ticks per second > 0)")
        self.interval = float(interval)
        self._sleep = sleep_fn
        self._now = monotonic_fn

    def run(self, rt, seconds: Optional[float] = None,
            max_ticks: Optional[int] = None, on_tick: Optional[Callable] = None,
            save_every: int = 0, save_path: Optional[str] = None,
            on_stop: Optional[Callable[[DriverReport], None]] = None,
            ) -> DriverReport:
        """Drive the organism until a stop condition fires.

        Stop conditions (any may be given; the first to fire wins):
          seconds    wall-clock duration of the session
          max_ticks  tick budget
          Ctrl-C     graceful: the session stops cleanly and the report
                     says ``keyboard`` (the exception is swallowed here
                     by design — the host decides what ending means)

        ``save_every``/``save_path`` checkpoint the organism every N
        ticks (and once more at the end), so a crash costs at most N
        ticks of history. ``on_tick(tick_report)`` runs after each tick
        and may return ``False`` to stop the session (stopped_by
        ``host`` — e.g. "the player quit").
        """
        report = DriverReport()
        start = self._now()
        next_at = start
        try:
            while True:
                if max_ticks is not None and report.ticks >= max_ticks:
                    report.stopped_by = "max_ticks"
                    break
                if seconds is not None and (self._now() - start) >= seconds:
                    report.stopped_by = "duration"
                    break
                # drift-free pacing: aim at absolute slots, not relative sleeps
                now = self._now()
                if now < next_at:
                    self._sleep(next_at - now)
                last = rt.tick()
                report.ticks += 1
                if save_every and save_path and report.ticks % save_every == 0:
                    rt.save(save_path)
                    report.saves += 1
                if on_tick is not None and on_tick(last) is False:
                    report.stopped_by = "host"
                    break
                # tick N landed at (N-1)*interval from start (tick 1 at
                # t=0, like a metronome); aim the next slot at N*interval
                next_at = start + report.ticks * self.interval
        except KeyboardInterrupt:
            report.stopped_by = "keyboard"
        except Exception as exc:  # a driving error is reported, never raised
            report.stopped_by = "error"
            report.error = f"{exc.__class__.__name__}: {exc}"
        finally:
            # final checkpoint when the tail wasn't just saved
            if save_every and save_path and report.ticks % save_every != 0:
                rt.save(save_path)
                report.saves += 1
            report.wall_seconds = self._now() - start
            if on_stop is not None:
                on_stop(report)
        return report
