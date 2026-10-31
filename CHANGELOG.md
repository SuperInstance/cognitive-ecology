# Changelog

All notable changes to cognitive-ecology. Format follows
keepachangelog.com; versioning is semantic-ish (pre-1.0: minor bumps for
anything, patches for fixes).

## [Unreleased]

### Added
- **The attach rite, de-rited + duplicate economics** (round 23; wave-1
  findings 6 and 7). `Runtime.ensure_why / ensure_tension /
  ensure_component / ensure_script`: idempotent by contract — attach()
  can run twice (after load, or a dev hot-reload) without a single
  has()-guard; one honesty rule (an existing node_id re-ensured with a
  different statement raises: an id means one purpose, forever);
  ensure_tension never resets a saved drive's level;
  ensure_script rehydrates saved track records. `ScriptEcology
  .spawn_unique`: a rejected duplicate is a DEMOTION — behavior
  signatures (owner + action + args + when_hint; the name is not the
  behavior) compared against the live population, rejections counted
  (`duplicates_rejected`), tailed (`duplicate_log`, bounded), and the
  orchestrator's `~tick` variant hack is GONE: duplicates emit an
  ERROR event the model itself reads next turn, accept_rate counts
  spawns only so re-proposals decay the propose bid's expected value —
  population bloat by re-proposal is over. `rest` rejects non-finite
  amounts at the seam and `relieve`/`burden` no-op them in the kernel
  (the `max(0.0, nan)` free-lunch hole, closed at both layers).
  `docs/MIGRATIONS.md`: the compatibility law, release-by-release
  upgrade notes, and the old-rite/new-rite translation table.
- **Host drivers + the hosting guide** (round 22; wave-1 finding 4,
  "no host-integration story"). `WallClockDriver` (zero-dep,
  injectable clocks) ticks an organism on wall-clock intervals with
  drift-free absolute-slot pacing, graceful Ctrl-C, host-initiated
  stops, a checkpoint cadence, and a `DriverReport` receipt — and the
  pinned contract underneath every recipe: a driver owns WHEN, never
  WHAT (driven life is bit-identical to `rt.run(n)`). Guide
  `docs/10_host_integration.md`: the host-surface table, the
  world-not-bus ingest law, and four recipes (game loop with the
  accumulator-epsilon lesson, wall-clock session, cron tick with the
  attach rite, FastAPI lifespan) plus rotating checkpoints and
  declared cost/determinism notes. Example 09 runs all three shapes
  keyless — and caught itself: the frame-rate twin failed its own
  identity check until the float-undershoot epsilon was added (the
  1/30-accumulated-90-times bug), and the driver's first version
  doubled the first interval (off-by-one in slot arithmetic, caught
  by the injected clock). Example 04's lossy read is fixed: asks are
  persisted into the world graph at ingest time (pinned by
  tests/test_example04_asks.py — an unanswered ask now survives
  restarts), and gossip works the unanswered queue in order.
- **The market log — the observation boundary as a read model**
  (round 21, ADR-0015; wave-1 finding 3, "the organism is invisible").
  `Runtime.market_log` serializes every market clearing as it happens:
  one row per bid per tick with the EXACT floats of the five attention
  factors and the attention product (no rounding, no re-derivation —
  json roundtrips bit-for-bit), the resource and claimed success
  probability, and the market's verdict (`run` / `yield` / `starved` /
  `vetoed`, with vetoed finally distinguished from starved). When the
  delegated arbiter truly arbitrated, a row records pick, confidence,
  and divergence. `summary()` (volumes, clear rate, winners, vetoes),
  `veto_reasons()` (WHICH factor was zero, in the market's own
  numbers), `bids()` (pandas-ready), bounded retention
  (`MarketLog(keep=...)`, default 100k rows), `to_jsonl()` /
  `from_jsonl()`. Three laws pinned by test: exact, not a second
  source of truth, non-perturbing (bit-identical twin runs). The log
  is observation, not state — never saved, fresh on load. Guide:
  docs/09_market_log.md.
- **Run provenance and seed sweeps** (`scripts/run_rounds.py`): every
  run writes `manifest.json` (kernel version, python, platform, git
  commit, seed, config, wall time, sha256 digest of every output) —
  orphaned outputs are no longer possible; `market.jsonl` is written
  alongside the telemetry; `--sweep N` runs the scenario across N
  seeds and aggregates mean ± spread per metric. The sweep's first
  use found `minimal_world` is seed-invariant (nothing consumes
  randomness) — the instrument calibrated itself on day one.
- 17 new tests (`tests/test_marketlog.py`); 16 in round 22
  (`tests/test_drivers.py`, `tests/test_example04_asks.py`); 18 in
  round 23 (`tests/test_safe_seam.py`): 324 total.

### Added (earlier unreleased rounds)
- **Machine-checked docs truth** (round 18, the wave-1 diligence top
  one): `scripts/check_docs.py` + `make truth` + a CI step. Version
  coherence (CHANGELOG's newest numbered section must equal pyproject's
  version) and every documented count (tests, examples, ADRs,
  tutorials, guides) are checked against the tree on every push —
  prose numbers rot, checked numbers cannot. First run caught a live
  drift (INDEX claimed 6 ADRs on disk; the shared docs/ADRs holds 14).
  The quickstart's code block is now executed as a test
  (`tests/test_docs_code.py`), so a doc can never rot into a crash
  again.

- **Persistence trust at the door** (round 20a, the wave-1 backend
  persona's top one): `state.json` is written atomically (temp+rename);
  `events.jsonl` is append-mode (each save appends only the delta — no
  more whole-file rewrites and autosave hitches); the state records an
  event chain head + watermark, and `load()` refuses at the door —
  corrupt JSON, tampered events (any edit changes the fold), an
  interrupted save (watermark mismatch), or an edited WHY state (the
  conservation receipt is recomputed, never trusted) all raise by name
  instead of booting a silently-wrong organism. Sleeper stats and
  idle_window now persist; an adopted script keeps its saved born
  (tick-0-born scripts no longer re-stamp at the load tick — the
  game-dev persona's save-compat bug). 10 tests.

- **Bounded event retention — snapshot+delta** (round 20b, live
  ideation 015's verdict; the game-dev persona's hard ceiling — ~19
  events/tick meant 33 MB and 0.5 s autosave hitches at 100k ticks):
  `rt.compact_events(path, keep=N)` truncates the log to the most
  recent N events under a receipt, ONLY after a full snapshot proves
  the state at that tick (never truncate an unverified basis). The
  dropped prefix is folded into a chain anchor the door can verify —
  the chain still covers the FULL history, so a truncated file
  verifies exactly as a full one does, and what went away is a
  receipt, not a resurrection. Pinned by the test round 015 named: a
  compacted life is bit-identical to an un-compacted twin (same life,
  same books, same graph digest). Double compaction composes anchors.

### Fixed
- **Fail-safe totality** (round 17, found by the wave-1 red team — six
  zero-shot engineers play-tested the repo as real users):
  - a component whose `bid()` raises — or returns junk — no longer kills
    the tick loop; it is contained exactly like `act()` was, recorded
    as an `ERROR` event with the reason, and the component starves on
    its own economics;
  - a failed action's `Outcome.note` now reaches the event log as an
    `ERROR` event (on-call can see *why*, not just *that*);
  - an arbiter's ANSWER is validated like its exceptions already were:
    a malformed return (wrong types, a foreign look-alike bid, a single
    object, duplicates) degrades to the deterministic shadow, is
    counted in `Executive.arbiter_malformed`, and is recorded — the
    documented "degrades, never crashes" is now true for the whole
    failure surface.

## [0.4.0] — 2026-11-01

*(Backfilled at round 17 — this release shipped as tag `v0.4.0` without
a changelog entry; the wave-1 diligence play-test caught the gap.)*

### Added
- **Society-basis federation** (ADR-0011): treaties are foreign purpose
  references that route attestation between organisms; service keeps
  the beneficiary's books fresh through its own re-attestation
  economics; provider death propagates hard (question + exchange
  receipt, treaty broken), neglect propagates soft (the beneficiary's
  own reaper); the federation auditor detects forged service and
  missed propagations.
- **The WHY DAG** (ADR-0012, closes OPEN_QUESTIONS #1): multi-parent
  purposes with best-path (OR) semantics; path-survivor cascades with a
  fixpoint (no over-cascade, no under-cascade); stamping serves the
  whole DAG lineage; the auditor replays DAG bases; trees keep
  bit-for-bit v0.2 semantics.
- **The outcome-arbiter** (ADR-0013, closes OPEN_QUESTIONS #3): the
  delegated tie-break is scored by realized outcomes — calibration
  (Brier) plus value vs the action base rate; a miscalibrated or
  value-destroying arbiter is benched to the deterministic shadow with
  a receipt, announced once. Live round 014 (jev, 60 ticks): benched at
  tick 25 on Brier 0.307 while value-positive.
- **Journal compaction** (ADR-0014, closes OPEN_QUESTIONS #13): keep the
  last stamp per (node, ALIVE window, provenance) — exact replay
  equivalence, receipted and chain-covered; journal holds at 4 entries
  across 10 epochs of 1k ticks (vs 60k growing), verify ~0 ms flat.
- 61 new tests (179 → 240).

### Fixed
- Three-phase equal-tick replay ordering (found by the example-08
  play-test): to-ALIVE transitions → stamps → other transitions.
- Monotonic heartbeats + epoch-aware cursor resync (found by the society
  soak): a stale stamp never rewinds freshness; exchange cursors survive
  journal compaction instead of silently starving a beneficiary for
  ~500 ticks.
- Red-team hardening (round 011): sole-ness as a fact, doubter
  provenance on every `question()`.

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
