# Open Questions

The honest frontier. Each item is a live research question for this
kernel, ordered roughly by how soon it blocks somebody.

1. **Multi-parent WHY (DAG).** When two purposes jointly justify a
   behavior, verdict semantics need a policy: any-alive-parent?
   majority? weighted by justification? The tree was chosen for audit
   clarity; the first real shared-purpose organism will force this.

2. **Attention factor estimation.** Novelty is currently "fraction of
   watched nodes seen recently" and expected_value is a track record.
   Both could be far smarter (information gain, learned EV) — but every
   smarter estimator must stay cheap enough for per-tick use and
   deterministic enough for reproducibility.

3. **Decision-model integration boundary.** **Advanced (v0.3,
   ADR-0009):** they enter at exactly one bounded hook — the executive's
   tie-break among live contenders (veto-guarded, fail-safe, divergence
   counted) — plus the calibration log that scores probabilistic claims.
   Open remainder: score the arbiter by realized OUTCOMES, not just
   divergence (the v0.4 OUTCOME-ARBITER direction).

4. **Sleep scheduling.** Idleness-triggered sleep works for the demo
   worlds. Real organisms may want scheduled consolidation (nightly),
   budget-triggered sleep (event log growth), or both. What are the
   right triggers, and what consolidates best during replay?

5. **Multi-organism societies.** **Advanced (v0.4, ADR-0011):** the
   first society mechanic is the TREATY — a foreign purpose reference
   (A's node served by B's node) that routes attestation across
   organisms. Service keeps A's books fresh through A's own
   re-attestation economics; a provider's death propagates HARD
   (question, exchange receipt, treaty broken) while neglect propagates
   SOFT (A's own reaper). The federation auditor makes forged service
   and missed propagations detectable. Open remainder: cross-organism
   attention markets (treaties move attestation, not bids), full
   society replay equivalence (recomputing the exchange from both
   bases), and the original question in its sharpest form — whose WHY
   wins when organisms *disagree*, not merely when one dies.

6. ~~**Honest archival.**~~ **CLOSED (v0.3, ADR-0010):** cold storage
   with conservative eligibility, balanced books, manifest biographies
   verified by the auditor, and a recorded two-act restoration ceremony.

7. **Real-time tick sources.** Everything is counted ticks. Connecting
   a heartbeat to wall-clock, message queues, or market data — without
   losing determinism in tests — is an open engineering question.

8. **Script speciation.** Populations that grow large need niches:
   should the ecology cluster similar scripts, share resources by
   family, or speciate focus sets to reduce market congestion?

9. **Attention for humans.** The telemetry is JSONL; the dials
   (docs/07) are textual. What is the minimal *visual* attention
   dashboard that would make market dynamics legible without becoming
   a product?

10. **The benchmark question.** Play-tests discover; they do not
    compare. When two organisms must be compared (with/without a
    decision model; with/without sleep), what is a fair benchmark for
    *persistence* — and how do we keep it from becoming Goodhart's
    playground?

11. **LLM proposer economics.** Dogfooding found proposer starvation
    (successful children outcompete their proposer) and fixed it with a
    staleness drive. What other homeostatic terms do proposal organs
    need? Is there a principled account of "ideation appetite"?

12. **Formal statement of conservation.** The necrology gives an
    append-only transition log. Is there a clean formal statement
    (à la event sourcing / ledger invariants) that a theorem prover
    could check, and would it catch anything the randomized storm test
    does not?

13. **Journal compaction.** The attestation journal grows one entry per
    stamped node per winning act (60k entries at 10k ticks). Verify is
    O(journal). When does compaction (per-epoch digest rolling) become
    necessary, and what does it cost the replay basis?

## Closed questions (with their answers)

- **Should zero-attention bids clear in an empty market?** No — found
  by play-testing example 01 (a sated drink script drank forever); fixed
  as the veto law and pinned by test. (2026-10-31)
- **Should search scripts succeed when re-charting a charted topic?**
  No — one-shot semantics; eternal "success" was clogging the market
  with no-ops. (2026-10-31)
- **Can dream names collide?** They could; generation-counted unique
  names now guarantee they cannot. (2026-10-31)
