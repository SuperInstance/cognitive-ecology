#!/usr/bin/env python3
"""Round 3 — the iterative devil's-advocate expansion (experimental shape).

The owner's directive: ByteDance/Seed-2.0-mini is "especially good at being
an iterative devil's advocate and idea expander… good at out of the box
exploratory thinking and iterating and explaining itself on counter logic."

So this round is a different shape from the panel: ONE model, MANY
iterations. Seed-2.0-mini proposes, then attacks its own previous proposal,
then attacks the attack — each iteration sees its own prior text as an
append-only prefix (cache-first), and between iterations the TypeSafe
decision model gates the loop with typed questions: keep refining, pivot,
or stop. A language model generates; a decision model steers.

    PYTHONPATH=src python3 scripts/devils_advocate_round.py
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

MODEL = "ByteDance/Seed-2.0-mini"

SYSTEM = (
    "You are the devil's advocate of a research program on a persistent cognitive "
    "ecology (WHY = live justification as conservation law; runtime, attention "
    "economy, script ecology, sleep consolidation, world graph, LLM teachers).\n\n"
    "Your job is iterative: propose concretely, then attack your own proposal on "
    "its counter-logic, then repair or replace it. Every iteration must end with "
    "either a SHARPER proposal or an honest retraction. Format each iteration as: "
    "PROPOSAL / ATTACK / REPAIR (three short sections, <= 220 words total)."
)

START = (
    "The program's history left three abandoned jewels: (1) reasoning compression "
    "— 'reduce the amount of reasoning that must occur at all', measurable in "
    "tokens/approvals; (2) proof-carrying intent — every decision object carries "
    "its proof, authority, constraints, justification; (3) necessity drift — 'the "
    "gradual separation between a structure and the reason that created it'. "
    "Propose the single most valuable v0.2 feature for the ecology that embodies "
    "one of these, naming the module it lands in."
)

ITERATE = (
    "Now attack your own previous iteration on its weakest counter-logic, then repair it or "
    "replace it with a sharper proposal. Do not repeat yourself; escalate precision."
)


def main() -> int:
    settings = Settings.from_env(REPO / ".env")
    ledger = Ledger(REPO / settings.ledger_path)
    chat = DeepInfraClient(settings, ledger=ledger)
    jev = TypeSafeClient(settings, ledger=ledger)

    history: list[str] = []
    decisions: list[dict] = []
    cost = 0.0
    stable = SYSTEM + "\n\nTOPIC: turn the three abandoned jewels into concrete v0.2 features."

    prompt = stable + f"\n\nITERATION 1 — your opening move:\n{START}"
    for i in range(1, 4):
        spec = PromptSpec(
            stable_prefix=prompt,
            variable_suffix="Write iteration now.",
            max_tokens=700,
            temperature=0.8,
        )
        response = chat.complete(spec, MODEL, role="devils-advocate")
        cost += response.usage.cost_usd or 0.0
        history.append(response.text.strip())
        print(
            f"iteration {i}: {response.latency_ms}ms, "
            f"{response.usage.prompt_tokens}in ({response.usage.cached_tokens} cached)"
        )

        if i == 3:
            break
        name_q, q1 = TypeSafeClient.choice(
            "steer",
            "How should the next iteration proceed?",
            {
                "refine": "Keep sharpening the same proposal",
                "pivot": "Attack a different jewel instead",
                "retract": "The proposal is broken; start over from the strongest critique",
            },
        )
        name_n, q2 = TypeSafeClient.noul(
            "concrete", "Is the current proposal concrete enough to implement as code?"
        )
        gate = jev.decide(
            DecisionRequest(
                state={"iteration": i, "last_output": history[-1][:4000]},
                questions={name_q: q1, name_n: q2},
            ),
            role="devils-advocate-gate",
        )
        steer = gate.answers["steer"].value
        decisions.append(
            {"iteration": i, "steer": steer, "concrete": gate.answers["concrete"].value}
        )
        cost += gate.usage.cost_usd or 0.0
        print(f"  gate: steer={steer} concrete={gate.answers['concrete'].value}")

        if isinstance(steer, tuple) and steer[0] == "pivot":
            nudge = "PIVOT: the gate says attack a different jewel now."
        elif isinstance(steer, tuple) and steer[0] == "retract":
            nudge = (
                "RETRACT: the gate says your proposal is broken — "
                "restart from your own strongest critique."
            )
        else:
            nudge = ITERATE
        prompt = (
            stable
            + "\n\nTRANSCRIPT OF YOUR OWN ITERATIONS:\n"
            + "\n---\n".join(history)
            + f"\n\nITERATION {i + 1}. {nudge}"
        )

    lines = [
        "# Round 3 — iterative devil's advocate (experimental shape)",
        "",
        f"*Run: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} — "
        f"{MODEL} iterating on itself, gated by jev — cost ${cost:.6f}*",
        "",
        "## Iterations",
        "",
    ]
    for i, text in enumerate(history, 1):
        lines.append(f"### iteration {i}")
        lines.append("")
        lines.append(text)
        lines.append("")
    if decisions:
        lines.append("## Decision gates (jev)")
        lines.append("")
        for d in decisions:
            lines.append(
                f"- after iteration {d['iteration']}: "
                f"steer={d['steer']} concrete={d['concrete']}"
            )
        lines.append("")
    lines.append(f"---\n*Recorded cost: ${cost:.6f}*")

    out = REPO / "library" / "rounds" / "003-devils-advocate-three-jewels.md"
    out.write_text("\n".join(lines))
    print(f"written: {out}  cost so far (this round): ${cost:.6f}")
    ledger.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
