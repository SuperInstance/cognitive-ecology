#!/usr/bin/env python3

"""Ideation leg — dogfood Hy4-preview for expansion directions (round 004b).

Same cache-first shape as the red-team round: one stable prefix (the
architecture digest), one ask. The output feeds the next build rounds:
whatever survives triage becomes a round of work.

    PYTHONPATH=src python3 scripts/ideation_round.py
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
that persist like organisms. Current state (v0.3-in-progress):

- WHY conservation law: purpose nodes are never deleted; four states
  (ALIVE/DEAD/UNKNOWN/ABSENT); kills cascade descendants to UNKNOWN;
  append-only necrology records every transition.
- Re-attestation economics (new): liveness is a subscription — running
  under a purpose stamps its whole chain; justification decays by
  weakest-link freshness; unserved purposes lapse to UNKNOWN; revival
  lands on parole (justification capped 0.5 until truly served).
- Attention market: multiplicative bids (urgency * justification *
  opportunity * novelty * expected_value); zero factor vetoes; top-k
  clearing; executive resolves resource conflicts.
- Script ecology: candidate -> active -> retired by learned utility;
  dreams mutate parameters; starvation deaths recorded in a necrology.
- Sleep: idle organisms replay events into the world graph and prune.
- Anti-RAG world graph: append/decay only, no deletion; digests are
  cache-stable (statements, not states).
- LLM teachers are citizens: they enter the same market under the same
  WHY gate (Hy4-preview default), cache-first prompting.
- Zero-dependency kernel, 143 tests, deterministic, tick-based.

Open questions already on the ledger: multi-parent WHY (DAG), smarter
attention estimators, decision-model integration boundary (typed
calibrated choices), sleep scheduling triggers, multi-organism societies,
honest archival of ancient DEAD nodes, real-time tick sources, script
speciation, a persistence benchmark, proposer homeostasis, a formal
conservation statement."""


def main() -> int:
    settings = Settings.from_env()
    ledger = Ledger(REPO / settings.ledger_path)
    chat = DeepInfraClient(settings, ledger=ledger)

    ask = (
        "Propose the THREE next build rounds (v0.3), ranked by value/risk. "
        "For each: (1) what to build, concretely, named module; (2) which "
        "open question it advances or closes; (3) the single sharpest test "
        "that would pin its semantics; (4) the failure mode that would "
        "falsify the approach. Be specific to THIS kernel — no generic "
        "agent-framework advice. <= 400 words."
    )
    spec = PromptSpec(
        stable_prefix=STABLE, variable_suffix=ask,
        max_tokens=900, temperature=0.7,
    )
    r = chat.complete(spec, MODEL, role="ideation")
    cost = r.usage.cost_usd or 0.0
    print(f"ideation: {r.latency_ms}ms, {r.usage.prompt_tokens}in "
          f"({r.cache_hit_tokens} cached), ${cost:.5f}")

    out = REPO / "library" / "rounds" / "004b-ideation-next-rounds.md"
    out.write_text(
        "# Round 4b — ideation: the next build rounds\n\n"
        f"*Run: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} — "
        f"{MODEL}, cache-first, ${cost:.6f}.*\n\n## Proposal\n\n"
        + r.text.strip()
        + "\n\n---\n*Triage: see JOURNAL.*\n"
    )
    print(f"written: {out}")
    ledger.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
