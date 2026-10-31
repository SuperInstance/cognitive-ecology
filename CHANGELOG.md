# Changelog

All notable changes to cognitive-ecology. Format follows
keepachangelog.com; versioning is semantic-ish (pre-1.0: minor bumps for
anything, patches for fixes).

## [0.2.0] — 2026-10-31

The kernel becomes a complete, documented, play-tested organism suite.

### Added
- **Merged with the parallel v0.1 research line** (`src/ecology/`): kept
  intact as provenance — its alternative WHY formalism, LLM teacher
  layer (DeepInfra panel / MiniMax / TypeSafe Jev client / SQLite usage
  ledger), research panel harness, 6 ADRs, tiny-MUD and week-in-a-box
  examples, and `library/` panel-round receipts. Both test suites run
  green together (121 = 40 + 81). New work targets `cognitive_ecology`.
- **Complete L0–L8 kernel** (`src/cognitive_ecology/`): runtime, events,
  world graph, memory, script ecology, attention market, executive, WHY
  conservation tree, identity, sleep, tensions, simulations — zero
  runtime dependencies, zero LLM required.
- **`agents/` subpackage**: OpenAI-compatible providers (DeepInfra /
  `tencent/Hy4-preview` default; typesafe.ai-style decision endpoints
  via env), deterministic MockProvider, `StablePrefixSession` with
  token/cache journaling and savings estimates; `LLMAgent` orchestrator
  with a safe, audited action library (observe/note/search/message/rest)
  and a tiny `when_hint` trigger DSL.
- **The veto law**: zero-attention bids never clear — not even in an
  empty market. (Found by play-testing; pinned by test.)
- **Proposer staleness**: LLM agents' propose bids include a boredom
  term, after dogfooding showed successful spawned scripts starve their
  own proposer. (Found by dogfooding.)
- **One-shot search semantics**: re-charting a charted topic fails
  honestly, so no-op scripts cannot clog the market.
- **Deterministic dream naming**: generation-counted unique names for
  mutated scripts (collision bug found by test).
- **`experiments/minimal_world.py`**: the ten-minute organism — life,
  crisis (kill the root), resurrection, sleep, save/load persistence.
- **Five runnable examples** across domains (heartbeat, research
  assistant, decision desk, game NPC, personal journal), all keyless.
- **Templates**: fill-in agent template + play-test scenario template
  with eight seeded scenarios from dogfooded ideation.
- **Docs suite**: 8 guides + 4 hands-on tutorials, including caching
  economics and the decision-model synergy plan.
- **Tooling**: `scripts/run_rounds.py` (JSONL telemetry),
  `scripts/ideate.py` (dogfood ideation loop), `Makefile`, CI (test
  matrix 3.10–3.12 + secret scan), `bootstrap.sh` (PAT via env, askpass
  shim — credentials never touch disk).
- **Dogfood artifacts** (`experiments/dogfood/`): real model outputs +
  token/cache journals from the 2026-10-31 Hy4-preview session that
  seeded the scenario catalog and the misconception fixes.

### Changed
- World graph digest format now `id (kind) w=…` for readability.

### Fixed
- Zero-attention market clearing (see veto law, above).
- Dream name collisions.
- Diary/telemetry printed post-run state instead of per-tick state
  (`TickReport.tensions` added).

## [0.1.0] — 2026-10-30

Initial design: layer architecture (L0–L8), WHY conservation law,
attention economics formula, anti-RAG world graph concept, script
ecology concept, security posture for keys. Kernel modules
`why/runtime/events/graph/attention/scripts` drafted.
