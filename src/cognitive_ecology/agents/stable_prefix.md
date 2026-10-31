# The Stable Prefix — caching discipline for LLM citizens

This file is both documentation and the canonical template for the frozen
part of every LLM prompt in this kernel.

## Why this exists

Providers cache the longest identical *prefix* of a prompt. On DeepInfra,
`tencent/Hy4-preview` bills cached input at **$0.042/M tokens** versus
**$0.834/M** for fresh input (~20x cheaper), with automatic prefix caching
and an optional `prompt_cache_key` for session-scoped hits. Output is
$2.501/M. (Prices checked 2026-10-31 — see docs/06_agents_and_providers.md
for the full arithmetic.)

A 6,000-token prefix reused across 100 dev-loop iterations saves ~$0.48
on that loop alone — and more importantly keeps time-to-first-token low
enough that iterative agent development feels interactive.

## The rule

**Everything that can change between calls goes AFTER everything that
cannot.** Concretely:

```
[ system prompt: STABLE PREFIX — frozen for the session ]
  1. identity introspect   (L7: who the organism is — drifts only between sessions)
  2. action library        (the safe, audited action surface)
  3. output contract       (the JSON proposal format)

[ user message: VOLATILE SUFFIX — rebuilt every call ]
  4. tensions snapshot     (L5: what the organism needs now)
  5. world digest          (L2: what the world looks like now)
  6. recent events         (L1: what just happened)
  7. the current ask       (what this turn should propose/answer)
```

`StablePrefixSession` (agents/providers.py) enforces this: the prefix is
set once, journaled per call with `cached_tokens`, and any change must go
through `set_prefix(reason)` — a counted, deliberate cache bust.

## What never goes in the prefix

- anything with a timestamp, tick number, or "now" in it
- tension levels, world digests, recent events (they churn every tick)
- WHY *states* (alive/dead) — WHY *statements* are fine and stable
- anything you expect to edit while iterating on the agent's behavior

## The template

```
You are {name}, a citizen of a cognitive-ecology organism.

## Who you are
{identity.introspect()}

## What you may propose (the action library — compose within it, never beyond)
{ACTION_LIBRARY_DOC}

## Output contract
Reply with a JSON array of 1-3 proposal objects:
{"name": str, "action": str, "args": {...}, "relieves": [tension names],
 "focus": [graph node ids], "when_hint": "always"|"tension_above:<name>:<x>"|"every:<n>"}
Invalid proposals are dropped silently. The WHY tree decides what may
exist; the attention market decides what runs. You propose.
```

## Identity drift is scheduled, not ad hoc

`Identity.introspect()` is memoized: it returns a byte-identical string
for the whole session no matter how many commitments accumulate. New
commitments surface only when you call `Identity.drift()` — typically
between sessions. Slow identity is not a limitation; it is the mechanism
that makes long-lived cheap agents possible.
