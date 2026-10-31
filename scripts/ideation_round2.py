#!/usr/bin/env python3

"""Round 9 — ideation against the EXPANDED kernel (v0.3 complete).

Same cache-first dogfood shape as round 004b, but the stable prefix now
describes everything v0.3 built. The output is the v0.4 frontier: what
survives triage becomes the roadmap.

    PYTHONPATH=src python3 scripts/ideation_round2.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from ecology.config import Settings  # noqa: E402
from ecology.llm.base import PromptSpec  # noqa: E402
from ecology.llm.deepinfra import DeepInfraClient  # noqa: E402
from ecology.llm.ledger import Ledger  # noqa: E402

MODEL = "tencent/Hy4-preview"

STABLE = """You are the research director of cognitive-ecology: a kernel for agents
that persist like organisms. State as of v0.3 (all built, 179 tests):

- WHY conservation law: purpose nodes are never deleted; four states;
  kills cascade to UNKNOWN; append-only necrology.
- Re-attestation economics: liveness is a subscription — running stamps
  the whole WHY chain; justification decays by weakest-link freshness;
  unserved purposes lapse to UNKNOWN; revival lands on PAROLE
  (justification capped 0.5 until genuinely served again).
- Conservation auditor: genesis + necrology + attestation journal replay
  to exactly the living tree; receipts carry digests and a hash chain
  over the whole basis; saved organisms vouch for themselves; every
  tamper vector is caught (flip, edit, remove, reorder, forge, drop).
- Honest archival: ancient DEAD subtrees sweep to cold storage; books
  stay balanced (hot + cold == ever declared); the manifest is verified
  by the auditor; restoration is a recorded two-act ceremony.
- Attention market: multiplicative bids, veto law (zero factor vetoes),
  optional delegated tie-break to a calibrated decision model (one
  bounded choice; vetoed bids never reach it; failures degrade to the
  deterministic shadow); divergence from the shadow is counted telemetry.
- Calibration: bids may claim success probabilities; the runtime scores
  every claim (Brier, reliability bins, per component) — an overconfident
  component is measurably dishonest from the organism's own receipts.
- Soak-proven: 10k ticks with verification every 1k, 2.3k ticks/s,
  archival engaged, zero invariant failures, disk round-trips verified.
- Still open on the ledger: multi-parent WHY (DAG), smarter factor
  estimators, sleep scheduling triggers, multi-organism societies,
  real-time tick sources, script speciation, persistence benchmarks,
  journal compaction, outcome-weighted arbiter scoring."""


def main() -> int:
    settings = Settings.from_env()
    ledger = Ledger(REPO / settings.ledger_path)
    chat = DeepInfraClient(settings, ledger=ledger)

    ask = (
        "Propose the v0.4 frontier: the THREE highest-value directions, "
        "ranked. For each: (1) what to build, concretely, named module; "
        "(2) which open question it closes; (3) the sharpest pinning test; "
        "(4) the falsifier. One of the three must be about MULTI-ORGANISM "
        "societies (the ledger's biggest hole) unless you argue convincingly "
        "it is still premature. Be specific to THIS kernel. <= 400 words."
    )
    spec = PromptSpec(stable_prefix=STABLE, variable_suffix=ask,
                      max_tokens=900, temperature=0.7)
    r = chat.complete(spec, MODEL, role="ideation2")
    cost = r.usage.cost_usd or 0.0
    print(f"ideation2: {r.latency_ms}ms, {r.usage.prompt_tokens}in "
          f"({r.cache_hit_tokens} cached), ${cost:.5f}")

    out = REPO / "library" / "rounds" / "009-ideation-v04-frontier.md"
    out.write_text(
        "# Round 9 — ideation: the v0.4 frontier\n\n"
        f"*Run: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} — "
        f"{MODEL}, cache-first, ${cost:.6f}. Stable prefix describes the "
        f"complete v0.3 kernel.*\n\n## Proposal\n\n"
        + r.text.strip()
        + "\n\n---\n*Triage: see JOURNAL round 9.*\n"
    )
    print(f"written: {out}")
    ledger.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
