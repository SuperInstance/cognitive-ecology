# Changelog

All notable changes to this project are documented here. The build log
(`docs/JOURNAL.md`) carries the narrative; this file carries the deltas.

## v0.1.0 — 2026-10-31

The first organism: the law, the body, the teachers, and the receipts.

### Added

- **WHY kernel** (`ecology.why`): faithful Python port of why-core v0.2 —
  two-file format (graph.txt/att.txt with `all-of:`, `until=`, `review-by=`,
  `# discovered:`), six-pass evaluation (explicit-only liveness, full-depth
  deadness, candidate namespace for inferred edges, conjunctive
  short-circuit, mortality), reverse dominators, derivation chains. Pinned
  to the 15-pair golden corpus shared with the Rust reference; `ecology
  check` is CLI-compatible (same statuses, same exit codes).
- **Ecology layers**: L0 runtime (processes, bids, ticks, starvation-not-death),
  L1 event fabric, L2 world state graph (SQLite, memory maturity ladder),
  L3 budgeted simulations, L4 script ecology (candidate→active→retired by
  learned utility), attention economy (manifesto formula; market/central/
  hybrid policies with governance rollover), tension field (pressure
  compounds with age), mechanical sleep (observations→episodes→patterns→
  replay-validated routines; zero LLMs), identity as a stable attractor,
  morning briefing.
- **WHY as the scheduler**: `JustificationWatch` multiplies every bid by
  its justification weight (alive 1.0 / questionable 0.25 / dead 0.0) and
  emits `justification.broken` when chains die. Open Question #5, answered
  in code.
- **The experiment**: `ecology week` — the smallest persistent world that
  improves itself unattended (seed 42: 4 routines compiled, 332
  observations handled, 5 scripts self-retired, day-4 root-kill broke 8
  justifications without deleting anything, 10.88 learned utility, zero
  LLM calls).
- **LLM teacher layer**: cache-first prompt protocol, DeepInfra client
  (7 panel models, `prompt_cache_key`, cached-token accounting,
  provider-reported costs), TypeSafe Jev decision client (noul/choice/score),
  retry/backoff honoring Retry-After, token bucket, circuit breaker, SQLite
  usage ledger (`ecology usage`).
- **Research panel**: 7 model lineages in role seats (ideator seat vacant —
  MiniMax key rejected), append-only transcripts, Jev decision gates
  between rounds, receipts in `library/rounds/`. Three live rounds shipped
  (~$0.116 total spend).
- **Knowledge library**: original manifesto, audit copy, provider research,
  open-questions ledger (10/10 probed), crown-question reflection.
- **Docs**: architecture map, journal, process manual, 6 ADRs with reversal
  conditions, provider observations (including the MiniMax outage).
- **CI**: lint + tests (Python 3.10/3.12) + secrets scan on every push.

### Known issues

- MiniMax authentication rejected on all endpoints (key issue, not client) —
  ideator seat vacant until rotated.
- Sleep's replay validation conflates frequency with value (round-002
  panel finding); utility-from-consequence is the queued fix.
- Sleep-born routines carry no WHY edges yet (open question #11 in the
  ledger).
