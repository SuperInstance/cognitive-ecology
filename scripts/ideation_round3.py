#!/usr/bin/env python3
"""Round 24 — ideation 016: rounds 21-23 through outside eyes.

Same cache-first dogfood shape as rounds 004b/009/015: one stable
prefix describing the wave (17-23) is sent to Hy4-preview with
different volatile suffixes, so the prefix caches across calls. Then
the typesafe decision model arbitrates which wave-2 probe runs first —
dogfooding the typed-decision seam the kernel already ships.

    PYTHONPATH=src python3 scripts/ideation_round3.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from ecology.config import Settings  # noqa: E402
from ecology.llm.base import DecisionRequest, PromptSpec  # noqa: E402
from ecology.llm.deepinfra import DeepInfraClient  # noqa: E402
from ecology.llm.ledger import Ledger  # noqa: E402
from ecology.llm.typesafe import TypeSafeClient  # noqa: E402

MODEL = "tencent/Hy4-preview"

STABLE = """You are the research director of cognitive-ecology: a kernel for agents
that persist like organisms. The DX wave (rounds 17-23, 324 tests) just
landed on top of the v0.4 kernel. What exists now:

KERNEL (v0.4.0): WHY conservation (never delete; four states; kill
cascades to UNKNOWN); re-attestation economics (liveness is a
subscription: running stamps the whole chain, freshness decays
weakest-link, unserved purposes lapse, revival lands on parole);
conservation auditor (replay basis + hash chain; tamper vectors all
caught); honest archival (cold storage, balanced books); WHY DAG
(multi-parent, best-path verdicts); outcome-arbiter (delegated
tie-break scored by realized outcomes, benchable); journal compaction;
society federation (treaties route attestation across organisms).

THE DX WAVE, just built:
- Round 17: fail-safe totality (bid()/arbiter failures degrade, never
  crash; ERROR events carry reasons). Round 18: machine-checked docs
  truth (every README count checked against the tree on every push).
- Round 20a/20b: persistence trust (atomic saves, append-only events,
  event-bus hash chain verified at load, snapshot+delta compaction).
- Round 21: the market log — an observation READ MODEL over the
  attention market: one row per bid per tick, EXACT floats (no
  rounding, bit-for-bit json roundtrips), run/yield/starved/VETOED
  statuses, veto_reasons() naming the zero factor, bounded memory
  (keep=100k), never in state.json; run manifests (seed, config,
  versions, git commit, sha256 of outputs) and seed sweeps (mean ±
  spread) in run_rounds.py.
- Round 22: host drivers — WallClockDriver (drift-free absolute-slot
  pacing, injectable clocks, graceful Ctrl-C, checkpoint cadence,
  DriverReport receipt); the pinned contract: a driver owns WHEN,
  never WHAT (driven life bit-identical to rt.run(n)); recipes for
  game loop / cron / FastAPI lifespan; rotating checkpoints; the
  world-not-bus ingest law (facts persist into the graph at ingest,
  the bus only narrates; example-04's lossy read fixed and pinned).
- Round 23: the safe seam — ensure_why/ensure_tension/ensure_component/
  ensure_script (the attach rite is idempotent; an id re-ensured with
  a different statement raises); spawn_unique (behavior signatures:
  owner+action+args+when_hint, the NAME is not the behavior; a
  rejected duplicate is a DEMOTION: counted, tailed, ERROR event the
  model itself reads, accept_rate counts spawns only so re-proposals
  starve); rest rejects non-finite amounts at the seam, kernel no-ops
  them.

WAVE-1 LEDGER (six personas, verdict PILOT 6.5-7/10): items 1, 2, 5
closed (fail-safes, persistence trust, stale numbers); items 3, 4, 6,
7, 8, 9 closed by rounds 21-23 as described. NOT yet done: the
physiology round (OQ #15: resource envelope, health surface, tick
duration contract — deliberately deferred); ScriptedProvider for CI;
one-shot search scripts never starving; prefix stability advisory not
enforced.

WHAT'S NEXT: wave-2 — fresh personas re-play-test the whole wave to
verify the fixes landed AS EXPERIENCED, not just as tests."""


def main() -> int:
    settings = Settings.from_env()
    ledger = Ledger(REPO / settings.ledger_path)
    chat = DeepInfraClient(settings, ledger=ledger)

    # -- call 1: red-team the wave ------------------------------------
    ask1 = (
        "Red-team rounds 21-23. Name the THREE sharpest holes in what "
        "was just built (not the deferred physiology — holes in what "
        "SHIPPED): where would the read model lie, where would a driver "
        "break its own contract, where does the safe seam still leak? "
        "For each: the concrete failure scenario, the user it hits, and "
        "the pinning test that would catch it. <= 300 words."
    )
    r1 = chat.complete(PromptSpec(stable_prefix=STABLE, variable_suffix=ask1,
                                  max_tokens=1400, temperature=0.7),
                       MODEL, role="ideation3-redteam")

    # -- call 2: cast wave-2 (same prefix = cache hit) ------------------
    ask2 = (
        "Cast the wave-2 play-test: SIX fresh personas (different people "
        "from wave-1's Sam/Priya/Morgan/Kai/Ana/Dana), each carrying a "
        "checklist that ties one probe to one fix: exactly what to do, "
        "what 'landed' looks like, what 'regressed' looks like. Cover: "
        "the market log + manifests + sweeps, the drivers + ingest law, "
        "the ensure_* rite + duplicate demotions, persistence trust, "
        "fail-safes, and the docs/truth gate. <= 350 words."
    )
    r2 = chat.complete(PromptSpec(stable_prefix=STABLE, variable_suffix=ask2,
                                  max_tokens=1500, temperature=0.7),
                       MODEL, role="ideation3-cast")

    cost = (r1.usage.cost_usd or 0.0) + (r2.usage.cost_usd or 0.0)
    cached = r1.usage.cached_tokens + r2.usage.cached_tokens
    print(f"redteam : {r1.latency_ms}ms, {r1.usage.prompt_tokens}in "
          f"({r1.usage.cached_tokens} cached), ${r1.usage.cost_usd:.6f}")
    print(f"cast    : {r2.latency_ms}ms, {r2.usage.prompt_tokens}in "
          f"({r2.usage.cached_tokens} cached), ${r2.usage.cost_usd:.6f}")

    # -- call 3: the typesafe arbiter ranks the probes ------------------
    jev = TypeSafeClient(settings, ledger=ledger)
    probes = {
        "A_read_model": "run 300 ticks, load market.jsonl in pandas, "
                        "verify veto_reasons names real zero factors, "
                        "re-run a sweep and diff manifests",
        "B_driver_contract": "drive minimal_world 40 ticks via "
                             "WallClockDriver with a fake and a real "
                             "clock; diff event streams vs rt.run(40); "
                             "try the FastAPI recipe verbatim",
        "C_safe_seam": "re-attach an organism three times (fresh, "
                       "post-load, post-hot-reload); re-propose a "
                       "duplicate 5x; watch accept_rate and population",
        "D_persistence": "kill -9 mid-save; tamper events.jsonl; compact "
                         "at tick 200 and replay to 300; verify "
                         "bit-identity and door refusals",
        "E_docs_truth": "clone cold, follow README quickstart verbatim, "
                        "then deliberately rot one count and expect CI "
                        "to fail; run every example keyless",
        "F_ingest_law": "port example-04's OLD bus-read pattern into a "
                        "fresh app, observe the ask loss, then apply the "
                        "world-not-bus law and observe the fix",
    }
    state = (
        "cognitive-ecology wave-2 planning. Six candidate probes verify "
        "the DX wave (rounds 17-23) landed as experienced. Engineering "
        "capacity: 3 probes this round. The strongest wave-2 signal "
        "comes from probes a REAL user would run unprompted, that "
        "regress loudly when wrong, and that no existing test already "
        "covers."
    )
    (qname, question) = TypeSafeClient.choice(
        "first_probe",
        "Which single probe should run FIRST in wave-2? (Choose by user-"
        "realism x regression-loudness x test-coverage gap.)",
        probes,
    )
    (q2name, question2) = TypeSafeClient.score(
        "coverage_gaps",
        "How much of the wave's risk surface do the six probes cover, "
        "as a set?",
        ["thin — major shipped surface unprobed",
         "partial — notable gaps remain",
         "solid — the shipped surface is probed",
         "overcovered — probes overlap existing tests"],
    )
    resp = jev.decide(
        DecisionRequest(state=state,
                        questions={qname: question, q2name: question2}),
        role="wave2-arbiter",
    )
    first = resp.answers[qname].value
    cover = resp.answers[q2name].value
    print(f"jev     : first_probe={first[0]}, coverage={cover[0]} "
          f"(conf {first[1]})")

    # -- write the round receipt ----------------------------------------
    out = REPO / "library" / "rounds" / "016-wave2-through-outside-eyes.md"
    out.write_text(
        "# Round 24 — ideation 016: rounds 21-23 through outside eyes\n\n"
        f"*Run: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} — "
        f"{MODEL} x2 (cache-first, ${cost:.6f}, {cached} cached tokens) "
        f"+ typesafe jev (wave2-arbiter).*\n\n"
        "## I. Red-team of rounds 21-23\n\n" + r1.text.strip()
        + "\n\n## II. The wave-2 cast\n\n" + r2.text.strip()
        + "\n\n## III. The arbiter's call (typesafe)\n\n"
        f"- first_probe: **{first[0]}** (confidence {first[1]})\n"
        f"- probe-set coverage: **{cover[0]}** (confidence {cover[1]})\n"
        f"- probes under consideration: {', '.join(sorted(probes))}\n"
        "\n---\n*Triage: see JOURNAL round 24.*\n",
        encoding="utf-8",
    )
    print(f"written: {out}")
    ledger.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
