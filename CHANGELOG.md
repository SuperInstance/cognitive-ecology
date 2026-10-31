# Changelog

All notable changes to cognitive-ecology. Format follows
keepachangelog.com; versioning is semantic-ish (pre-1.0: minor bumps for
anything, patches for fixes).

## [0.3.0] — 2026-10-31

### Added
- **The soak test** (`experiments/soak.py`, `make soak`): one organism,
  10,000 ticks, every invariant — re-attestation, probation, archival,
  full auditor verification every 1,000 ticks, save/load re-verify.
  Receipts (seed 99): 2,327 ticks/s, 70k events, 60k journal stamps, hot
  tree held at 11 nodes while 15 archived, 81 ms final verify, 6.8 MiB
  state round-tripped and re-verified from disk. Pinned in CI at 1,500
  ticks; determinism pinned bit-for-bit by test.
- **Honest archival** (ADR-0010, closes OPEN_QUESTIONS #6): `ColdStorage`
  sweeps ancient DEAD subtrees (dead > min_age, no living descendant,
  whole subtree together) into cold storage — counted by conservation,
  biographied in a manifest the auditor verifies against the replay basis
  (tampered manifests fail), restorable by a recorded two-act ceremony
  (restore-with-reason → resurrect-with-parole). 10 tests.
- **Decision-model integration, two narrow points** (ADR-0009, live round
  005): the executive's optional `arbiter` hook delegates ONE bounded
  decision (reordering live contenders when slots are contended — vetoed
  bids never reach it, failures degrade to the deterministic shadow);
  `DecisionArbiter` adapts typed choice questions (typesafe/Jev shape,
  cache-stable state). Bids may carry `success_p`; the runtime scores
  every claim against outcomes in a `CalibrationLog` (Brier, reliability
  bins, per component). Live receipt: jev diverged from the shadow 50/50
  contended ticks; the overconfident scout measured MISCALIBRATED
  (Brier 0.395) while the humble archivist measured calibrated.
- **Conservation auditor** (ADR-0008, adopted from live ideation round
  004b): every WhyTree carries a complete replay basis (genesis block +
  necrology + attestation journal); `ConservationAuditor.verify()` replays
  it from nothing and requires bit-for-bit equivalence with the living
  tree. Receipts carry per-check results, live/replay digests, and a hash
  chain over the whole basis (pins history against edits, including
  superseded stamps). `Runtime.save()` embeds the receipt in state.json —
  saved organisms vouch for themselves. 12 tests covering equivalence,
  every tamper vector, persistence, and a 300-tick random storm.

### Added
- **Re-attestation economics** (ADR-0007): optional `attestation_horizon`
  makes WHY liveness a subscription instead of a purchase — running under
  a purpose stamps its whole chain (`stamp_chain`, transitive to the root);
  `justification()` is discounted by weakest-link `freshness()` (grace
  window, then linear decay); the periodic audit reaps unserved ALIVE
  nodes to UNKNOWN ("lapsed", recorded, never deleted); only explicit
  `revive(reason)` restores a lapsed purpose. Default `None` keeps v0.2
  semantics bit-for-bit. 16 new tests; receipts in
  `experiments/reattestation_economics.py` (served purpose holds 1.000
  for 480 ticks; unserved lapses twice — revival without service buys
  exactly one more horizon).

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
