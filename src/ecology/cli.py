"""The ecology CLI.

Commands mirror the two faces of the project:

- ``check``  — the WHY flashlight, format-compatible with the Rust ``why``
  CLI (same statuses, same exit codes), so both implementations can be run
  against the same graph.txt/att.txt and diffed.
- ``week``   — the week-in-a-box experiment: the smallest persistent world
  improving itself while nobody watches.
- ``briefing`` — one morning briefing from a persisted world (v0.1: runs in-memory).
- ``panel`` / ``usage`` — the LLM teacher layer (multi-model discussion,
  cost ledger); see ecology.llm.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import why
from .demo import WeekInABox


def _cmd_check(args: argparse.Namespace) -> int:
    """Status of every node. Exit 1 iff any dead (unknown never fails)."""
    graph = why.parse_graph(Path(args.graph).read_text())
    attestation = why.Attestation()
    if args.alive:
        attestation = why.parse_attestation(Path(args.alive).read_text())
    as_of = args.as_of if args.as_of else (None if args.no_clock else why.today())
    evaluation = why.evaluate(graph, attestation, as_of)
    for node_id in sorted(evaluation.status):
        print(f"{evaluation.status[node_id].value}\t{node_id}")
    if evaluation.coverage is not None:
        cov = evaluation.coverage
        print(f"coverage: {cov.wired}/{cov.discovered} ({cov.pct:.0f}%)")
        if args.fail_under is not None and cov.pct < args.fail_under:
            print(f"FAIL: coverage below --fail-under {args.fail_under}%", file=sys.stderr)
            return 1
    if evaluation.expired_roots:
        print(f"expired roots: {', '.join(sorted(evaluation.expired_roots))}", file=sys.stderr)
    dead = [n for n, s in evaluation.status.items() if s is why.Status.DEAD]
    if dead:
        print(f"{len(dead)} dead findings", file=sys.stderr)
        return 1
    return 0


def _cmd_week(args: argparse.Namespace) -> int:
    report = WeekInABox(seed=args.seed, days=args.days, day_len=args.ticks, quiet=False).run()
    print()
    for line in report.leverage_lines():
        print(line)
    if args.json:
        import json

        print(json.dumps([d.__dict__ for d in report.days], indent=2, default=str))
    return 0


def _cmd_briefing(_args: argparse.Namespace) -> int:

    week = WeekInABox(quiet=True)
    week.run()
    # briefing for the final morning
    return 0


def _cmd_panel(args: argparse.Namespace) -> int:
    try:
        from ecology.research.discussion import run_panel_cli
    except ImportError as exc:
        print(f"panel requires the llm extras: {exc}", file=sys.stderr)
        return 2
    return run_panel_cli(args)


def _cmd_usage(_args: argparse.Namespace) -> int:
    try:
        from ecology.llm.ledger import usage_cli
    except ImportError as exc:
        print(f"usage requires the llm extras: {exc}", file=sys.stderr)
        return 2
    return usage_cli()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ecology", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_check = sub.add_parser("check", help="status of every node in a why graph")
    p_check.add_argument("graph", help="path to graph.txt")
    p_check.add_argument("--alive", help="path to att.txt")
    p_check.add_argument("--as-of", help="evaluation date YYYY-MM-DD (default: today)")
    p_check.add_argument("--no-clock", action="store_true", help="ignore expiry fields")
    p_check.add_argument("--fail-under", type=float, help="fail if coverage %% below this")
    p_check.set_defaults(func=_cmd_check)

    p_week = sub.add_parser("week", help="run the week-in-a-box experiment")
    p_week.add_argument("--days", type=int, default=7)
    p_week.add_argument("--ticks", type=int, default=30, help="ticks per day")
    p_week.add_argument("--seed", type=int, default=42)
    p_week.add_argument("--json", action="store_true", help="also print per-day JSON")
    p_week.set_defaults(func=_cmd_week)

    p_brief = sub.add_parser("briefing", help="one morning briefing (demo world)")
    p_brief.set_defaults(func=_cmd_briefing)

    p_panel = sub.add_parser("panel", help="run a multi-model discussion round")
    p_panel.add_argument("--topic", required=True)
    p_panel.add_argument("--context", help="path to a context document")
    p_panel.add_argument("--rounds", type=int, default=1)
    p_panel.add_argument("--out", help="output markdown path")
    p_panel.set_defaults(func=_cmd_panel)

    p_usage = sub.add_parser("usage", help="provider usage and cost report")
    p_usage.set_defaults(func=_cmd_usage)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
