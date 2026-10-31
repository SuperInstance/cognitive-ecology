# Round 9 — ideation: the v0.4 frontier

*Run: 2026-10-31T09:53:29Z — tencent/Hy4-preview, cache-first, $0.002710. Stable prefix describes the complete v0.3 kernel.*

## Proposal

V0.4 frontier, ranked:

1. **SOCIETY-BASIS: cross-organism WHY federation**
   Build `society_basis`: signed `FOREIGN_PURPOSE_REF` receipts, a shared `NecrologyExchange`, and a `FederationAuditor` that replays each organism’s basis plus foreign attestations into one cross-organism liveness graph. A purpose may be served by another organism; justification becomes weakest-link across *organisms*, not just local chain. Closes: **multi-organism societies**. Pinning test: two organisms, A’s purpose P is only served by B; kill B; A’s P must lapse to UNKNOWN and cascade, with an exchange receipt in A’s necrology. Falsifier: if A can keep P LIVE after B dies, or if a forged foreign receipt passes the FederationAuditor, federation is fake.

2. **WHY-DAG: multi-parent purpose substrate**
   Build `why_dag`: replace tree-only parent edges with a DAG node type `PurposeNode(parents: set)`, update `ConservationAuditor` replay to topological ordering, and make cascade/kill propagate over union of ancestors. Closes: **multi-parent WHY (DAG)**. Pinning test: purpose C with parents A and B; kill A only; C must survive if B remains served, and die only when all parents lapse. Falsifier: a DAG replay that yields a different living set than the serialized hash-chain basis, or a kill that under/over-cascades.

3. **OUTCOME-ARBITER: outcome-weighted arbiter scoring**
   Build `outcome_arbiter`: replace/augment Brier-only scoring with realized-outcome weights per arbiter/bid, feeding `AttentionMarket` factor estimators and

---
*Triage: see JOURNAL round 9.*
