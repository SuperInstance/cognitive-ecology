#!/usr/bin/env python3

"""Round 4 — the re-attestation economics under attack (live dogfood).

Directive: dogfood tencent/Hy4-preview with concepts for ideation and
expansion, gaming the provider cache. So this round is ONE cheap model,
adversarial, cache-first:

  * a LARGE stable prefix (the architecture digest + ADR-0007 verbatim)
    is sent identically every call — that is what the cache holds;
  * the transcript grows APPEND-ONLY, so each call's genuinely new input
    is only the increment; prompt_cache_key pins the routing;
  * between iterations, jev (typesafe.ai) gates the loop with typed,
    calibrated questions: attack again, repair, or concede.

The question: where does the re-attestation economics BREAK? Gaming
vectors, degenerate equilibria, self-dealing components, cold starts.

    PYTHONPATH=src python3 scripts/reattestation_round.py
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

STABLE = """You are the red team of a research program: cognitive-ecology, a kernel
for agents that persist like organisms. Its conservation law: a WHY node
(purpose) is never deleted; states are ALIVE / DEAD / UNKNOWN / ABSENT;
killing cascades living descendants to UNKNOWN (questionable, revivable);
every transition lands in an append-only necrology.

The newest mechanic, ADR-0007 (v0.3), makes liveness a subscription:

1. USE IT — when a component wins the attention market and acts, the
   runtime stamps heartbeats along its ENTIRE WHY chain (transitive to
   the root). Serving a purpose maintains its whole lineage.
2. LOSE IT — justification() multiplies the alive-fraction of the chain
   by weakest-link freshness: full through the first third of the
   horizon (grace window), then linear decay to zero at the horizon.
   Stale purposes bid progressively weaker and lose contention.
3. LAPSE — an ALIVE node unattested longer than the horizon flips to
   UNKNOWN ("lapsed") at the periodic conservation audit (every 25
   ticks). Lapse is per-node (no cascade). Recorded, never deleted.
4. REVIVE — only an explicit revive(reason) restores a lapsed purpose,
   buying a fresh horizon. Play-tested result: revival WITHOUT service
   buys exactly one more horizon, then it lapses again; revival WITH
   service holds.

Attention bids are multiplicative: attention = urgency * justification *
opportunity * novelty * expected_value; any zero factor vetoes the bid.
The whole organism is deterministic, tick-based, zero-LLM by default.

Your job: find where this BREAKS."""

TASK = """Attack the re-attestation economics. Hunt specifically for:
(a) gaming vectors — how does a self-interested component keep a purpose
fresh WITHOUT genuinely serving it (empty actions? cheap loop bids?
mutual back-scratching between components stamping each other's chains?);
(b) degenerate equilibria — parameter regimes (horizon, grace, cadence)
where the market goes pathological;
(c) cold start — a newborn organism or a resurrected root with nothing
serving it yet;
(d) anything the design team has not thought of.

Each iteration: ATTACK (the sharpest new hole, concretely) then REPAIR
(the minimal fix, naming the module it lands in). <= 200 words total.
Escalate precision; do not repeat an earlier iteration's hole."""


def main() -> int:
    settings = Settings.from_env()
    ledger = Ledger(REPO / settings.ledger_path)
    chat = DeepInfraClient(settings, ledger=ledger)
    jev = TypeSafeClient(settings, ledger=ledger)

    history: list[str] = []
    gates: list[dict] = []
    cost = 0.0
    prompt_tokens = cached_tokens = 0

    prompt = STABLE
    suffix = TASK
    for i in range(1, 5):
        spec = PromptSpec(
            stable_prefix=prompt,
            variable_suffix=suffix + "\n\nWrite iteration now.",
            max_tokens=700,
            temperature=0.7,
        )
        response = chat.complete(spec, MODEL, role="reattestation-redteam")
        cost += response.usage.cost_usd or 0.0
        prompt_tokens += response.usage.prompt_tokens
        cached_tokens += response.cache_hit_tokens
        history.append(response.text.strip())
        print(
            f"iteration {i}: {response.latency_ms}ms, "
            f"{response.usage.prompt_tokens}in "
            f"({response.cache_hit_tokens} cached), "
            f"${(response.usage.cost_usd or 0):.5f}"
        )

        if i == 4:
            break
        name_q, q1 = TypeSafeClient.choice(
            "steer",
            "The red team has one more iteration. Steer it.",
            {
                "attack": "A bigger hole remains — attack again, deeper",
                "repair": "The holes found are real — switch to repairing them",
                "concede": "The design holds — say so and rank what remains",
            },
        )
        name_s, q2 = TypeSafeClient.score(
            "severity",
            "How severe is the most severe UNREPAIRED hole in the design?",
            ["trivial", "moderate", "serious", "design-breaking"],
        )
        gate = jev.decide(
            DecisionRequest(
                state={"iteration": i, "last_output": history[-1][:4000]},
                questions={name_q: q1, name_s: q2},
            ),
            role="reattestation-gate",
        )
        steer = gate.answers["steer"].value
        severity = gate.answers["severity"].value
        gates.append({"iteration": i, "steer": steer, "severity": severity})
        cost += gate.usage.cost_usd or 0.0
        print(f"  gate: steer={steer} severity={severity}")

        if isinstance(steer, tuple) and steer[0] == "repair":
            nudge = "The gate says the holes found are real: REPAIR them."
        elif isinstance(steer, tuple) and steer[0] == "concede":
            nudge = (
                "The gate says the design holds: CONCEDE and rank the "
                "remaining holes by severity."
            )
        else:
            nudge = "The gate says a bigger hole remains: ATTACK again."
        # append-only growth: everything said so far stays in the prompt
        prompt = STABLE + "\n\nTRANSCRIPT OF YOUR ITERATIONS:\n" + \
            "\n---\n".join(history)
        suffix = f"ITERATION {i + 1}. {nudge}"

    lines = [
        "# Round 4 — the re-attestation economics under attack",
        "",
        f"*Run: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} — "
        f"{MODEL} red-teaming ADR-0007, gated by jev. "
        f"Cost ${cost:.6f}; {prompt_tokens} prompt tokens "
        f"({cached_tokens} cached, {100 * cached_tokens / max(1, prompt_tokens):.0f}% "
        f"cache hit).*",
        "",
        "## Iterations",
        "",
    ]
    for i, text in enumerate(history, 1):
        lines += [f"### iteration {i}", "", text, ""]
    if gates:
        lines += ["## Decision gates (jev)", ""]
        for g in gates:
            lines.append(
                f"- after iteration {g['iteration']}: steer={g['steer']} "
                f"severity={g['severity']}"
            )
        lines.append("")
    lines.append("---\n"
                 f"*Recorded cost: ${cost:.6f}. "
                 "Build actions taken in response: see JOURNAL round 4.*")

    out = REPO / "library" / "rounds" / "004-reattestation-under-attack.md"
    out.write_text("\n".join(lines))
    print(f"written: {out}  cost: ${cost:.6f}")
    ledger.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
