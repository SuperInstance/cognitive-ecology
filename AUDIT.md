# AUDIT

Two sections: the **build self-audit** (what the build claims, and the
test or run that backs each claim), and an **external audit** section kept
ready for a reviewer.

## Build self-audit — v0.2.0 → v0.4.0 (rows 1–51: the v0.2/v0.3 builds; rows 52–57: v0.4 + round 17; all still pinned by the same tests)

Every load-bearing claim in the docs, with its evidence:

| # | Claim | Evidence | Status |
|---|---|---|---|
| 1 | WHY nodes are never deleted; conservation invariant holds under arbitrary operations | `tests/test_why.py::test_conservation_survives_random_storm` (500 random ops, 31 nodes) + runtime audit every 25 ticks | ✅ tested |
| 2 | Kill cascades descendants to UNKNOWN (questionable), not deletion; revival cascades back | `test_kill_cascades_to_unknown_never_deletion`, `test_revive_after_ancestor_resurrect` | ✅ tested |
| 3 | Resurrection requires substantive evidence | `test_resurrect_requires_a_reason` | ✅ tested |
| 4 | Contradictions (ALIVE over DEAD) are representable and detectable | `test_contradictions_detectable` | ✅ tested |
| 5 | Events are immutable, append-only, causally chained, ~MIDI-sized | `tests/test_events.py` (frozen dataclass, jsonl round-trip, `<160 bytes` budget test) | ✅ tested |
| 6 | World graph is append/decay-only; deletion API raises by design | `tests/test_graph.py::test_forget_raises_by_design`, `test_decay_never_deletes` | ✅ tested |
| 7 | Graph digest is deterministic (cache-safe) | `test_digest_is_deterministic` | ✅ tested |
| 8 | Memory consolidates events → graph structure (co-occurrence, actors, tensions); replay boosts | `test_memory_consolidation_builds_structure` | ✅ tested |
| 9 | Attention is the product of five clamped factors; any zero vetoes | `tests/test_attention.py::test_any_zero_factor_vetoes` | ✅ tested |
| 10 | Vetoed bids never clear, even in an empty market | `test_vetoed_bids_never_clear_even_in_an_empty_market` (added after play-testing found the bug) | ✅ tested |
| 11 | Market clearing is deterministic (tie-breaks by src, label) | `test_market_clears_top_k_and_counts_starvation` | ✅ tested |
| 12 | Executive resolves resource conflicts (yield) and cause-chains decisions | `test_executive_resolves_resource_conflicts` | ✅ tested |
| 13 | Script fire updates EMA; crashes never propagate | `tests/test_scripts.py` | ✅ tested |
| 14 | Starving never-fired scripts die into a permanent necrology (DEATH event) | `test_starving_never_fired_script_dies_into_necrology` | ✅ tested |
| 15 | Dreams mutate parameters with unique lineage names | `test_mutate_jitters_params_and_lineage` (collision fix verified) | ✅ tested |
| 16 | Save/load round-trips state; adopt() restores track records | `tests/test_integration.py::test_save_load_round_trip` | ✅ tested |
| 17 | Killing the root stops all action; resurrection resumes it; nothing is lost | `test_killing_the_root_stops_but_preserves_everything` | ✅ tested |
| 18 | Idle organisms sleep; dreams spawn; pruning kills | `test_sleep_on_idle_with_dreams_and_pruning` | ✅ tested |
| 19 | An LLM citizen (mock) proposes → scripts spawn → they fire; cache session measures hits | `test_llm_citizen_with_mock_provider_and_cache_session` | ✅ tested |
| 20 | Identity commitments are hash-chained; tampering breaks verify(); introspect is stable within a session | `test_identity_chain_and_stable_introspect` | ✅ tested |
| 21 | Registration without a WHY node is a hard error | `test_registering_without_why_is_an_error` | ✅ tested |
| 22 | The ten-minute tour runs end-to-end, story intact | `python experiments/minimal_world.py` (run in CI via `make world`) | ✅ verified in build |
| 23 | All eight examples run keyless | `examples/*/main.py` (executed in CI on every push) | ✅ verified in build |
| 24 | No secrets in the tree | CI secret-scan step + `make guard` | ✅ wired (see note) |
| 25 | DeepInfra/Hy4 pricing + caching claims ($0.834 / $0.042 / $2.501 per 1M) | checked against deepinfra.com model page on 2026-10-31; dogfood journal shows real `cached_tokens` | ✅ verified live (re-check before big spend) |
| 26 | No horizon configured → v0.2 justification semantics bit-for-bit | `tests/test_reattestation.py::test_no_horizon_keeps_v02_semantics_forever` | ✅ tested |
| 27 | Freshness: grace window then linear decay; weakest link rules the chain | `test_freshness_grace_then_linear_decay`, `test_weakest_link_rules_the_chain` | ✅ tested |
| 28 | Running under a purpose re-attests its whole chain (transitive to root) | `test_runtime_stamps_chains_of_winners`, `test_stamp_chain_is_transitive_to_the_root` | ✅ tested |
| 29 | Unserved ALIVE nodes lapse to UNKNOWN at the audit; necrology records it; nothing deleted | `test_runtime_reaps_unserved_purposes_on_audit_ticks`, `test_unserved_purpose_lapses_to_unknown_never_deleted` | ✅ tested |
| 30 | A lapsed node cannot run and cannot self-attest; only revive(reason) restores it | `test_lapsed_node_blocked_until_revived` | ✅ tested |
| 31 | Conservation holds under random kill/revive/lapse storms (43 nodes, 300 ticks) | `test_conservation_survives_random_storm_with_reaping` | ✅ tested |
| 32 | Save/load round-trips horizon, last_beat, freshness, justification | `test_revived_purpose_resumes_and_persistence_roundtrips` | ✅ tested |
| 49 | 10,000-tick soak: conservation at every audit, full verify at every 1,000 ticks, archival engaged, lapses under an idler, disk round-trip re-verified | `python experiments/soak.py --ticks 10000` (receipts above; CI pins 1,500) | ✅ verified in build |
| 50 | Soak determinism: same seed -> identical receipts (digest + chain) | `tests/test_soak.py::test_soak_is_deterministic` | ✅ tested |
| 51 | Pinned soak invariants under pytest | `tests/test_soak.py::test_soak_every_invariant_holds` | ✅ tested |
| 43 | Archival eligibility is conservative (ancient DEAD, no live descendant, whole subtree) | `tests/test_archive.py::test_eligibility_is_conservative`, `::test_dead_with_live_descendant_is_not_eligible` | ✅ tested |
| 44 | Hot + archived == ever_declared after any sweep | `test_sweep_archives_whole_dead_subtree_and_books_balance` | ✅ tested |
| 45 | The manifest carries full biographies; the auditor verifies cold nodes against the replay | `test_nothing_is_lost_the_manifest_carries_biographies`, `test_auditor_verifies_cold_storage_against_the_replay` | ✅ tested |
| 46 | A tampered manifest fails the receipt | `test_tampered_manifest_is_caught` | ✅ tested |
| 47 | Restoration is the recorded two-act ceremony (restore still-DEAD w/ reason, then resurrect w/ parole) | `test_restoration_is_a_recorded_two_act_ceremony`, `::test_restore_requires_a_reason` | ✅ tested |
| 48 | Archival survives save/load and still verifies | `test_archival_survives_save_load_and_still_verifies` | ✅ tested |
| 38 | Brier scores are pinned math (perfect=0, coin=0.25, confidently-wrong=1); claims are validated | `tests/test_calibration.py::test_brier_score_math_is_pinned`, `::test_calibration_records_are_validated_and_filterable` | ✅ tested |
| 39 | The runtime scores every success_p claim against its realized outcome | `test_runtime_scores_success_p_claims_against_outcomes` | ✅ tested |
| 40 | The arbiter sees only live bids; vetoed bids never reach it; failing arbiters degrade to deterministic | `test_vetoed_bids_never_reach_the_arbiter`, `test_failing_arbiter_degrades_to_deterministic` | ✅ tested |
| 41 | Arbiter divergence from the deterministic shadow is counted telemetry | `test_arbiter_reorders_contenders_and_divergence_counts` | ✅ tested |
| 42 | Live: jev arbitrated 50 contended ticks, 0 errors, 50 divergences; overconfident scout measured MISCALIBRATED (Brier 0.395) | `library/rounds/005-decision-arbiter.md` (run 2026-10-31) | ✅ verified live |
| 34 | Genesis + necrology + journal replay to exactly the living tree (states, heartbeats, provenance, parole) | `tests/test_audit.py::test_replay_equivalence_on_a_rich_tree`, `::test_replay_equivalence_through_save_load`, `::test_replay_survives_a_random_storm` | ✅ tested |
| 35 | Every tamper vector is caught with the check named (flip, edit, remove, reorder, forge record, forge/drop stamp) | `test_tamper_*` (7 tests) | ✅ tested |
| 36 | The hash chain pins necrology + journal against any edit, including superseded stamps | `test_chain_head_pins_history_and_journal` | ✅ tested |
| 37 | Saved organisms carry their own conservation receipt | `Runtime.save()` embeds it; `make audit` prints it | ✅ verified in build |
| 33 | Revival without service buys exactly one horizon; revival with service holds | `python experiments/reattestation_economics.py` (CI-verified: 2 lapses, 2 revives, ever_declared=3) | ✅ verified in build |
| 52 | Treaties route attestation between organisms; provider death propagates hard with exchange receipts; the federation auditor catches forged service | `tests/test_society.py` (lockstep determinism pinned bit-for-bit) | ✅ tested |
| 53 | Multi-parent purposes: best-path verdicts, path-survivor cascades with a fixpoint; trees keep v0.2 semantics bit-for-bit | `tests/test_why_dag.py` | ✅ tested |
| 54 | Arbiter delegation is scored by realized outcomes; miscalibrated or value-destroying judgment is benched to the shadow with a receipt | `tests/test_outcome_arbiter.py` | ✅ tested |
| 55 | Journal compaction keeps replay equivalence exactly; every compaction is receipted and chain-covered | `tests/test_compaction.py` | ✅ tested |
| 56 | Fail-safe totality: bid() explosions, junk bids, and malformed arbiter answers are contained, recorded as ERROR events, and never fatal | `tests/test_failsafe.py` (round 17) | ✅ tested |
| 57 | Docs counts are machine-checked against the tree on every push; the quickstart's code block is executed as a test | `scripts/check_docs.py` in CI; `tests/test_docs_code.py` | ✅ wired |
| 58 | Saves are atomic; loads verify at the door (event chain head, watermark, recomputed conservation receipt); the events file is append-mode | `tests/test_persistence_trust.py` (round 20a) | ✅ tested |
| 59 | An adopted script keeps its saved biography — born=0 survives load; sleeper stats + idle_window persist | `::test_born_zero_survives_load`, `::test_sleeper_stats_and_idle_window_survive_save_load` | ✅ tested |

**Test count:** 268 as of round 20 — **187 from the kernel**
(`src/cognitive_ecology/`, the subject of this audit; 28 of them the
round-17/20 pins: fail-safe, docs-code, and persistence-trust) **+ 81
from the preserved v0.1 research line**
(`src/ecology/`, alternative WHY formalism + LLM teacher layer; see
README "Two development lines"). Both suites run green together;
`make test` ~4s. Counts are machine-checked on every push by
`scripts/check_docs.py` (`make truth`).

### Known limitations (honest list)

- **Single-process.** No async tick sources, no wall-clock integration;
  ticks are counted, not scheduled.
- **Weighted/majority WHY parents are unexplored.** Multi-parent DAG
  purposes shipped in v0.4 (ADR-0012, best-path semantics); weighted
  parents and majority semantics remain open (OPEN_QUESTIONS.md #1).
- **Script mutation is parameter-only.** Behavior-level novelty comes
  only from LLM proposals within the action library.
- **Memory consolidation is heuristic.** No abstraction/schema formation
  yet; co-occurrence and recency only.
- **Typesafe/decision-model client is EXPERIMENTAL.** Protocol is stable;
  the HTTP client's request shape must be checked against your
  provider's current schema (docs/08).
- **Archival exists (v0.3, ADR-0010)** with conservative eligibility
  and a recorded two-act restoration — but the policy is age-based
  only; smarter sweeps remain open.
- **The `runs/` telemetry directory** is gitignored output, not state
  management; long-lived organisms need a real storage story.

## External audit

*(Reserved for an independent reviewer. Suggested protocol: run
`pip install -e ".[dev]" && make test && make world`, then review
against docs/02_architecture.md claims and the table above. Findings,
with file/line references, below.)*

| Date | Reviewer | Scope | Findings |
|---|---|---|---|
| — | — | — | awaiting |
