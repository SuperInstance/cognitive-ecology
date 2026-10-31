"""Dogfood ideation: use a real model to expand the project's own concepts.

This is the tool that produced the artifacts in experiments/dogfood/ —
we use tencent/Hy4-preview (cheap, strong, aggressively cache-discounted)
to stress-test our ideas, while the kernel's caching discipline keeps the
iteration loop affordable.

    export DEEPINFRA_API_KEY=...        # env-only; never a file
    python scripts/ideate.py --ask "design 5 play-test scenarios for ..." \
        --out experiments/dogfood/my-ideas.md

Without a key it falls back to the deterministic MockProvider, so the loop
is always runnable (CI included). Every call is journaled with token and
cache-hit counts to experiments/dogfood/journal.jsonl.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cognitive_ecology.agents import (  # noqa: E402
    MockProvider, OpenAICompatProvider, StablePrefixSession,
)

# The STABLE PREFIX: the project spec. It never changes between calls, so
# every ideation call after the first hits the provider's prompt cache.
SPEC = """You are the ideation organ of the cognitive-ecology project: a persistent,
skeptical product designer who thinks in terms of living systems, incentives,
and failure modes.

PROJECT SPEC (stable across this whole session — reason from it, do not restate it):
cognitive-ecology is a Python kernel (zero dependencies, zero-LLM core) for
building agents that persist like organisms instead of dying with each chat
session. Layers:
- L0 Runtime: a process, not an agent. Advances in ticks. Never calls a model.
- L1 Events: MIDI-style immutable events (~100 bytes) with causal chains.
- L2 World Graph: anti-RAG. Typed graph; every node has a biography
  (born_tick, last_seen, weight). Recall = attention-guided traversal.
- L3 Memory: events consolidate into the graph (Hebbian, repetition, decay).
- L4 Script Ecology: an agent is a population of scripts that compete,
  starve, die (recorded in a necrology, never deleted), and mutate.
- L5 Attention Market: attention = urgency * justification * opportunity *
  novelty * expected_value (multiplicative; any zero vetoes).
- L6 WHY (crown): every component answers why_should_this_run(). States:
  alive/dead/unknown/absent. CONSERVATION LAW: WHY is never deleted; killing
  a root cascades descendants to UNKNOWN (questionable, revivable).
- L7 Identity: slowly-drifting self-model; stable introspection string
  (prompt-cache-friendly).
- L8 Sleep: idle time triggers replay, pruning, and dreams (mutations).
LLMs are citizens, not kings: they propose parameterized scripts from a safe
action library; WHY decides what may exist, the market decides what runs.
Decision models (typed outputs with calibrated confidence) are a second
citizen class for structured choices under uncertainty.

Answer with concrete, buildable specifics. Prefer tables and short numbered
lists. No hype."""


def main() -> None:
    ap = argparse.ArgumentParser(description="dogfood ideation loop")
    ap.add_argument("--ask", help="the ideation ask (or use --ask-file)")
    ap.add_argument("--ask-file", help="file containing the ask")
    ap.add_argument("--out", required=True, help="markdown output path")
    ap.add_argument("--provider", default="DEEPINFRA",
                    choices=["DEEPINFRA", "TYPESAFE"],
                    help="env prefix for _API_KEY/_BASE_URL/_MODEL")
    ap.add_argument("--max-tokens", type=int, default=2400)
    ap.add_argument("--temperature", type=float, default=0.8)
    ap.add_argument("--journal", default=None)
    a = ap.parse_args()

    ask = a.ask if a.ask else Path(a.ask_file).read_text(encoding="utf-8")
    journal = a.journal or str(
        Path(__file__).resolve().parents[1] / "experiments" / "dogfood" / "journal.jsonl"
    )

    api_key = os.environ.get(f"{a.provider}_API_KEY", "")
    if api_key:
        provider = OpenAICompatProvider.from_env(a.provider)
        print(f"provider: {provider.name}")
    else:
        provider = MockProvider()
        print("no API key in env -> MockProvider (deterministic, simulated caching)")

    session = StablePrefixSession(provider, SPEC, journal_path=journal,
                                  label="ideate")
    completion = session.call(ask, max_tokens=a.max_tokens,
                              temperature=a.temperature)

    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    header = (
        f"<!-- dogfood: model={completion.model} | "
        f"prompt_tokens={completion.prompt_tokens} "
        f"completion_tokens={completion.completion_tokens} "
        f"cached_tokens={completion.cached_tokens} "
        f"latency_s={completion.latency_s} | "
        f"date={time.strftime('%Y-%m-%d')} | tool=scripts/ideate.py -->\n\n"
    )
    Path(a.out).write_text(header + completion.text.strip() + "\n", encoding="utf-8")

    stats = session.stats()
    print(f"wrote {a.out}")
    print(f"cache: hit_rate={stats['cache_hit_rate']:.2%} "
          f"cached={stats['cached_tokens']} tok "
          f"est_saved=${stats['est_saved_usd']}")


if __name__ == "__main__":
    main()
