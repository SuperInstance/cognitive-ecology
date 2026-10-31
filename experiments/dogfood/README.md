# Dogfood — artifacts from ideating with real models

This directory holds outputs from `scripts/ideate.py`: ideation and
critique loops run against `tencent/Hy4-preview` on DeepInfra, under the
kernel's own caching discipline (stable prefix, journaled tokens).

Every file's header comment records the model, token counts, cache hits
and latency of the call that produced it. `journal.jsonl` is the raw
usage ledger — the receipts.

## Artifacts (2026-10-31 session)

| File | What it is | Where it landed |
|---|---|---|
| `2026-10-31-hy4-playtest-scenarios.md` | 4 play-test scenarios (games, health, finance, education), full 7-field detail | seeded `templates/scenario_template.md` + examples 03/04 |
| `2026-10-31-hy4-playtest-scenarios-5to8.md` | 4 more scenarios (science, devops, smart home, agriculture) | completed the scenario catalog |
| `2026-10-31-hy4-comprehension-and-cache.md` | top-5 newcomer misconceptions + cache-economics arithmetic | misconception fixes in `docs/02_architecture.md`; cost tables in `docs/06` & tutorial 04 |

## What the session proved (with receipts)

- **Prefix caching is real and measurable.** Calls 2+ report
  `cached_tokens=256` for the shared system prompt (see journal) — the
  stable-prefix discipline pays for itself even across *separate
  process invocations* of the tool.
- **The model is a useful design citizen, not an oracle.** Its scenario
  failure modes ("WHY ossification", "urgency gaming", "assumption rot")
  were concrete enough to become watch-list items; its misconception
  list is now nearly verbatim in the architecture doc.
- **Token economics of ideation.** ~600 prompt tokens + ~2-3.5k
  completion tokens per call ≈ $0.01-0.02 at Hy4-preview rates; with the
  cached prefix, the *effective* prompt cost drops further on every
  subsequent call in a session.

## Reproduce

```bash
export DEEPINFRA_API_KEY=...   # env-only
python scripts/ideate.py \
  --ask "design 5 play-test scenarios for a cognitive-ecology organism in <domain>" \
  --out experiments/dogfood/my-session.md
```

Without a key the tool runs against the deterministic MockProvider, so
the loop itself is testable in CI.
