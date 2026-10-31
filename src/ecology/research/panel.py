"""The research panel: who is at the table.

Eight panelists across two providers and (at least) seven model lineages —
diversity of thought is the point (the owner's directive: MiniMax for
"ideation that's different from your model"; Seed-2.0-mini as the iterative
devil's advocate). Roles are the research-cell metaphors from the
manifesto: Reader, Indexer, Verifier, Contrarian, Synthesizer, Teacher.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Participant:
    name: str  # display name in the transcript
    provider: str  # deepinfra | minimax
    model: str
    role: str  # panel role
    instruction: str  # what this participant does each turn


DEFAULT_PANEL: list[Participant] = [
    Participant(
        name="ideator",
        provider="minimax",
        model="MiniMax-M3.1-Flash",
        role="ideator",
        instruction=(
            "Open the round: generate 2-3 genuinely new directions or framings nobody "
            "at the table has tried yet. Favor ideas from outside the obvious lineage."
        ),
    ),
    Participant(
        name="analyst",
        provider="deepinfra",
        model="XiaomiMiMo/MiMo-V2.6-Pro",
        role="analyst",
        instruction=(
            "Analyze the strongest current proposal on its mechanics: what would actually "
            "break first, what it costs, what it assumes. Be quantitative where possible."
        ),
    ),
    Participant(
        name="explorer",
        provider="deepinfra",
        model="tencent/Hy4-preview",
        role="explorer",
        instruction=(
            "Reach for a structural analogy from another domain (biology, logistics, "
            "music, cities, ecology) and say exactly what it predicts here."
        ),
    ),
    Participant(
        name="verifier",
        provider="deepinfra",
        model="nvidia/NVIDIA-Nemotron-3-Ultra-550B-A55B",
        role="verifier",
        instruction=(
            "Audit the round so far: separate claims into EVIDENCED, PLAUSIBLE, and "
            "UNSUPPORTED. Name what evidence would move a claim up a tier."
        ),
    ),
    Participant(
        name="contrarian",
        provider="deepinfra",
        model="ByteDance/Seed-2.0-mini",
        role="contrarian",
        instruction=(
            "Be the devil's advocate: attack the weakest link of the round's reasoning, "
            "steelman the opposite conclusion, and explain your counter-logic. Then say "
            "what would change your mind."
        ),
    ),
    Participant(
        name="architect",
        provider="deepinfra",
        model="ByteDance/Seed-2.0-pro",
        role="architect",
        instruction=(
            "Respond to the attacks: either concede with a design change (be specific) "
            "or defend with a mechanism. Turn the round's surviving ideas into concrete "
            "next steps for the codebase."
        ),
    ),
    Participant(
        name="indexer",
        provider="deepinfra",
        model="inclusionAI/Ling-3.1-flash",
        role="indexer",
        instruction=(
            "Compress the round into (a) at most 5 load-bearing claims and (b) the 2 "
            "sharpest open questions. Terse. These feed the decision model."
        ),
    ),
]

SYNTHESIZER = Participant(
    name="synthesizer",
    provider="deepinfra",
    model="Qwen/Qwen3.8-Max",
    role="synthesizer",
    instruction=(
        "Synthesize the whole discussion into a verdict: what was learned, what changed "
        "in the design, what goes in the open-questions ledger, and one recommendation "
        "the maintainer should act on first."
    ),
)


def panel_for(available_providers: set[str]) -> list[Participant]:
    return [p for p in DEFAULT_PANEL if p.provider in available_providers]
