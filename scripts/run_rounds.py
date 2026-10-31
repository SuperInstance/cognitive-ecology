"""Headless rounds runner with JSONL telemetry, provenance, and sweeps.

Runs the minimal-world organism for N ticks and writes per-tick telemetry,
so you can study attention dynamics, starvation, and conservation offline.

    python scripts/run_rounds.py --ticks 300 --out runs/exp1 --seed 7

    # a seed sweep: same scenario, five worlds, one aggregate
    python scripts/run_rounds.py --ticks 300 --sweep 5 --out runs/sweep1

Outputs (under --out):
    telemetry.jsonl   one row per tick (ran / starved / slept / events)
    market.jsonl      the market log read model: every bid of every clear,
                      exact floats (round 21 — see docs/09_market_log.md)
    manifest.json     provenance: seed, config, versions, git commit,
                      output digests — a run can never be an orphan again
    state.json        the organism's saved state at the end
    events.jsonl      the append-only event log (chain-verified at load)

With --sweep N: one subdirectory per seed (seed_<s>/) each holding the
full outputs above, plus a top-level summary.json aggregating the key
metrics across seeds (mean and spread) — the experiment harness the
researcher persona asked for, above single runs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.minimal_world import build_world  # noqa: E402

import cognitive_ecology  # noqa: E402


# ---------------------------------------------------------------------------
# provenance: the run manifest
# ---------------------------------------------------------------------------
def _git_commit() -> str | None:
    """Best-effort commit id; None anywhere git is absent or unwed."""
    import subprocess
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
            cwd=str(Path(__file__).resolve().parents[1]),
        )
        return out.stdout.strip() if out.returncode == 0 else None
    except Exception:
        return None


def _digest(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def build_manifest(args, out_dir: str, started: float, extra: dict | None = None) -> dict:
    """Everything a future self needs to attribute these files.

    Ana's wave-1 finding: telemetry had no provenance — no seed, no
    config echo, orphaned outputs. A manifest is cheaper than a memory.
    """
    manifest = {
        "kind": "cognitive-ecology/run",
        "kernel_version": cognitive_ecology.__version__,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "git_commit": _git_commit(),
        "seed": args.seed,
        "ticks": args.ticks,
        "top_k": args.top_k,
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)),
        "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "wall_seconds": round(time.time() - started, 3),
    }
    if extra:
        manifest.update(extra)
    manifest["outputs"] = {}
    for name in sorted(os.listdir(out_dir)):
        p = os.path.join(out_dir, name)
        if os.path.isfile(p) and name != "manifest.json":
            manifest["outputs"][name] = {
                "bytes": os.path.getsize(p),
                "sha256_16": _digest(p),
            }
    return manifest


# ---------------------------------------------------------------------------
# one run
# ---------------------------------------------------------------------------
def run_one(args, out_dir: str) -> dict:
    """Run the organism; write telemetry, market log, state, manifest.

    Returns the run's key metrics (for sweep aggregation).
    """
    os.makedirs(out_dir, exist_ok=True)
    started = time.time()
    rt = build_world(args.seed)
    rt.top_k = args.top_k

    telemetry_path = os.path.join(out_dir, "telemetry.jsonl")
    with open(telemetry_path, "w", encoding="utf-8") as f:
        for report in rt.run(args.ticks):
            f.write(json.dumps(report.to_row(), sort_keys=True) + "\n")

    rt.save(out_dir)
    # the observation boundary, made durable (exact floats, no rounding)
    with open(os.path.join(out_dir, "market.jsonl"), "w", encoding="utf-8") as f:
        f.write(rt.market_log.to_jsonl())

    market = rt.market_log.summary()
    metrics = {
        "seed": args.seed,
        "actions_fired": sum(1 for r in rt.bus.log() if r.kind.name == "NOTE_ON"),
        "events": len(rt.bus),
        "live_scripts": rt.ecology.population(),
        "necrology": len(rt.ecology.necrology()),
        "clear_rate": market["clear_rate"],
        "vetoed_bids": market["vetoed"],
        "mean_winner_attention": market["mean_winner_attention"],
        "conservation_ok": rt.why.conservation()["invariant_ok"],
    }
    manifest = build_manifest(args, out_dir, started, {"metrics": metrics})
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1, sort_keys=True)
    return metrics


# ---------------------------------------------------------------------------
# sweep aggregation
# ---------------------------------------------------------------------------
def _mean_spread(values: list) -> dict:
    """Mean and spread (population stddev) of a list of numbers."""
    n = len(values)
    if n == 0:
        return {"mean": None, "spread": None, "n": 0}
    mean = sum(values) / n
    var = sum((v - mean) ** 2 for v in values) / n
    return {"mean": round(mean, 4), "spread": round(var ** 0.5, 4), "n": n}


def aggregate(per_seed: list[dict]) -> dict:
    """Cross-seed summary: which numbers are properties of the SCENARIO
    (tight spread) and which are properties of the SEED (wide spread)."""
    keys = [k for k in per_seed[0] if k != "seed"]
    out = {"seeds": [m["seed"] for m in per_seed], "metrics": {}}
    for k in keys:
        vals = [m[k] for m in per_seed]
        if all(isinstance(v, bool) for v in vals):
            out["metrics"][k] = {"all_true": all(vals), "n": len(vals)}
        elif all(isinstance(v, (int, float)) for v in vals):
            out["metrics"][k] = _mean_spread(vals)
    return out


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(description="headless rounds with telemetry")
    ap.add_argument("--ticks", type=int, default=200)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--top-k", type=int, default=2)
    ap.add_argument("--out", default="runs/rounds")
    ap.add_argument("--sweep", type=int, default=1,
                    help="run N seeds starting at --seed (one subdir each)")
    args = ap.parse_args()

    if args.sweep <= 1:
        metrics = run_one(args, args.out)
        _print_metrics(metrics, args.out)
        return

    per_seed = []
    for i in range(args.sweep):
        seed = args.seed + i
        sub = os.path.join(args.out, f"seed_{seed}")
        sub_args = argparse.Namespace(**{**vars(args), "seed": seed})
        per_seed.append(run_one(sub_args, sub))
        print(f"  seed {seed}: {per_seed[-1]['actions_fired']} actions,"
              f" clear_rate {per_seed[-1]['clear_rate']}")
    summary = {"kind": "cognitive-ecology/sweep", "ticks": args.ticks,
               "top_k": args.top_k, "aggregate": aggregate(per_seed),
               "per_seed": per_seed}
    with open(os.path.join(args.out, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=1, sort_keys=True)

    print(f"\nsweep of {args.sweep} seeds -> {args.out}/summary.json")
    for k, v in summary["aggregate"]["metrics"].items():
        if "mean" in v and v["mean"] is not None:
            print(f"  {k:24s} mean {v['mean']:>10} ± {v['spread']}")


def _print_metrics(metrics: dict, out_dir: str) -> None:
    for k, v in metrics.items():
        if k != "seed":
            print(f"{k:22s}: {v}")
    print(f"outputs      : {out_dir}/ (telemetry.jsonl, market.jsonl,"
          f" manifest.json, state.json, events.jsonl)")


if __name__ == "__main__":
    main()
