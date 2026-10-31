#!/usr/bin/env python3
"""The week in a box: can a persistent world improve itself unattended?

The manifesto's core experiment. Seven compressed days: the environment
emits, the reflex layer handles, sleep compiles routines, the WHY graph
keeps score — and on day 4 a root goal dies so the conservation law has
something to bite. Nobody prompts anything.

    python examples/week_in_a_box.py [--days 7] [--seed 42]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ecology.demo import WeekInABox  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--ticks-per-day", type=int, default=30)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--verbose", action="store_true", help="print daily briefings")
    args = parser.parse_args()

    report = WeekInABox(
        seed=args.seed, days=args.days, day_len=args.ticks_per_day, quiet=not args.verbose
    ).run()
    print()
    for line in report.leverage_lines():
        print(line)
    print()
    print("per-day necessity census:")
    for day in report.days:
        active = {k: v for k, v in day.necessity.items() if v}
        print(f"  day {day.day}: scripts={day.scripts} necessity={active}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
