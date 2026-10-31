#!/usr/bin/env python3
"""The tiny MUD: the smallest persistent world, live.

Five processes, ~17 seeded scripts, one WHY graph, one sleep cycle. Run it
for a few days and watch the morning briefings scroll by — the world keeps
working whether or not anyone is watching.

    python examples/tiny_mud.py --days 3
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ecology.demo import TinyMud  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=3)
    parser.add_argument("--ticks-per-day", type=int, default=30)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    mud = TinyMud(seed=args.seed, day_len=args.ticks_per_day, quiet=False)
    for _ in range(args.days * args.ticks_per_day):
        mud.step()
    print("\n(final script census:", mud.scripts.census(), ")")
    return 0


if __name__ == "__main__":
    sys.exit(main())
