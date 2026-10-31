#!/usr/bin/env python3
"""Round 11 — the society-basis federation under attack (live dogfood).

Same adversarial cache-first shape as round 004 (which attacked
ADR-0007 and won two fixes): ONE cheap model (tencent/Hy4-preview),
a large stable prefix describing ADR-0011 verbatim-ish, an APPEND-ONLY
transcript so each call's new input is only the increment, and jev
(typesafe.ai) gating the loop with typed questions between iterations.

The question: where does WHY federation BREAK? Treaty washing, mutual
back-scratching societies, question() as an intra-organism weapon,
sole_basis evasion, auditor blind spots.

    PYTHONPATH=src python3 scripts/society_round.py
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
for agents that persist like organisms. Its first law: a WHY (purpose)
node is never deleted; states are ALIVE / DEAD / UNKNOWN / ABSENT;
every transition lands in an append-only necrology; a conservation
auditor replays genesis + necrology + attestation journal to exactly
the living tree.

The newest mechanic, ADR-0011 (v0.4), is SOCIETY-BASIS federation:

1. TREATY — a foreign purpose reference: beneficiary A's node `a` is
   served by provider B's node `b`. Append-only ledger (active ->
   broken | revoked, never back, never deleted). At most one ACTIVE
   sole treaty per beneficiary node ("served only by" cannot be said
   twice). Both endpoints must be ALIVE at establishment.
2. THE EXCHANGE — treaties route attestation, nothing else. When B's
   runtime stamps B's provider chain (a component under `b` won the
   attention market), the society re-stamps A's beneficiary chain ON
   A'S OWN BOOKS with provenance `treaty:<id>`. A's existing economics
   does the enforcing: routed stamps keep A's chain fresh; sparse
   service decays A's bids; with a horizon, neglect lapses the node on
   A's own books (the SOFT path).
3. HARD PROPAGATION — B's provider node transitioning to DEAD or
   UNKNOWN breaks the treaty and, if the treaty was the node's sole
   basis, QUESTIONS A's node: a new public transition question(nid,
   reason) -> ALIVE to UNKNOWN, recorded, no cascade, revivable by
   A's own revive(reason) (which lands on parole, justification capped
   0.5 until genuinely served). The question record + an EXCHANGE
   event on both buses are the exchange receipts.
4. BOTH-ENDS-ALIVE — A's beneficiary dying/killed/archived breaks the
   treaty too. A may revive and establish a NEW treaty, or serve the
   purpose locally (the node was always A's).
5. FEDERATION AUDITOR — ledger append-only (contiguous ids); no ACTIVE
   treaty with a dead endpoint; every treaty-provenance stamp on a
   beneficiary's journal must match a provider stamp on the provider
   node at the same tick (forged service detectable); provider-side
   sole breaks must have their question() receipt; each member's own
   books balance. Plus a hash chain over the ledger.
6. MECHANICS — Society.step() ticks members in lockstep (join order),
   then one exchange. Delegation flows ONE HOP per exchange
   (cycle-safe). The exchange consumes only frozen log slices.
7. NOTE — question() is a PUBLIC method on WhyTree. The runtime never
   calls it; the society does. Components receive a WorldSnapshot that
   exposes the live WhyTree object.

Attention bids are multiplicative: attention = urgency * justification
* opportunity * novelty * expected_value; any zero factor vetoes.
Everything is deterministic, tick-based, zero-LLM by default.

Your job: find where this BREAKS."""

TASK = """Attack the society-basis federation. Hunt specifically for:
(a) treaty washing — cheap establish/break/re-establish cycles; does
revive-then-new-treaty ever beat honest service on cost?
(b) mutual back-scratching — two organisms treaty each other's nodes
into permanent freshness without anything real being done; is a
service loop between A and B distinguishable from genuine delegation?
(c) question() as a weapon — it is public; who else can call it, and
what should the books record about WHO doubted?
(d) sole_basis evasion — non-sole stacking to dodge hard propagation;
(e) auditor blind spots — what cross-organism lie still passes all
five checks?
(f) anything the design team has not thought of.

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
        response = chat.complete(spec, MODEL, role="society-redteam")
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
            role="society-gate",
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
        "# Round 11 — the society-basis federation under attack",
        "",
        f"*Run: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} — "
        f"{MODEL} red-teaming ADR-0011, gated by jev. "
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
                 "Build actions taken in response: see JOURNAL round 11.*")

    out = REPO / "library" / "rounds" / "011-society-under-attack.md"
    out.write_text("\n".join(lines))
    print(f"written: {out}  cost: ${cost:.6f}")
    ledger.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
