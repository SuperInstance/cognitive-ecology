# ADR 0004 — cache-first prompt protocol

Date: 2026-10-31 · Status: accepted

## Context

The owner's directive: use the DeepInfra models "iteratively in
development… clever about the caching." DeepInfra caches automatically on
longest common prefix; cache-read is 80–90% off list price on the panel
models. A multi-model panel called naively (fresh context each turn) pays
full price for the same shared context ~30 times per discussion.

## Decision

Every teacher call is a `PromptSpec`: a **stable prefix** (panel rules +
topic + context document + the append-only transcript so far) and a **tiny
variable suffix** (this turn's role instruction). Transcripts never
rewrite history — they only append — so every call's prefix extends the
previous call's prefix, which is exactly the shape prefix caching rewards.
A session `prompt_cache_key` scopes the cache to the discussion.

## Consequences

- Observed: 6,560 tokens served from cache in round 001 on the very first
  live run, with the share rising as transcripts grow (round 2+ turns are
  mostly cache).
- The protocol constrains prompt design: no per-turn system prompts (they
  would zero the shared prefix), no editing past turns, summaries must be
  appended as new turns rather than replacing old ones. These constraints
  are cheap and make transcripts honest receipts.
- The ledger reports cached-vs-uncached per model, so the economics stay
  visible instead of assumed.
