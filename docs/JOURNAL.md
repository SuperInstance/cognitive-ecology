# Journal — the build log

*The process is a product. This journal records what was done, what was
learned, and what failed, in order, with the receipts. UTC timestamps.*

## 2026-10-31 — session one: from manifesto to organism

### Recon (03:45–04:00Z)

- The session opened with the owner's brief: the Persistent Cognitive
  Ecology manifesto, a DeepInfra model list for iterative ideation, and the
  directive to keep building with subagents over many rounds, using
  typesafe.ai experimentally and documenting the process as a first-class
  artifact.
- Parallel subagents ran: (a) a web-research agent produced the full
  TypeSafe/Jev API shapes (from the live OpenAPI spec), MiniMax endpoints,
  and DeepInfra caching mechanics — including prices; (b) a deep-read agent
  covered all 23,776 lines of SIR.md (the original conversation) and
  returned the lineage map, the rabbit-trail inventory, and a crown
  verdict; (c) a comparative agent read the five digests + the why-v0.1
  code and returned per-digest analyses, the settled core, and build
  recommendations.
- Discovered prior work the summary had missed: `repos/why` (Rust, v0.2,
  already pushed to SuperInstance/why), the uv-to-why knowledge library
  (3 rounds of discussion, 24 concept cards), and Muse's external audit at
  `repos/why/docs/audit-2026-10-30.md`. The audit's two findings
  (inferred-edge liveness; one-hop deadness) were already fixed in v0.2 —
  the port inherits the fixes and the golden corpus that pins them.
- Live provider probes: GitHub PAT valid (SuperInstance); all 7 DeepInfra
  models present; DeepInfra caching confirmed as
  `usage.prompt_tokens_details.cached_tokens` (0 hits below ~1k tokens —
  expected); TypeSafe answered in 178ms (my first choice-question shape was
  wrong — the OpenAPI spec gave the correct one); **MiniMax 401 on every
  host/auth combination** — key rejected, panel runs without it.

### M1 (04:05Z) — the kernel first, deliberately

- Ported why-core v0.2 to Python (`ecology.why`): parsers, six-pass
  evaluation, reverse dominators — a pure function of (graph, attestation,
  as_of), no I/O.
- **Test failures that taught semantics:** my first test expected
  dependents of a root *attested dead* to be "questionable". The kernel
  said otherwise, and the kernel is right: attested-dead is certainty
  (dead at any depth); *questionable* is what happens when liveness is
  withdrawn (dangling), stale, or inferred. The manifesto's "questionable,
  not deleted" maps to the kernel's `unknown` via those three paths. Pinned
  as tests; documented in ARCHITECTURE.md.
- 39 tests green against the 15 golden pairs copied verbatim from the Rust
  repo. Repo created (public) and pushed: `48a5086`.

### M2 (04:15Z) — the organism under the law

- L0 runtime (processes bid; funded ones tick; starved ones wait — the
  economy is not a hierarchy), L1 event fabric, L2 world graph (SQLite,
  memory maturity ladder), attention economy (market/central/hybrid), and
  the tension field.
- **Two design lessons from failing tests:** (1) default bids with all-zero
  factors score zero under the manifesto's multiplicative formula — the
  default bid now carries the justification as its whole score
  (`Bid.keepalive`); (2) the hybrid policy's governance reserve must roll
  over when no governed bidder claims it, or 30% of every tick is wasted.
- Discovered the discount semantics: questionable processes still run when
  budget is abundant; the 0.25 weight bites under contention (pinned as a
  4:1 energy-ratio test). Pushed: `537e534`.

### M3 (04:25Z) — the week in a box

- Script ecology (candidate→active→retired by learned utility), budgeted
  simulations, the mechanical sleep pipeline, identity as attractor, the
  morning briefing, the tiny MUD, and `ecology week`.
- **Bugs found by the experiment itself:** compiled routines fired on every
  telemetry event regardless of sensor (1,178 "handled" > 393 events) —
  fixed with signature conditions, restoring honest metrics; flaky scripts
  never retired because retirement only checked active scripts — a
  candidate that keeps failing must be rejected (that is the candidate
  stage's whole job).
- Result (seed 42): 4 routines compiled from 332 observations, 4 promoted
  by their own success, 5 scripts self-retired, day-4 root-kill broke 8
  justifications without deleting anything, 10.88 learned utility — zero
  LLM calls. 87 tests green. Pushed: `35e78e7`.

### M4 (04:35Z) — the teachers

- Cache-first prompt protocol (stable prefix + append-only transcripts),
  DeepInfra client (7 models, `prompt_cache_key`, provider-reported cost),
  MiniMax client (anthropic-style, x-api-key — unverified live, key dead),
  TypeSafe Jev decision client (noul/choice/score per the OpenAPI spec),
  retry/backoff honoring Retry-After, token bucket, circuit breaker, SQLite
  usage ledger.
- **A test hang taught an API lesson:** `TokenBucket.acquire` with a
  no-op blocker spins forever; the non-blocking `try_acquire` now exists
  and the blocking path is built on it. 99 tests green. Pushed: `8890eae`.

### M5 (04:40–04:55Z) — the library and the live rounds

- Wrote the canonical docs: manifesto (original preserved in the library),
  architecture map, open-questions ledger (all ten manifesto questions now
  have probes or opinions, several have running code), the crown-question
  reflection, provider research.
- **Round 001 (live, 7 panelists + jev):** "Is WHY truly the conservation
  law?" — 13 turns, 2 decision gates, 70,620 in / 6,560 cached, $0.064.
  The panel independently converged on the re-attestation economics gap
  (the same hole digest 2 identified from the other direction); Jev's
  coherence score rose 2.12 → 2.22 across rounds with the architect thread
  chosen as next-focus at 0.51 → 0.89.
- **Round 002 (live):** "Does week-in-a-box support or falsify the core
  hypothesis?" — 13 turns, $0.050. Falsification designs proposed against
  the utility-seeding and replay-validation shortcuts.
- **Round 003 (live, experimental shape):** the devil's-advocate loop —
  Seed-2.0-mini attacking its own proposals across three iterations with
  Jev gates between them (steer refine/pivot/retract; concreteness tracked
  0.34 → 0.50). $0.002. Cache floor confirmed live: sub-1k-token prompts
  show zero cached tokens.
- Panel resilience added after the first crash: a dropped panelist records
  a vacant seat and the round continues (the MiniMax 401 would otherwise
  have killed round 001 on its first turn).

### Running totals

- Tests: 99 green · Corpus: 15 golden pairs · Live calls: 33 panel turns +
  5 decision gates · Panel spend: ~$0.116 · Commits: 5
