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

## 2026-10-31 — session two: the parallel line becomes the organism (v0.2.0)

- **The merge decision.** Two development lines had grown in parallel: the
  research line (`src/ecology`, session one) and the organism line
  (`src/cognitive_ecology`). Instead of one absorbing the other, both were
  kept: the research line intact as provenance (its alternative WHY
  formalism, the teacher layer, the panel receipts), the organism line as
  the target for all new work. Both suites run green together — 121 tests
  (40 new + 81 preserved).
- **The complete kernel**: runtime, events, world graph, memory, script
  ecology, attention market, executive, WHY conservation tree, identity
  attractor, sleep, tensions, simulations. Zero runtime dependencies, zero
  LLM required — the organism is fully alive without any teacher.
- **Three semantics found by playing, not by design:** (1) the veto law —
  a sated drink script in example 01 kept drinking forever because its
  zero-attention bid still cleared in an empty market; now zero-attention
  bids never clear, anywhere. (2) proposer starvation — dogfooding showed
  successful spawned scripts outcompeting their own proposer, fixed with a
  staleness drive. (3) dream-name collisions — found by test, fixed with
  generation-counted unique names.
- **The agents subpackage**: OpenAI-compatible providers (DeepInfra panel,
  `tencent/Hy4-preview` default), deterministic MockProvider,
  `StablePrefixSession` with token/cache journaling, and a safe audited
  action library (observe/note/search/message/rest) — the LLM enters as a
  citizen under the same conservation law, not as a god process.
- Five keyless examples, agent/scenario templates seeded from dogfooded
  ideation, the docs suite (8 guides + 4 tutorials), the build self-audit
  (25 claims, each with its test), and the dogfood journals from the
  Hy4-preview session that seeded the scenario catalog.

## 2026-10-31 — session three: recovery, CI, and the road to v0.3

- **Sandbox recycle cost the repo its `.git`.** Recovery: re-init, fetch,
  reconcile against the remote — the local tree was strictly ahead (204
  changed files, zero deletions), pushed as four grouped commits
  (`c978db7` kernel, `e1763fa` examples, `d72afea` docs + evidence,
  `78e2f03` tooling).
- **CI broke on `httpx`.** The teacher-layer tests import it; the
  "zero-dependency" claim was about the kernel, not the dev toolchain.
  Fixed honestly: `dev` and `llm` extras declared (`4fbc483`); the kernel
  itself stays zero-dep. All three Python versions green.
- **A forensic lesson worth pinning.** The CI workflow's branch filter
  looked corrupted (`branches: ain]`) through every lens — cat, grep,
  python repr, even the GitHub API — yet hex dumps proved the bytes were
  `[main]` all along: **the tool gateway's display layer eats the two
  bytes `[m` from output**, so `[main]` renders as `ain]`. Thirty minutes
  of "fixing" a file that was already correct. Rule adopted: *verify
  bytes via hex (od/jq-escaped), never raw display.*
- **Plan for this session**, in rounds: (2) re-attestation economics in
  the WHY kernel — the gap the live panel found independently; (3) live
  panel round 004 against the design, Hy4-preview with cache gaming;
  (4) pluggable attention arbitration with decision models; (5) honest
  archival; (6) examples 06–08; (7) the soak test; (8) v0.3.0.

### Round 3 — the red team gets its turn (live, cache-gamed)

- **Round 004 (live):** Hy4-preview attacked ADR-0007 for four iterations
  ($0.009 total; cache hits 0 → 128 → 512 → 896 — the append-only
  transcript is doing its job; 38% overall). Jev steered attack/attack/
  attack with severity holding at 2.93 ("serious, not design-breaking").
- **The triage:** hole 1 (ancestral piggybacking) was half-wrong —
  stamps go leaf→root, so parasites never ride siblings — but earned
  attestation **provenance** (`last_attested_by`); hole 2
  (UNKNOWN-washing: mass kill-and-revive cheaper than honest service)
  was real and is now fixed as **parole, not pardon** — revived nodes
  cap at justification 0.5 until a genuine win re-attests them; holes
  3–4 (UNKNOWN as bid veto; audits as scheduling primitive) were
  rebutted with the actual math (proportional discount; continuous
  freshness decay). All pinned by tests; the idle-revival receipt now
  reads 0.500 where it read 1.000 — the fix is visible in the wild.
- **Round 004b (live ideation, $0.0026):** Hy4 as research director
  proposed the next rounds. Adopted: **necrology replay equivalence**
  (replay the append-only log from genesis; reconstructed state must
  equal the live digest — conservation becomes proof-carrying) and
  **calibrated attention estimators** (lower-bound multiplication,
  Brier-logged — merges into the decision-model round). Deferred: sleep
  scheduler triggers (kept on the ledger).
- 143 tests green. Commit: this one.

### Round 4 — conservation becomes proof-carrying (ADR-0008)

- **Adopted from the ideation round**: the necrology replay equivalence.
  Every WhyTree now carries a genesis block (declarations as born), the
  necrology (transitions), and an attestation journal (every stamp with
  provenance) — together a complete replay basis.
- `ConservationAuditor.verify()` replays the basis from nothing and
  demands bit-for-bit equivalence with the living tree: states, heartbeats,
  provenance, parole. Receipts carry live/replay digests and a hash chain
  over the whole basis; `Runtime.save()` embeds the receipt in state.json,
  so a saved organism vouches for its own history.
- **Two honest limits found by the tests themselves:** same-tick reorders
  of independent records are outcome-equivalent and absorbed (the receipt
  proves outcomes, not byte-order); and a *superseded* stamp is invisible
  to state equivalence — which is why the chain covers the journal, not
  just the necrology.
- The replay semantics needed no schema change: every transition's effect
  is determined by its (from, to) pair — revive/resurrect land on parole,
  activate does not, lapse/kill/park touch state only.
- `make audit` prints a live receipt; 155 tests green (12 new).

### Round 5 — judgment enters the market, and gets scored (ADR-0009)

- **The integration boundary question is answered empirically**: decision
  models enter at exactly ONE bounded hook — the executive's tie-break
  among live contenders — with the veto law applied before they see
  anything and silent degradation to the deterministic shadow on any
  failure. Keyless default preserved.
- **Calibration is the immune system**: bids may claim `success_p`; the
  runtime scores every claim against the outcome. Live round 005
  (50 ticks, jev arbiter): 50 calls, 0 errors, **50 divergences** —
  the paid judgment is countable, not silent. The seeded overconfident
  scout (claims 0.90, truly 0.52) measured MISCALIBRATED at Brier 0.395;
  the humble archivist (0.40 claimed, 0.39 true) measured calibrated.
  Overall Brier landed exactly on the 0.250 coin-flip line.
- **Found and fixed live**: the typesafe choice question requires the
  `criteria` field (422 otherwise) — pinned by probe, folded into the
  adapter with the spec note; the first live run had silently degraded
  (every exception swallowed by the executive's catch), which taught the
  adapter to record `last_error` before raising.
- 167 tests green (12 new).

### Round 6 — cold storage that is not deletion (ADR-0010)

- OPEN_QUESTIONS #6 closed with an implementation, not an opinion.
  `ColdStorage` sweeps ancient DEAD subtrees out of the hot tree under
  conservative eligibility (dead > min_age, no ALIVE descendant, whole
  subtree together), balanced books (hot + archived == ever_declared),
  traveling biographies (the manifest carries full rows, verified by the
  conservation auditor against the replay basis), and a two-act
  restoration ceremony (restore-with-reason keeps the node DEAD and
  records it; resurrect-with-parole follows).
- **Found while testing:** the first restore only re-attached direct
  children, orphaning cold grandchildren — restoration is now transitive
  over the whole cold subtree. And the DEAD→DEAD restore record taught
  the auditor a new no-op transition shape, which replays cleanly.
- 177 tests green (10 new).

### Round 7 — the soak: everything at once, for a long time

- **10,000 ticks, one organism, every v0.3 mechanic active.** Receipts
  (seed 99): 2,327 ticks/s; 70,104 events; 60,000 attestation stamps;
  22 necrology records; the hot tree held at 11 nodes while cold storage
  took 15 (archival is doing its job); 4 lapses, 1 revive; full auditor
  verification every 1,000 ticks — zero failures; final verify 81 ms;
  6.8 MiB state saved, loaded, and re-verified from disk.
- Throughput degrades gracefully with journal growth (6.4k → 2.3k ticks/s
  from 2k → 10k ticks) — the O(journal) replay price is visible and
  honest; compaction is future work (ADR-0008 already flags it).
- Pinned: CI runs a 1,500-tick soak; the suite pins the invariants and
  bit-for-bit determinism (same seed → identical receipts). 179 green.

### Round 8 — the new mechanics become examples

- **06_attestation_economy**: the subscription model of purpose as a
  story — served vs unserved sibling, economic strangulation, double
  lapse, parole visible in the receipts (0.500 where v0.2 printed 1.000).
- **07_audit_and_archive**: the proof-carrying organism as a courtroom
  drama — valid receipt; flip a state off the books (caught); rewrite
  one word of history (chain head breaks); sweep the ancient dead to
  cold storage (books balanced, manifest verified); the two-act
  restoration ceremony; the whole story replays.
- All seven examples run keyless; 179 tests green; guard clean.
