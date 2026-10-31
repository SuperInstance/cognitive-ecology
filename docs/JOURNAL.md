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

### Round 9 — the expanded kernel meets its research director again

- **Live ideation round 009** ($0.0027, Hy4-preview, cache-first, the
  stable prefix now describing the complete v0.3 kernel): the v0.4
  frontier it proposed, ranked — (1) **SOCIETY-BASIS**, cross-organism
  WHY federation with foreign purpose references, a necrology exchange,
  and a federation auditor; justification becomes weakest-link across
  organisms (its pinning test is sharp: A's purpose served only by B
  lapses when B dies, with an exchange receipt on A's books); (2)
  **WHY-DAG**, multi-parent purpose with topological replay; (3)
  **OUTCOME-ARBITER**, scoring the delegated tie-break by realized
  outcomes. All three adopted into the roadmap.
- README refreshed for v0.3 (badge 179 tests, the subscription and
  proof-carrying framing in the intro, seven examples, ADR index, the
  v0.4 roadmap). OPEN_QUESTIONS ledger updated: #6 (honest archival) and
  #12 (formal conservation statement) CLOSED with their answers; #3
  advanced with the ADR-0009 result; #13 (journal compaction) opened.

## 2026-10-31 — session three: running totals

- **v0.3.0 shipped**: five major mechanics — re-attestation economics
  (ADR-0007), proof-carrying conservation (ADR-0008), decision-model
  tie-break + calibration (ADR-0009), honest archival (ADR-0010), and
  the soak that runs them all together.
- **Tests**: 121 → 179 (58 new, every one pinning a semantic found by
  design, play-testing, or a live red team).
- **Live calls this session**: 4 Hy4-preview ideation/red-team rounds +
  53 jev decision gates + 50 jev arbitrations. Session spend: ~$0.027.
  Cache gaming worked as designed — round 004's append-only transcript
  hit 58% cached tokens by its last iteration.
- **Commits this session**: 12 (recovery → v0.3.0).
- **Ledger movement**: OPEN_QUESTIONS closed #6 (honest archival) and
  #12 (formal conservation); advanced #3 (decision-model boundary);
  opened #13 (journal compaction). The v0.4 frontier is society-basis
  federation, WHY-DAG, outcome-weighted arbitration — proposed by the
  models that now live inside the kernel's own market.

### Postmortem: the red CI streak nobody watched

- v0.3.0 initially shipped with CI red on nine consecutive commits: the
  round-2 CI edit injected experiment steps with the *run-line* indent
  (8 spaces) instead of the *step* indent (6 spaces) — invalid YAML, so
  every run after `f4ca95c` died before executing a single job, and the
  failure was only noticed at release time. A second, real bug hid
  behind it: the soak smoke at 1500 ticks could not engage archival
  (killed purposes never reached min_age), which the parse failure had
  been masking.
- **Rules adopted:** (1) check CI after *every* push — "pushed" is not
  "green"; (2) YAML edits go through a parser check in the same command
  that writes them; (3) release tags point only at commits whose CI is
  green. The v0.3.0 tag now sits on the verified-green `a7789e3` line.

## 2026-11-01 — session four: the v0.4 frontier opens

### Round 10 — society-basis: purpose that crosses organisms (ADR-0011)

- **The design in one sentence**: treaties route attestation, and the
  v0.3 economics does the enforcing. A treaty is a foreign purpose
  reference — A's node served by B's node — and when B's runtime stamps
  B's provider chain, the society re-stamps A's beneficiary chain *on
  A's own books* with provenance `treaty:<id>`. Nothing else needed to
  change: freshness, lapse, parole, and the conservation auditor all
  compose with routed stamps for free, because a routed stamp IS a
  stamp.
- **Death vs neglect, hard vs soft**: B's provider purpose dying
  (DEAD or UNKNOWN transition) breaks the treaty and QUESTIONS A's
  node — the new `question()` transition (ALIVE→UNKNOWN, recorded, no
  cascade, revivable) — but only when the treaty was the node's sole
  basis. B merely going quiet propagates through A's own reaper: the
  stamps stop, the freshness decays, A's horizon does the rest. Known
  broken is not doubtful; the UNKNOWN epistemology now spans organisms.
- **The pinning test is green**: "A's purpose served only by B lapses
  when B dies, with an exchange receipt on A's books" — exactly as the
  round-009 adoption note demanded, plus the receipts: the question
  record names the treaty, an EXCHANGE event lands on both buses, and
  A's own conservation receipt still replays.
- **The federation auditor** lifts ADR-0008 one level: not "do these
  books replay" but "do these books AGREE." Forged service (a
  treaty-provenance stamp with no matching provider stamp at that tick)
  and missed propagations (an active treaty with a dead endpoint) are
  both caught and pinned by test.
- **Found while testing — the cursor bug**: the exchange originally
  advanced its journal cursors to the full log length, which included
  the stamps it had just routed — delegated service was consumed
  instead of flowing onward, and delegation chains (C serves B serves
  A) silently died after one hop. The fix (cursors advance by exactly
  the frozen slice length) makes one-hop-per-exchange a real invariant
  rather than a docstring claim, and keeps cycles safe by construction.
- **Also found**: a sole treaty breaking questions A's node, so
  re-establishing requires A's `revive()` ceremony first —
  UNKNOWN-washing now applies to treaties, not just purposes. Pinned.
- Kernel surface: one transition (`question`), one event kind
  (`EXCHANGE`), one new module (`society.py`, zero new deps). 198
  tests green (19 new).

### Round 11 — the society under attack (live red-team, round 011)

- **4 iterations of Hy4-preview ($0.0086, 47% cache hit), jev-gated**
  (steer ×3, severity ×3: the gate said "repair" twice, then "attack"
  again — the panel smelled blood and was right).
- **Adopted (1): sole-ness is a fact, not a declaration.** The shield
  treaty hole: declare `sole_basis=False`, dodge hard propagation when
  your only servant dies. The fix derives sole-ness from the journals —
  a provider death questions the beneficiary node unless another
  servant (an ACTIVE treaty that actually routed service, or a local
  component) ever stamped the node ITSELF. Ancestor stamps don't count:
  a sibling's win stamps the shared root without serving this node.
  Pinned by three tests: the lie, the dead-weight shield, and the
  honest second servant that still stands.
- **Adopted (2): doubter provenance.** `question()` records WHO
  doubted (`by="society"` from the exchange; unnamed challengers are
  recorded as such). The books no longer just say a purpose was
  questioned — they name the doubter.
- **Found while repairing: the one-exchange window.** A question
  written mid-exchange (treaty 1's break) left treaty 2 still ACTIVE
  on a dead endpoint until the next exchange — caught by our own
  federation auditor in the dead-weight test. The exchange now ends
  each treaty with a live endpoint sweep: no treaty walks out of an
  exchange active with a dead endpoint. This also self-heals missed
  propagations from manual (non-lockstep) drivers.
- **Rebutted with the math**: the "permanent freshness via shield
  treaty" claim fails on its own terms — a treaty that never serves
  contributes zero stamps, and the node still decays and lapses on its
  own books. Freshness-laundering (are the provider's actions
  genuinely serving?) is the same boundary round 004 drew for single
  organisms: stamps bind to winning acts with outcomes; semantic
  service quality is the audited action library's jurisdiction.
- **Opened on the ledger: #14, the WHY mutation surface** — the
  snapshot exposes the live tree, so a component can kill or question
  a competitor's purpose with a legitimate-looking record. Provenance
  vs capabilities vs trust: a real design question, honestly asked.
- 202 tests green (4 new); guard clean; round receipt committed.

### Round 12 — example 08: the society as a story (and what the story found)

- **The new mechanic became the eighth keyless example**: three
  organisms — a researcher leaning on two archives — living the whole
  life of a delegation. ACT 1 the treaty works (service lands on A's
  books with provenance `treaty:1`); ACT 2 neglect is soft (B goes
  quiet, nobody dies, A's own reaper lapses the node — the receipt is
  a Lapse record, doubt that grew at home); ACT 3 death is hard (C's
  provider purpose killed; same step: treaty broken, A's node
  questioned, receipt naming treaty + cause + doubter); ACT 4 every
  receipt verifies — per-organism conservation AND the federation's
  books-agree check, with the append-only treaty ledger showing
  broken-is-forever.
- **The play-test caught a real cross-layer bug on its first run** —
  the repo's thesis doing its job. The conservation auditor's replay
  ordered same-tick entries as stamps-before-transitions (correct for
  the runtime's act -> stamp -> reap), but the society introduced a
  legitimate order the replay could not express: manual revive at tick
  t, then a treaty-routed stamp landing at the SAME tick t. The replay
  applied the stamp while the node was still UNKNOWN -> false
  stamp_validity failure. 202 tests had not covered it; one narrative
  example did.
- **The fix is a three-phase equal-tick ordering in the replay**:
  to-ALIVE transitions (phase 0) -> stamps (phase 1) -> all other
  transitions (phase 2). This matches every real order in both layers,
  including the exchange's break-then-route (a questioned node REFUSES
  its stamp, so a stamp never follows its own question — the ordering
  is total, not heuristic). Pinned by a focused regression test.
- 203 tests green; example 08 in the README table; ADR-0011's replay
  semantics note updated.

### Round 13 — the WHY DAG: purpose with several parents (ADR-0012)

- **Best-path semantics (OR)**: a purpose declared with
  `parents=(a, b)` runs while ANY path to a root is fully ALIVE, and
  its justification is the strongest path's score. The round-009
  pinning test is green verbatim: kill A, C survives on B; kill B too,
  C dies (questioned, never deleted). Freshness follows the same rule
  — served through either parent, fresh through that parent — and
  probation caps apply per path, so a paroled lineage only drags down
  the paths that use it.
- **Cascade by surviving path, with a fixpoint.** No over-cascade: a
  kill questions only descendants with no surviving fully-alive path
  (a surviving parent's lineage shields the child). No under-cascade:
  cross-linked topologies — where a node's last living path runs
  through a *descendant* that cascades later in the same sweep — are
  settled by re-checking survivors until a full pass cascades nothing.
  The revive cascade mirrors it: an UNKNOWN descendant returns iff its
  ancestors on some path are all ALIVE.
- **Contradictions now require destroyed warrant**: ALIVE, no
  fully-living path, AND a DEAD ancestor. Doubt (UNKNOWN ancestors)
  is questionable, not contradictory; a living path through another
  parent is warrant, not dissonance. Trees reduce to the v0.2 rule
  exactly.
- **The whole v0.3 suite passes unchanged** — 203 pre-existing tests
  green without touching a line, including the tree-cascade-order
  pin (BFS, bit-for-bit) and the 2000-tick soak. The genesis row
  grew a parents tuple (v0.3 rows normalize on load); the auditor
  replays DAG bases and catches off-books re-parenting; cold storage
  sweeps and restores DAG subtrees through any parent edge; treaties
  may delegate multi-parent purposes (the service check walks every
  parent edge).
- **Found while testing**: my first revive-cascade rule ("a dead
  parent anywhere blocks the cascade-revive") was too conservative —
  under OR semantics a resurrected parent DOES restore the child's
  warrant (the mirror of the kill rule the pinning test demands).
  The correct rule: would the node have a fully-living path if it
  were ALIVE? Plus a fixpoint, because DAG parents can revive in the
  wrong order for a single pass.
- 220 tests green (17 new); ADR-0012 written; OQ #1 CLOSED with an
  implementation, not an opinion.

### Round 14 — the outcome-arbiter: paid judgment must earn its keep (ADR-0013)

- **Divergence is not value.** ADR-0009 counted how often the arbiter
  disagreed with the deterministic shadow; round 005 measured 50/50
  and could not say whether that was worth anything. The scorecard
  (kernel, zero-dep) closes OQ #3's remainder with three scores where
  there was one: the arbiter's picks are probabilistic claims in the
  SAME calibration immune system as component claims; its overrides
  are compared against the action base rate; and either a
  miscalibrated or value-destroying arbiter is BENCHED after a
  window — never consulted again, announced once as a DECISION event,
  receipt naming the numbers.
- **The live run is the best receipt yet**: jev arbitrated a
  4-contender organism for 60 ticks under the scorecard. 25 calls, 25
  divergences, 0 errors. The VALUE test did not fire — overrides
  succeeded at 0.72 vs the 0.66 base rate; the judgment was slightly
  better than the shadow's ordering. The CALIBRATION test benched it
  at tick 25 (Brier 0.307): jev chose decently but could not price
  its own choices. Three different scores, three different stories —
  divergence count alone would have called the run a disaster and
  been wrong about why.
- The wiring is minimal: the executive exposes
  last_arbiter_context, the runtime scores the pick that acts,
  scorecard=None keeps exact v0.3 behavior (keyless default
  preserved), and the scorecard persists with the organism while the
  arbiter callable stays code.
- 228 tests green (8 new: confident-and-wrong benched, calibrated
  keeps its job, value-destroying benched, benching degrades to the
  shadow with exactly one announcement, window prevents snap
  judgments, persistence roundtrip, veto-guard survives the wiring).

### Round 15 — journal compaction: the replay basis without the ballast (ADR-0014)

- **The soak's honest price, paid back.** 60k journal entries at 10k
  ticks, verify O(journal), throughput 6.4k -> 2.3k ticks/s. The fix
  keeps the last stamp per (node, ALIVE window, PROVENANCE): exact
  replay equivalence (live digest == replay digest, pinned), each
  servant's evidence survives for the society's effective-sole check,
  and the measurement is dramatic — 4 journal entries across 10
  epochs of 1k ticks, verify ~0 ms flat.
- **Receipted, never silent.** Compaction is a storage transition
  like archival: every one appends a CompactionReceipt (counts,
  dropped digest, chain before/after) to an append-only list, the
  auditor's hash chain covers the receipts, and a lying receipt fails
  the new compaction_accounting check. The pre-compaction chain head
  stays pinnable; the federation auditor's service check spans only
  the uncompacted history, bounded by BOTH books' cutoffs.
- **The necrology is never compacted** — it is the transition record
  and the replay's authority for ALIVE windows; compacting it would
  change semantics, not storage.
- 238 tests green (10 new: bit-for-bit replay equivalence, repeated
  compaction stability, per-provenance survival, kill/revive windows,
  receipt tampering caught, persistence, effective-sole under
  compaction, cross-organism derivability under compaction, bounded
  verify cost); OQ #13 CLOSED; the 3000-tick soak holds.

### Round 16 — the society soak, the bug it caught, and v0.4.0

- **The society soak** runs three organisms in lockstep — a researcher
  leaning on two archives — through the whole delegation life cycle:
  service on A's own books, hard propagation when B's provider purpose
  is killed (treaty broken, A's purpose questioned with a receipt),
  revival, re-delegation to C, service through the end. Per-epoch
  journal compaction on all three books; federation + conservation
  audits every epoch. Receipts: 1,398 ticks/s lockstep, journals
  bounded at 9/4/4 entries across epochs, 48 audits green,
  save/load with the embedded receipt.
- **The soak caught a real integration bug on its first full run**:
  journal compaction (round 15) shrank a provider's journal past the
  exchange's positional cursor — every slice came back EMPTY until the
  journal regrew past the cursor. A ~500-tick silent service gap; the
  beneficiary starved and lapsed at tick 925, before the provider was
  even killed at 2000. The receipts told the story (treaty:1 "broken:
  beneficiary purpose unknown (lapsed)" at 925) — the ledger found the
  bug before we did.
- **The fix is two-part**: monotonic heartbeats (a stamp carrying a
  tick older than the node's current last_beat is a no-op — stale
  information must never rewind freshness, which makes re-consumption
  idempotent) and epoch-aware cursor resync (cursors track each
  member's compaction count and the last consumed entry; on mismatch
  they relocate that entry in the compacted journal, or re-consume the
  tiny journal from the start). After the fix, the soak tells the
  designed story exactly.
- **v0.4.0 released**: society-basis federation (ADR-0011), the WHY
  DAG (ADR-0012), the outcome-arbiter (ADR-0013), journal compaction
  (ADR-0014); versions bumped; README refreshed (240 tests, L9 in the
  stack, the v0.4 status paragraph); society soak smoke pinned in CI.

## 2026-11-01 — session four: running totals

- **v0.4.0 shipped**: four major mechanics in one session —
  society-basis federation, the WHY DAG, the outcome-arbiter, journal
  compaction — plus the red-team hardening (sole-ness as fact, doubter
  provenance, the live endpoint sweep) and the three-phase replay
  ordering found by the example-08 play-test.
- **Tests**: 179 → 240 (61 new, every one pinning a semantic found by
  design, play-testing, a live red team, or a soak).
- **Live calls this session**: round 011 (Hy4 red team, 4 iterations,
  $0.0086, 47% cache hit) + round 014 (jev outcome-arbiter, 25 gated
  decisions). Session spend: ~$0.02.
- **Bugs found by our own instruments**: the cursor bug (routing died
  at the first compaction — found by the society soak), the
  same-tick-replay ordering (found by example 08), the one-exchange
  dead-endpoint window (found by the federation auditor in a test).
  The thesis keeps working: receipts find what reviews miss.
- **Ledger movement**: OPEN_QUESTIONS closed #1 (WHY-DAG), #3
  (decision-model boundary, fully), and #13 (journal compaction);
  advanced #5 (multi-organism societies); opened #14 (the WHY mutation
  surface). The v0.5 frontier: cross-organism attention markets,
  society replay equivalence, arbiter re-promotion, weighted DAG
  parents — and whatever the next play-test finds.

## 2026-11-01 — session five: the developers' turn (wave-1)

The directive changed lens: build for the developers and users who will
harness this with their applications; deep play-test as many types of
users and engineers as possible, iteratively; use zero-shot helpers for
fresh perspectives. So wave-1 was **six independent cold personas**,
each self-contained, each judging as a real user with a real
application: Sam (hobbyist, a digital pet for his notes), Priya
(senior backend, SaaS background jobs), Morgan (10-year game dev,
NPCs), Kai (ML/agent engineer), Ana (computational researcher), Dana
(staff engineer doing diligence). All six ran code, measured, and
attacked; all six verdicts landed at **PILOT 6.5–7/10** — the core
holds, the integration layer is thin. The wave-1 ledger, ranked:

1. **Fail-safes with holes** — FIXED round 17 (same push): `bid()`
   explosions killed the whole tick loop; a malformed arbiter ANSWER
   crashed the organism at `chosen[0].label`. The docs promised
   "degrades, never crashes"; only exceptions ever did.
2. **Persistence not trustworthy end-to-end** (Priya's top one): save
   is non-atomic (a torn write destroys the only checkpoint), `load()`
   never verifies the receipt it carries, `events.jsonl` is rewritten
   whole on every save, and failure reasons were computed then thrown
   away (the log recorded THAT, never WHY).
3. **The organism is invisible** (Ana's top one): the five attention
   factors — the platform's core scientific object — are never logged;
   telemetry has no provenance (no seed/config echo, orphaned files);
   no experiment harness above single runs; sleeper stats dropped on
   save.
4. **No host-integration story** (Sam's top one; Priya's tick
   question; Morgan's game loop): `rt.bus.emit` is undiscoverable;
   wall-clock/schedulers are everyone's first build; the
   cron/game-loop/FastAPI patterns are folklore, not docs (this IS
   OPEN_QUESTIONS #7, seen from the user side).
5. **Stale numbers everywhere** (Dana's diligence): the README
   contradicted itself (240 vs 121 tests, seven vs eight examples,
   "v0.2.0, the subject of this README"), CHANGELOG had no 0.4.0
   entry, `pip show` said 0.3.0, PROCESS.md pins a Rust golden corpus
   that is not in this repo.
6. **attach() is a rite of passage** (Priya/Morgan): re-declaring
   raises; live scripts are not restored by `from_json`; the real
   pattern lives only in examples — wants idempotent `ensure_*` + a
   migration page.
7. **The safe seam has soft edges** (Kai): prefix stability is
   advisory, not enforced; duplicate proposals count as accepted
   (population bloat); one-shot search scripts never die of starvation;
   no ScriptedProvider for CI; `rest` accepts `"nan"` (saved only by a
   lucky `max()` clamp); v0.1's circuit breaker/retry hardening never
   ported to the line that superseded it.
8. **Examples that teach lossy patterns** (Morgan): example 04 reads
   player questions from `ctx.recent(10)` racing the top-k scheduler —
   a real ask provably never reached the graph; asks must be persisted
   into the graph in `player_visit`.
9. **Smaller bites**: `walk()` on an isolated node returns `[]` (recall
   silently fails for unlinked facts); `starved` names dropped in
   telemetry (`starved_n` only); `born` resets on load; the save
   `version` field is written but never checked; the modding trust
   boundary is undocumented (OQ #14); `starved_n` vs "starved" doc
   drift.

### Round 17 — fail-safe totality + the wave-1 truth pass

- **The two production-fatal holes, closed.** `bid()` is now contained
  exactly like `act()`: a raising bid, a non-iterable, a junk-bearing
  list — each is an ERROR event with its reason, and the component
  proposed nothing that tick (its scripts starve on their own
  economics; the other organs are untouched — pinned by a twin-run
  identity test). A failed action's `Outcome.note` now rides its own
  cause-chained ERROR event; NOTE_ON stays a 2-tuple. And the arbiter's
  ANSWER is validated like its exceptions were: anything that is not an
  ordered subset of the very bids it was shown (wrong types, a foreign
  look-alike, duplicates) is a failed answer — degrade to the
  deterministic shadow, count it in `arbiter_malformed`, record it.
  Recovery is per-tick, not a scar: a flaky arbiter that speaks
  properly again is trusted again (benching remains the scorecard's
  business, judged by outcomes, never by protocol stumbles).
- **17 new tests** (`tests/test_failsafe.py`): every bid() failure
  mode, the reason channel, all seven malformed-answer shapes,
  twin-run shadow identity, determinism while failing, and recovery.
  240 → 257.
- **The truth pass rode the same push** (never ship a self-contradicting
  README): all numbers made true (257 tests, eight examples, 176+81
  split, v0.4.0 line, CHANGELOG 0.4.0 backfilled with an honest note,
  pip metadata refreshed, INDEX/Makefile/AUDIT/CONTRIBUTING swept);
  AUDIT's two now-false limitations replaced with the true ones (the
  DAG shipped; archival shipped). The quickstart BLOCKER is fixed
  (`Tiny(rt)` crashed on first copy-paste — `Tiny()` now) and its
  tensions now print a sawtooth, not a pinned zero: relief is
  threshold-gated, so the doc teaches homeostasis by showing it.
  Verified by executing the doc's code verbatim
  (`scripts/verify_quickstart.py` pattern — docs code must run, not
  read pretty).
- **Tooling lessons for future sessions** (the `[m` family): the edit
  layer EATS TABS — Makefiles must be patched via `sed`, never the
  edit tool; and a multi-edit here applies earlier edits before
  reporting a later miss, so re-grep the file after every batch.
- **Next rounds, from the ledger**: 18 — the machine-checked truth gate
  (`scripts/check_docs.py` in CI: CHANGELOG-top == pyproject version,
  every README count generated from the tree; PROCESS/AUDIT full
  reconciliation); 19 — persistence trustworthiness end-to-end (atomic
  temp+rename saves, `load()` verifies the receipt at the door,
  bounded event retention); 20 — the measurable organism (per-tick
  market log with the five factors, run manifests, seed sweeps in
  `run_rounds.py`); 21 — host integration (tick drivers + recipes:
  cron, game loop, FastAPI lifespan; example-04's lossy read fixed);
  22 — the safe seam (orchestrator/provider hardening, ScriptedProvider,
  duplicate-rejection economics); then wave-2 re-play-test with fresh
  personas to verify it all landed as experienced.

### Round 18 — the machine-checked truth gate

- **`scripts/check_docs.py` + `make truth` + a CI step.** Dana's top
  one, delivered: version coherence (CHANGELOG's newest numbered
  section must equal pyproject's version) and every documented count
  (tests, examples, ADRs, tutorials, guides) checked against the tree
  on every push. Prose numbers rot; checked numbers cannot.
- **The gate proof-demonstrated itself inside its own round, twice.**
  First run caught a live drift nobody had noticed (INDEX claimed the
  shared docs/ADRs holds 6 records from the v0.1 line; it holds 14 —
  0001–0006 are that line's era). Then adding the docs-code test
  rippled the test count 257 → 258 through five doc claims, and the
  build refused to pass until every one was updated. That is the whole
  point: the contradiction Dana found becomes a build failure instead
  of a trust question.
- **The quickstart's code block is now executed as a test**
  (`tests/test_docs_code.py`): extract the ```python block from
  docs/01, exec it, assert the sawtooth and the conservation law. A
  doc can never again rot into a `Tiny(rt)`-class crash — the class of
  bug that shipped for days and hit every cold user in minute one.
- **PROCESS.md reconciled with reality**: the golden corpus is real
  (`tests/corpus/`, run by `tests/test_why_corpus.py`) — the "Rust why
  + Python port" pairing was external prior work, now stated as the
  corpus pinning semantics; the secrets bullet now describes what CI
  actually does (history-wide scan), not what a script no longer
  wires; a docs-truth rule joined the road list.
- **AUDIT.md untangled**: header spans v0.2.0 → v0.4.0, rows 52–57
  added (society federation, the WHY DAG, the outcome-arbiter, journal
  compaction, fail-safe totality, docs truth — each with its test
  file), and the three-era count paragraph replaced by one true
  sentence: 258 = 177 kernel + 81 v0.1, machine-checked every push.
- 258 tests (257 + the docs-code gate); CI runs the truth step before
  the kernel tests on all three matrix versions.

### Round 19 — live ideation 015: the wave-1 ledger through outside eyes

- **Three slices on Hy4-preview** (~$0.019; spec bumped to v0.4 so the
  first call re-primes the cache — a deliberate, receipted cache-bust):
  the seventh engineer, the round ranking, the hidden assumptions, the
  symptom diagnosis, and the retention verdict. Full texts in
  `library/rounds/015-*.md`; provenance in the dogfood journal.
- **The seventh engineer we did not cast** (operator/SRE): the kernel
  is "a correct organism with no physiology" — no resource envelope,
  no health surface, no tick-duration contract, no multi-process
  guard, no export hatch, and sleep prunes only when idle (the safety
  valve exists only when there is no pressure). Opened as
  OPEN_QUESTIONS #15 rather than promised as a layer.
- **Triage accepted in full**:
  - ranking A > C > B > D — the build order stands;
  - **round 20 reshaped**: event retention is **snapshot+delta**, not
    a ring buffer, not plain truncation — the snapshot is a compacted
    state root under receipts, deltas are the ordered stream since
    that root, and pre-snapshot ranges are truncated only after the
    snapshot proves exact replay equivalence. Pinning test named:
    bit-identical replay equivalence through a snapshot+truncate;
  - **round 21 reshaped**: the market log must be a READ MODEL — it
    serializes the exact floats of the very bids the market cleared
    (no re-computation, no rounding at write time), never a second
    source of truth; run manifests carry the provenance;
  - **round 22 note**: host drivers ship with a declared cost note and
    determinism guidance — recipes must not make the missing
    physiology load-bearing silently;
  - **round 23 note**: duplicate rejection must count at the ecology
    layer too (a rejected duplicate is a demotion in L4), not only at
    the proposal seam.
- The symptom diagnosis: **finding 3 (the invisible organism) is the
  design gap** — the kernel lacks a first-class observation boundary /
  read model, which is why every later need arrives as a bolted-on
  feature. Round 21 is that read model, built on the exact-values
  discipline above.

### Round 20 — persistence trustworthiness, part one: the door (20a)

- **Every Priya probe, closed.** `save()` is atomic (temp + os.replace;
  a crash mid-write leaves the previous checkpoint byte-intact, no torn
  temp behind — pinned by a test that explodes json.dump mid-write).
  `events.jsonl` is append-mode: each save appends only the delta, so
  the file is never rewritten whole again (the 94 ms autosave hitch at
  19k events is gone; the first save's bytes are a byte-identical
  prefix forever after — pinned).
- **The bus grew a chain** (`EventBus.chain_head`): a fold of every
  event row in seq order, maintained on emit (one sha256 per event,
  ~19/tick) and rebuilt on from_jsonl. Zero bytes added to any event —
  the chain lives on the bus, not in the rows; the MIDI-size budget is
  untouched. save() records the head; load() refuses a file that folds
  to anything else — edits, drops, splices, and the interrupted-save
  window (events appended, state.json not yet replaced) are all caught
  by name. The watermark check runs first (cheaper, names the window);
  the chain check catches count-preserving edits.
- **The conservation receipt is recomputed at the door, never
  trusted** — the tampered-state probe that used to boot silently now
  raises with the failing check. Pre-20a saves still load (their states
  carry no head/watermark; the conservation door covers them) — compat
  by absence, not by exception.
- **Smaller bites landed with it**: sleeper stats + idle_window now
  persist (the researcher persona's dropped dial); an adopted script
  keeps its saved born (the tick-0-born save-compat bug — `_register`
  no longer re-stamps adopted biographies); load() passes the saved
  idle_window into the sleeper instead of silently defaulting it.
- **The attach() rite of passage is now documented in code**: the
  round's tests carry the guarded-attach workaround (has()-checks
  before declare/add) with a note that the real fix — idempotent
  `ensure_*` + a migration page — is round 23.
- **Part two remains (20b)**: bounded retention via snapshot+delta
  (the 015 verdict) — the events file still grows forever; that is the
  next round, along with rotating checkpoints for hosts.
- 268 tests (258 + 10); truth gate rippled 258 → 268 through five doc
  claims exactly as designed.

### Round 20b — bounded retention: snapshot+delta, the 015 verdict

- **`Runtime.compact_events(path, keep=N)`**: truncate the event log to
  the most recent N events — but only after a full snapshot (the call
  saves first) proves the state at that tick. Never truncate an
  unverified basis; the refuse-on-broken-receipt path raises rather
  than drops.
- **The anchor** (`EventBus.chain_anchor`): the dropped prefix is
  folded, in order, into a value recorded in the state. The chain
  invariant becomes chain_head == fold(anchor, retained...) ==
  fold("genesis", ALL rows ever) — sequential hash chains are
  associative by construction, so a truncated file folds to exactly
  the head the full history would have produced. The door does not
  weaken: editing an event deep inside the RETAINED region is still
  caught (pinned), and double compaction composes (anchor2 =
  fold(anchor1, slice2) — pinned).
- **The 015 pin landed and is green**: a life that compacts at tick 200
  and runs to 300 is bit-identical to an un-compacted twin — same ran
  sequences, same tensions, same conservation live_digest, same graph
  digest, same necrology. Compaction is storage-only, never
  behavioral. (The first draft of the pin had the wrong arithmetic —
  the loaded bus holds retained + post-compaction tail, not the bare
  keep; the machinery was right and the test was wrong. Fixed.)
- 273 tests (268 + 5); the events file is now bounded at host-chosen
  epochs. Rotating checkpoints for hosts remain a recipe to document
  in the host-integration round (22).

### Round 21 — the measurable organism: the read model ships

- **The design gap, closed as architecture.** Finding 3 ("the organism
  is invisible") was diagnosed by ideation 015 as the absence of a
  first-class observation boundary. `marketlog.py` is that boundary:
  a READ MODEL over the attention market, wired into every Runtime
  (constructor and load), fed by the executive after every decision is
  final. One row per bid per tick: the exact five factors, the
  attention product, resource, claimed success_p, and the market's
  verdict — run / yield / starved / VETOED, with vetoed finally
  separated from starved (the event stream mixes them; the read model
  does not). Arbiter rows appear only when the arbiter truly
  arbitrated — a degraded or uncontended judgment writes nothing.
- **The three laws, pinned before they were promises**: exact
  (bit-for-bit float roundtrips through json — the test uses
  `0.1 + 0.2` and `1/3`, and the first draft FAILED its own discipline
  by rounding clear_rate in summary(); the test caught its own
  author), not a second source of truth (rows serialize the market's
  ClearResult and the executive's Decisions), non-perturbing
  (bit-identical twin runs, log read every tick vs never touched; and
  the entire pre-existing 273-test suite passed unchanged with the log
  wired in — the cheapest non-perturbation proof available).
- **`veto_reasons()` is the docs promise, evidenced.** "Fix the
  factor; don't bypass the market" now comes with WHICH factor was
  zero, in the market's own stored floats. Writing its test surfaced a
  truth worth pinning: the script ecology pre-gates zero-justification
  scripts upstream of the market, so vetoed rows can only come from
  components that submit raw bids (LLM proposal agents, custom
  components) — the veto law protects the market no matter who
  speaks. The test documents it.
- **Provenance: runs can no longer be orphans.** run_rounds.py writes
  a manifest per run (kernel version, python, platform, git commit,
  seed, config, wall time, sha256 of every output) and now emits
  `market.jsonl` alongside telemetry. `--sweep N` aggregates mean ±
  spread per metric across seeds — and its FIRST USE found that
  minimal_world is seed-invariant (three seeds, one event stream;
  nothing in the demo consumes randomness). The instrument calibrated
  itself on day one; the finding is documented, not silently
  "fixed" (changing the demo's rng use would destabilize pinned
  determinism tests for no user gain).
- **ADR-0015** records the decision and the deferred follow-ons
  (push-stream sinks, factor histograms, the physiology round
  consuming summary() as its health surface). docs/09_market_log.md
  is the user-facing guide; truth gate rippled 273→290 tests and
  14→15 ADRs through every doc claim exactly as round 18 designed.
- Memory discipline: the in-memory log is a bounded tail (keep=100k
  default), never rides in state.json, fresh on load — observation
  history belongs to the observer, not the organism.
- Next, per the ledger: **round 22 — host integration** (tick drivers
  + recipes: cron, game loop, FastAPI lifespan; example-04's lossy
  read; rotating checkpoints; declared cost notes), then **round 23 —
  the safe seam + attach() ergonomics** (ensure_*, migration page,
  duplicate rejection at the ecology layer), then **wave-2** fresh
  personas to verify it all landed as experienced.

### Round 22 — host integration: folklore becomes law (and bites back twice)

- **The contract first.** "A driver owns WHEN. It must never influence
  WHAT." `drivers.py` is the seam: `WallClockDriver` with injectable
  sleep/monotonic (tests drive a "3-second session" in microseconds),
  drift-free absolute-slot pacing, graceful Ctrl-C, host stops via
  `on_tick(...) is False`, a `save_every` checkpoint cadence with no
  redundant final write, and a `DriverReport` receipt (ticks, wall
  seconds, stopped_by, saves, mean tps). The contract is pinned the
  only way contracts deserve pinning: a driven life is bit-identical
  to `rt.run(n)` — same seed, same stream, driver or no driver.
- **The round bit its own builders, twice, honestly recorded.**
  1. Example 09's frame-rate twin (60 fps vs 30 fps must produce the
     same life) FAILED its own printed claim: summing 1/30 ninety
     times gives 2.9999999999999994, and the epsilon-free accumulator
     silently dropped the third tick. The epsilon is now in the
     recipe with the scar visible (docs/10 § "the accumulator's
     epsilon").
  2. The driver's first version doubled the FIRST interval (next_at
     off-by-one: tick 1 at t=0, tick 2 at 2Δ). The injected clock
     made it visible as 60 ticks where 61 belonged; the test caught
     what a real-clock smoke test would have shrugged at as jitter.
     Both fixes shipped before the demo ever claimed to work.
- **The world-not-bus ingest law.** Example 04's lossy read (wave-1
  finding 8) is fixed at the pattern level: player asks are persisted
  into the WORLD GRAPH at ingest time; the bus may narrate, but the
  graph remembers. An ask Merle never answered now survives restarts,
  gossip works the unanswered queue in order, and the law is written
  into docs/10 where every host will read it. Pinned by
  tests/test_example04_asks.py, including the no-attention-was-ever-
  spent case and the restart case.
- **docs/10_host_integration.md**: host-surface table (tick/run/
  bus.emit/graph.upsert/save/load/market_log), four recipes (game
  loop, wall-clock session, cron tick with the attach rite shown in
  full, FastAPI lifespan), rotating checkpoints (the 20b deferral,
  closed as a recipe), and the declared cost/determinism notes from
  ideation 015 — including the honest pointer that the kernel has no
  resource envelope yet (OQ #15) so drivers must set budgets and wear
  external watchdogs. check_docs.py's guide glob grew to two digits
  (`[0-9]*.md`) — guide 10 broke the checker's assumption, the
  checker told on it immediately, which is the system working.
- 306 tests (290 + 16); truth gate rippled through every claim.
- Next: **round 23 — the safe seam + attach() ergonomics** (idempotent
  `ensure_*` builders, the migration page, duplicate-rejection
  economics at the ecology layer), then **wave-2** fresh personas.

### Round 23 — the safe seam: the attach rite, de-rited; bloat, over

- **ensure_* is the rite, made law.** Priya and Morgan's finding 6
  ("attach() is a rite of passage") closed at the layer that owns it:
  `ensure_why` (idempotent by node_id; a statement MISMATCH raises —
  an id means one purpose, forever), `ensure_tension` (never resets a
  saved drive's level — the state file answers for levels, not the
  code), `ensure_component`, `ensure_script` (rehydrates saved track
  records). The pinned test is the whole point: the rite runs TWICE,
  painlessly, no guards. The old guarded pattern and the new one are
  translated side by side in docs/MIGRATIONS.md, which also states the
  compatibility law the code already lives by: newer readers accept
  older states by absence; proofs are re-derived at the door, never
  trusted from disk.
- **Duplicate rejection at the ecology layer (the 015 note, done).**
  `behavior_signature`: owner + action + args + when_hint — the NAME
  is not the behavior. `spawn_unique` rejects an exact live duplicate
  and returns it; rejections are counted, tailed (bounded at 200),
  and — the part that makes it economics rather than policy — the
  orchestrator's accept_rate counts spawns only, so a model that
  keeps re-proposing the same script watches its propose bid's
  expected value decay until it starves. The old `name~tick` variant
  hack (which MULTIPLIED duplicates: every re-proposal became a new
  clone) is deleted. The demotion is also visible to the demoted: an
  ERROR event on the bus, which the model reads in its next proposal
  turn's recent-events window. Kai's population-bloat finding is
  closed at both the seam and the layer.
- **The nan hole, closed twice.** `rest` with amount nan used to slip
  through to relieve(), where `max(0.0, nan)` silently zeroed the
  tension — a free lunch the wave-1 red team ordered. Now the action
  library rejects non-finite amounts with an honest note, AND the
  kernel (relieve/burden) no-ops them: the seam is polite, the kernel
  is incorruptible. Defense in depth, pinned at both layers.
- 324 tests (306 + 18); docs 03 and 06 updated; MIGRATIONS.md added
  (not a numbered guide — meta-doc, like PROCESS).
- Next: **wave-2** — fresh personas re-play-test the whole wave
  (17–23) to verify it landed as experienced, not just as tests.
