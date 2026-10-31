#!/usr/bin/env python3
"""Wave-2 play-test probes (rounds 17-23 verified as EXPERIENCED).

The repeatable harness behind JOURNAL round 25: five personas'
checklists, executed mechanically against a COLD CLONE of this repo
(fresh venv, editable install, no help from the test suite). Each
check prints LANDED or REGRESSED; the exit code is the wave's verdict.

    # once: clone + venv + install
    git clone <repo> /tmp/wave2/cold && cd /tmp/wave2/cold
    python -m venv /tmp/wave2/venv
    /tmp/wave2/venv/bin/pip install -e ".[dev]"

    # then: the wave
    python scripts/playtest_wave2.py --clone /tmp/wave2/cold \\
        --python /tmp/wave2/venv/bin/python

Probe B needs fastapi + uvicorn in the target environment (dev extras
include fastapi). The clone is never modified except by its own runs/
outputs. Keyless throughout. Findings from the first run live in
JOURNAL round 25; the FastAPI recipe bug it found is fixed and pinned
by tests/test_host_recipes.py.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO: Path = Path(".")          # set by main()
VENV_PY: str = sys.executable   # set by main()
RUNS: Path = Path(".")          # set by main()
FAILS: list = []


def check(name: str, ok: bool, detail: str = "") -> None:
    tag = "LANDED  " if ok else "REGRESSED"
    print(f"  {tag} {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        FAILS.append(name)


def _py(code: str, timeout: int = 120) -> subprocess.CompletedProcess:
    """Run python code inside the clone (repo root + src on path)."""
    boot = ("import sys; sys.path.insert(0, %r); sys.path.insert(0, %r)\n"
            % (str(REPO), str(REPO / "src")))
    return subprocess.run([VENV_PY, "-c", boot + code],
                          cwd=str(REPO), capture_output=True, text=True,
                          timeout=timeout)


# ---------------------------------------------------------------------------
# Probe A (Noor): sweeps, manifests, exact floats
# ---------------------------------------------------------------------------
def probe_a() -> None:
    print("== Probe A (Noor): sweeps, manifests, exact floats ==")
    r = subprocess.run(
        [VENV_PY, "scripts/run_rounds.py", "--ticks", "80", "--sweep", "3",
         "--seed", "50", "--out", str(RUNS / "sweep")],
        cwd=str(REPO), capture_output=True, text=True, timeout=300)
    check("A1 sweep runs", r.returncode == 0,
          r.stdout.strip().splitlines()[-1] if r.returncode == 0
          else r.stderr[-200:])
    man = json.loads((RUNS / "sweep" / "seed_50" / "manifest.json").read_text())
    check("A2 manifest provenance",
          all(k in man for k in ("kernel_version", "python", "git_commit",
                                 "seed", "outputs"))
          and all("sha256_16" in v for v in man["outputs"].values()))
    mkt = [json.loads(l) for l in
           (RUNS / "sweep" / "seed_50" / "market.jsonl").read_text()
           .splitlines() if l.strip()]
    bids = [row for row in mkt if row.get("kind") == "bid"]
    check("A3 market rows exist", len(bids) > 50, f"{len(bids)} rows")
    statuses = {row["status"] for row in bids}
    check("A4 statuses from the market's vocabulary",
          statuses <= {"run", "yield", "starved", "vetoed"},
          str(sorted(statuses)))
    summary = _py(
        "from experiments.minimal_world import build_world\n"
        "rt = build_world(9); rt.run(60)\n"
        "s = rt.market_log.summary()\n"
        "print(s['clear_rate'] > 0, 'dropped_rows' in s, 'first_tick' in s)")
    check("A5 summary carries tail honesty",
          "True True True" in summary.stdout,
          summary.stdout.strip() or summary.stderr[-120:])


# ---------------------------------------------------------------------------
# Probe B (Mateo): driver contract + the FastAPI recipe, LIVE
# ---------------------------------------------------------------------------
def probe_b() -> None:
    print("== Probe B (Mateo): driver contract + FastAPI recipe live ==")
    contract = _py(
        "from experiments.minimal_world import build_world\n"
        "from cognitive_ecology import WallClockDriver\n"
        "driven, plain = build_world(4), build_world(4)\n"
        "WallClockDriver(0.001).run(driven, max_ticks=40)  # REAL clock\n"
        "plain.run(40)\n"
        "print('IDENTICAL' if driven.bus.to_jsonl() == plain.bus.to_jsonl()\n"
        "      else 'DIVERGED')")
    check("B1 real-clock driver is bit-identical to rt.run",
          "IDENTICAL" in contract.stdout,
          contract.stdout.strip() or contract.stderr[-160:])

    # the docs/10 recipe app (async-native), served by uvicorn, hit by curl
    (RUNS / "recipe_app.py").write_text('''
import asyncio, sys, time
from contextlib import asynccontextmanager
sys.path.insert(0, {repo!r} + "/src")
from fastapi import FastAPI
from cognitive_ecology import Runtime, Script
from cognitive_ecology.scripts import Outcome

rt = Runtime()
rt.declare_why("serve the web", node_id="why:web")
rt.tensions.add("questions", growth=0.4)

class Desk:
    id = "desk"; why_node = "why:web"
    def bid(self, ctx): return ctx.ecology.bids(ctx, owner="desk")
    def act(self, ctx, label): return ctx.ecology.fire(label, ctx)

rt.register(Desk())
rt.ecology.spawn(Script(name="answer", why_node="why:web", owner="desk",
                        relieves=("questions",),
                        act=lambda ctx: Outcome(True, "ok")), tick=0)
TICK_INTERVAL = 0.01

async def organism_loop(stop_after=30.0):
    end = time.monotonic() + stop_after
    while time.monotonic() < end:
        rt.tick()                          # async-native: the fixed recipe
        await asyncio.sleep(TICK_INTERVAL)

@asynccontextmanager
async def lifespan(app):
    task = asyncio.create_task(organism_loop())
    yield
    task.cancel()

app = FastAPI(lifespan=lifespan)

@app.post("/ask")
def ask(text: str):
    qid = "question:" + str(abs(hash(text)))[:8]
    rt.graph.upsert(qid, "question", {{"text": text}}, tick=rt.tick_no)
    rt.graph.link("user:web", qid, "asked", tick=rt.tick_no)
    return {{"ok": True, "tick": rt.tick_no}}

@app.get("/state")
def state():
    return {{"tick": rt.tick_no, "market": rt.market_log.summary(),
            "tensions": rt.tensions.snapshot()}}
'''.replace("{repo!r}", repr(str(REPO))).replace("{{", "{").replace("}}", "}"),
        encoding="utf-8")
    port = "8137"
    proc = subprocess.Popen(
        [VENV_PY, "-m", "uvicorn", "recipe_app:app", "--port", port],
        cwd=str(RUNS), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        deadline = time.monotonic() + 10
        up = False
        while time.monotonic() < deadline:
            time.sleep(0.25)
            probe = subprocess.run(
                ["curl", "-sf", f"http://127.0.0.1:{port}/state"],
                capture_output=True, text=True, timeout=5)
            if probe.returncode == 0:
                up = True
                break
        check("B2 the recipe serves at all (startup completes)", up,
              "the async-native loop must not block the event loop")
        if up:
            a = subprocess.run(
                ["curl", "-sf", "-X", "POST",
                 f"http://127.0.0.1:{port}/ask?text=hello+organism"],
                capture_output=True, text=True, timeout=5).stdout
            s = subprocess.run(
                ["curl", "-sf", f"http://127.0.0.1:{port}/state"],
                capture_output=True, text=True, timeout=5).stdout
            check("B3 /ask ingests, /state reads the read model",
                  '"ok"' in a and '"tick"' in s and '"clear_rate"' in s,
                  s[:80])
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


# ---------------------------------------------------------------------------
# Probe C (Ines): the rite three times, demotions paid
# ---------------------------------------------------------------------------
def probe_c() -> None:
    print("== Probe C (Ines): the rite twice, demotions paid ==")
    seam = _py("""
from cognitive_ecology import Runtime, Script
from cognitive_ecology.scripts import Outcome

rt = Runtime()
def attach():
    rt.ensure_why("serve", node_id="why:root")
    rt.ensure_why("answer", parent="why:root", node_id="why:desk")
    rt.ensure_tension("questions", growth=0.3)
    rt.ensure_script(Script(name="answer", why_node="why:desk", owner="desk",
                            relieves=("questions",),
                            act=lambda ctx: Outcome(True, "ok")))
attach(); attach(); attach()          # the rite, three times
print("RITE_OK", rt.ecology.population() == 1, len(rt.why.nodes()) == 2)
try:
    rt.ensure_why("a DIFFERENT purpose", node_id="why:root")
    print("MISMATCH_RAISED False")
except ValueError:
    print("MISMATCH_RAISED True")
rt.ensure_why("agent purpose", parent="why:root", node_id="why:agent")
for i in range(5):
    p = {"action": "observe", "args": {"focus": ["b:1"]},
         "when_hint": "always"}
    rt.ecology.spawn_unique(Script(name=f"clone-{i}", why_node="why:agent",
                                   owner="agent", params=p,
                                   act=lambda ctx: Outcome(True, "x")))
print("DEMOTIONS", rt.ecology.duplicates_rejected == 4,
      rt.ecology.population() == 2)
""")
    out = seam.stdout
    check("C1 rite runs three times painlessly", "RITE_OK True True" in out)
    check("C2 statement mismatch raises", "MISMATCH_RAISED True" in out)
    check("C3 five re-proposals -> four demotions, one script",
          "DEMOTIONS True True" in out,
          out.strip().replace("\n", " | ") or seam.stderr[-160:])


# ---------------------------------------------------------------------------
# Probe D (Yuki): SIGKILL mid-save, tamper, compaction
# ---------------------------------------------------------------------------
def probe_d() -> None:
    print("== Probe D (Yuki): kill -9 mid-life, tamper, compact ==")
    killer = RUNS / "killer.py"
    killer.write_text(f"""
import sys
sys.path.insert(0, {str(REPO)!r}); sys.path.insert(0, {str(REPO / 'src')!r})
from experiments.minimal_world import build_world
rt = build_world(31)
for i in range(400):
    rt.tick()
    rt.save({str(RUNS / 'killed')!r})     # save in a hot loop
""", encoding="utf-8")
    proc = subprocess.Popen([VENV_PY, str(killer)],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
    time.sleep(1.5)                # several saves have landed
    proc.kill()                    # SIGKILL: no atexit, no cleanup
    proc.wait()
    door = _py(f"""
from cognitive_ecology import Runtime
try:
    rt = Runtime.load({str(RUNS / 'killed')!r}, attach=lambda r: None)
    print('LOADED tick', rt.tick_no)
except Exception as exc:
    print('REFUSED', type(exc).__name__, str(exc)[:80])
""")
    check("D1 kill -9 leaves a loadable checkpoint (or an honest refusal)",
          door.stdout.startswith(("LOADED", "REFUSED")),
          door.stdout.strip() or door.stderr[-160:])

    subprocess.run([VENV_PY, "-c", f"""
import sys
sys.path.insert(0, {str(REPO)!r}); sys.path.insert(0, {str(REPO / 'src')!r})
from experiments.minimal_world import build_world
rt = build_world(31); rt.run(30); rt.save({str(RUNS / 'tampered')!r})
"""], capture_output=True, timeout=120)
    ev = RUNS / "tampered" / "events.jsonl"
    lines = [l for l in ev.read_text().splitlines() if l.strip()]
    obj = json.loads(lines[5])
    obj[3] = "tamperer"           # event rows are lists: [seq,kind,ts,src,...]
    lines[5] = json.dumps(obj, separators=(",", ":"))
    ev.write_text("\n".join(lines) + "\n")
    tam = _py(f"""
from cognitive_ecology import Runtime
try:
    Runtime.load({str(RUNS / 'tampered')!r}, attach=lambda r: None)
    print('BOOTED_SILENTLY')
except Exception:
    print('REFUSED')
""")
    check("D2 tampered events are refused at the door",
          "REFUSED" in tam.stdout,
          tam.stdout.strip() or tam.stderr[-160:])

    comp = _py(f"""
from experiments.minimal_world import build_world
a = build_world(31)
for _ in range(200): a.tick()
a.compact_events({str(RUNS / 'compactA')!r}, keep=500)
for _ in range(100): a.tick()
b = build_world(31)
for _ in range(300): b.tick()
# the 015/20b contract: the LIVES and the BOOKS are identical (the
# event FILE is legitimately truncated — storage-only, not behavior)
same = (a.graph.digest() == b.graph.digest()
        and a.audit().live_digest == b.audit().live_digest
        and a.why.necrology() == b.why.necrology()
        and a.tensions.snapshot() == b.tensions.snapshot())
print('BIT_IDENTICAL', same)
""")
    check("D3 compact at 200 + run to 300 keeps lives and books identical",
          "BIT_IDENTICAL True" in comp.stdout,
          comp.stdout.strip() or comp.stderr[-160:])


def run_probes() -> int:
    probe_a()
    probe_b()
    probe_c()
    probe_d()
    print()
    if FAILS:
        print(f"WAVE-2 A-D: {len(FAILS)} REGRESSED -> {FAILS}")
        return 1
    print("WAVE-2 A-D: all LANDED")
    return 0


def main() -> int:
    global REPO, VENV_PY, RUNS
    ap = argparse.ArgumentParser(description="wave-2 play-test probes")
    ap.add_argument("--clone", required=True, help="path to a cold clone")
    ap.add_argument("--python", default=sys.executable,
                    help="python of the clone's venv")
    ap.add_argument("--runs", default=None,
                    help="output dir (default: a fresh tempdir)")
    args = ap.parse_args()
    REPO = Path(args.clone).resolve()
    VENV_PY = args.python
    RUNS = (Path(args.runs).resolve() if args.runs
            else Path(tempfile.mkdtemp(prefix="wave2-")))
    RUNS.mkdir(parents=True, exist_ok=True)
    print(f"clone : {REPO}")
    print(f"python: {VENV_PY}")
    print(f"runs  : {RUNS}\n")
    return run_probes()


if __name__ == "__main__":
    sys.exit(main())
