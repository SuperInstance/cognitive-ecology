"""A research assistant that remembers by walking, not by embedding.

Pipeline:
  1. INGEST  ten short research notes -> STATE events -> memory consolidates
             them into a World Graph (entities, co-occurrence edges)
  2. WALK    each question -> cue entities -> graph.walk() under a budget
             (this is anti-RAG recall: traversal, not similarity search)
  3. ANSWER  an LLM (or the MockProvider) answers strictly from the walked
             context, under a StablePrefixSession that journals cache hits

Runs with zero keys (MockProvider); set DEEPINFRA_API_KEY for Hy4-preview.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from cognitive_ecology import Event, EventKind, Runtime  # noqa: E402
from cognitive_ecology.agents import (  # noqa: E402
    MockProvider, OpenAICompatProvider, StablePrefixSession,
)

# --------------------------------------------------------------------------
# the corpus: ten notes about agent memory, attention and caching economics
# (yes, the demo dogfoods the project's own research domain)
# --------------------------------------------------------------------------
NOTES = [
    ("note:rag-amnesia", "RAG retrieves chunks by embedding similarity but the agent retains nothing between queries; retrieval is not memory."),
    ("note:world-graph", "The world graph stores typed entities with a biography: born tick, last seen, and a weight reinforced by use."),
    ("note:hebbian", "Hebbian consolidation wires entities that co-occur within a tick; repetition strengthens the edge, disuse decays it."),
    ("note:attention", "Attention economics: bids multiply urgency, justification, opportunity, novelty and expected value; any zero factor vetoes."),
    ("note:why-law", "The WHY conservation law: purpose nodes are never deleted; killing a root cascades descendants to unknown, revivable."),
    ("note:script-ecology", "An agent is a population of scripts that compete for attention, starve, die into a necrology, and mutate in dreams."),
    ("note:sleep", "Sleep replays recent events with a boost, prunes starving scripts, and dreams parameter mutations for the next market."),
    ("note:cache-economics", "Prompt caching: a frozen prefix is billed at the cached rate; on Hy4-preview cached input is roughly twenty times cheaper than fresh input."),
    ("note:stable-prefix", "Identity introspection is memoized so the prompt prefix stays byte-identical within a session, keeping provider caches hot."),
    ("note:decision-models", "Decision models return typed choices with calibrated confidence, fitting the attention market better than free text."),
]

ENTITY_LEXICON = [
    "rag", "memory", "retrieval", "embedding", "world graph", "biography",
    "hebbian", "co-occurrence", "attention", "urgency", "justification",
    "novelty", "expected value", "why", "conservation", "purpose",
    "script", "ecology", "necrology", "sleep", "dreams", "prompt caching",
    "prefix", "identity", "decision models", "confidence",
]


def entities_in(text: str) -> list:
    t = text.lower()
    return [e for e in ENTITY_LEXICON if e in t]


def ingest(rt: Runtime) -> None:
    """Notes become STATE events; memory consolidates them into the graph."""
    tick = 0
    for nid, text in NOTES:
        tick += 1
        ents = entities_in(text) or ["memory"]
        rt.graph.upsert(nid, "note", {"text": text}, tick=tick)
        for e in ents:
            rt.graph.upsert(f"concept:{e}", "concept", {}, tick=tick)
            rt.graph.link(nid, f"concept:{e}", "about", tick=tick)
        # a synthetic event batch so memory's Hebbian pass links co-occurring concepts
        batch = [Event(kind=EventKind.STATE, ts=tick, src="ingest",
                       payload=(f"concept:{e}", {})) for e in ents]
        rt.memory.consolidate(batch, tick=tick)
    print(f"[ingest] {len(NOTES)} notes -> {rt.graph.node_count()} graph nodes, "
          f"{rt.graph.edge_count()} edges (Hebbian co-occurrence)")


def answer_context(rt: Runtime, question: str, budget: int = 10) -> str:
    """ANTI-RAG RECALL: find cue concepts, then walk. No embeddings anywhere."""
    cues = [f"concept:{e}" for e in entities_in(question)]
    cues = [c for c in cues if rt.graph.has(c)] or ["concept:memory"]
    walked = rt.graph.walk(cues, budget=budget)
    lines = [f"walked from {cues} ({len(walked.ids)} nodes):"]
    for nid in walked.ids:
        node = rt.graph.get(nid)
        if node.kind == "note":
            lines.append(f"- note: {node.props.get('text', '')}")
        else:
            related = [e.src if e.dst == nid else e.dst
                       for e in rt.graph.edges_of(nid) if e.rel == "about"]
            lines.append(f"- concept {nid} (w={node.weight:.2f}, "
                         f"appears in {len(related)} notes)")
    print("[walk]  " + lines[0])
    return "\n".join(lines[1:])


STABLE_PREFIX = """You are the memory organ of a research assistant built on the
cognitive-ecology kernel. You answer questions STRICTLY from the context
provided in the user message. If the context does not contain the answer,
say exactly: 'not in my graph'. Be concise: at most four sentences.
This system prompt is frozen for the whole session (it is the cacheable
stable prefix); only the user message changes between calls."""


def main() -> None:
    rt = Runtime(seed=5)
    ingest(rt)

    if os.environ.get("DEEPINFRA_API_KEY"):
        provider = OpenAICompatProvider.from_env("DEEPINFRA")
        print(f"model: {provider.name}")
    else:
        provider = MockProvider()
        print("model: no DEEPINFRA_API_KEY -> MockProvider "
              "(deterministic; cache hits are simulated)")

    session = StablePrefixSession(provider, STABLE_PREFIX, label="research")

    questions = [
        "How does the world graph remember things without embeddings?",
        "Why is a frozen prompt prefix worth money?",
        "What happens to purpose when a root WHY dies?",
    ]
    for q in questions:
        print(f"\n[ask]   {q}")
        context = answer_context(rt, q)
        completion = session.call(
            f"Context from my world graph:\n{context}\n\nQuestion: {q}",
            max_tokens=180, temperature=0.3,
        )
        print(f"[answer] {completion.text.strip()[:220]}")

    stats = session.stats()
    print(f"\n[cached] hit_rate={stats['cache_hit_rate']:.1%} "
          f"cached={stats['cached_tokens']} tok "
          f"est_saved=${stats['est_saved_usd']}")
    print("[graph]  top of the world:")
    for line in rt.graph.digest(6).splitlines()[1:]:
        print("   " + line)


if __name__ == "__main__":
    main()
