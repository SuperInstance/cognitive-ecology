"""Headless rounds runner with JSONL telemetry.

Runs the minimal-world organism for N ticks and writes per-tick telemetry,
so you can study attention dynamics, starvation, and conservation offline.

    python scripts/run_rounds.py --ticks 300 --out runs/exp1 --seed 7

Outputs (under --out):
    telemetry.jsonl   one row per tick (ran / starved / slept / events)
    state.json        the organism's saved state at the end
    events.jsonl      the full append-only event log
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.minimal_world import build_world  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="headless rounds with telemetry")
    ap.add_argument("--ticks", type=int, default=200)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--top-k", type=int, default=2)
    ap.add_argument("--out", default="runs/rounds")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    rt = build_world(args.seed)
    rt.top_k = args.top_k

    telemetry_path = os.path.join(args.out, "telemetry.jsonl")
    with open(telemetry_path, "w", encoding="utf-8") as f:
        for report in rt.run(args.ticks):
            f.write(json.dumps(report.to_row(), sort_keys=True) + "\n")

    rt.save(args.out)

    ran_ticks = sum(1 for r in rt.bus.log() if r.kind.name == "NOTE_ON")
    print(f"ticks        : {args.ticks}")
    print(f"actions fired: {ran_ticks}")
    print(f"events       : {len(rt.bus)}")
    print(f"live scripts : {rt.ecology.population()}")
    print(f"necrology    : {len(rt.ecology.necrology())}")
    print(f"graph        : {rt.graph.node_count()} nodes / {rt.graph.edge_count()} edges")
    print(f"conservation : {rt.why.conservation()}")
    print(f"outputs      : {args.out}/ (telemetry.jsonl, state.json, events.jsonl)")


if __name__ == "__main__":
    main()
