# Round 4 — the re-attestation economics under attack

*Run: 2026-10-31T09:33:25Z — tencent/Hy4-preview red-teaming ADR-0007, gated by jev. Cost $0.009087; 4033 prompt tokens (1536 cached, 38% cache hit).*

## Iterations

### iteration 1

**Iteration 1**

**ATTACK — “Heartbeat Laundering” via Ancestral Piggybacking.**  
A component `C` that wins a bid stamps heartbeats along its entire WHY chain. A parasitic child `P` can attach itself as a descendant of a high-traffic ancestor `A` (e.g., a root purpose that is constantly served by unrelated components). `P` never acts on its own purpose; it merely bids with urgency≈0 but nonzero opportunity/novelty, or rides a co-tenant’s winning bid by sharing `A`. Every win by any sibling refreshes `P`’s chain through `A`, so `P` stays ALIVE with zero genuine service. Cheaper still: `P` and `Q` mutually back-scratch by alternating trivial “actions” that each stamp the other’s shared ancestor; both stay fresh while producing no external value. The audit only checks per-node attestation recency, not *who* attested or *how much* service occurred, so the economy rewards lineage position over contribution.

**REPAIR — Attestation Provenance & Weight.**  
In `Necrology` (append-only ledger) and `Justification` (bid scoring): record not just tick stamped, but `(component, action_id, value_delta, ancestor_path)`. Justification must weight each ancestor’s freshness by the *fraction of total subtree value* attributable to that ancestor’s descendants, not mere recency. Add a `ServiceLedger` that decays a node’s justified weight if its refreshes come from low-`value_delta` actions or from non-descendant riders. This kills free riding while preserving genuine transitive maintenance.

### iteration 2

**Iteration 2**

**ATTACK — “Liveness Laundering via Cascade Recycling / UNKNOWN-Washing.”**

The repair in Iteration 1 stopped *riders* from inheriting ancestor freshness for free by weighting justification with `value_delta` and provenance. But it still treats **UNKNOWN as a safe, cheap, revivable parking state**. That is the bigger hole: the audit’s per-node lapse rule plus revive’s “buy one horizon” semantics turn the WHY tree into a **rotisserie of near-dead purposes**.

The exploit does not need a high-traffic ancestor or a fake sibling. It needs only **one sacrificial downstream component** and the fact that:

- killing cascades living descendants to UNKNOWN, not DEAD;
- UNKNOWN is questionable/revivable;
- lapse is per-node and does **not** cascade;
- `revive(reason)` is explicit and buys a fresh horizon;
- the audit runs only every 25 ticks.

**Attack sequence:**

1. Build a purpose chain `Root -> P -> Q -> D`, where `D` is a leaf component that can be cheaply “used” once.
2. Let `P` and `Q` go UNATTENDED until they are about to lapse. They are ALIVE but stale.
3. At the audit boundary, do **not** refresh `P` or `Q` by service. Instead, let `D` trigger a kill/abort action that **cascades `Q` and `P` to UNKNOWN**.  
   - This is recorded, never deleted, so it looks like legitimate state transition.
   - Crucially, the cascade does **not** require `P` or `Q` to have been recently attested. It only requires a living descendant to be killed.
4

### iteration 3

**Iteration 3**

**ATTACK — “Audit-Boundary Zombie Rotisserie / Lapse-Chain Recycling.”**

The Iteration-2 attack showed that a sacrificial kill can cascade stale ancestors to UNKNOWN, where they can be revived. The obvious repair is to make `revive()` require *recent descendant service* or to forbid reviving a node whose lapse was manufactured by a self-inflicted cascade. **That repair is still not enough**, because it patches the *revive()* path while leaving the **audit scheduler and the multiplicative bid veto** untouched. The bigger hole is that **UNKNOWN is not just a parking state — it is a *bid-veto* state**, and the audit’s coarse 25-tick granularity plus the all-or-nothing `justification()` product lets an attacker use UNKNOWN as a **scheduling primitive** to keep a purpose permanently “half-alive” while still controlling when it is allowed to contend.

The new exploit does not require a sacrificial descendant at all, nor a high-traffic ancestor, nor a fake rider. It exploits **three facts together**:

1. `attention = urgency * justification * opportunity * novelty * expected_value`; **any zero factor vetoes the bid**.
2. `justification()` multiplies the **alive-fraction** of the chain by **weakest-link freshness**; a node in UNKNOWN contributes an alive-fraction of **0**, so `justification` collapses to **0** for the entire chain — *even if every other ancestor is freshly attested.*
3. Lapse is **per-node**, non-cascading, and only evaluated at the **periodic audit every 25 ticks**. Between audits, a node’s recorded state is whatever the ledger says; there is no continuous-time check.

Therefore UNKNOWN is a **perfect zeroing gate**: the

### iteration 4

**Iteration 4**

**ATTACK — “Audit-Phase Zombie Reservoir / Veto-Gate Scheduling.”**

Iterations 1–3 patched free riding, cascade-recycling, and naive `revive()` abuse. The remaining hole is worse because it does not need riders, sacrificial descendants, or even a successful revive. It weaponizes the **audit’s discrete 25-tick sampling** and the fact that **UNKNOWN is a multiplicative zero inside `justification()`**, while `revive()` and `attention` are evaluated on different clocks.

The kernel believes UNKNOWN is “questionable/revivable,” so it is not death. But in the bid function, UNKNOWN is operationally identical to DEAD: it contributes alive-fraction `0`, so `justification = 0`, so `attention = 0`, so the whole chain is vetoed. That makes UNKNOWN a **perfect scheduling gate**: an attacker can keep a purpose in a reservoir of non-contending UNKNOWN, then release it into ALIVE exactly when the audit and bid windows favor it, while never letting the audit see a continuous honest decay.

The exploit uses four facts together:

1. Lapse is evaluated **only at the periodic audit every 25 ticks**, not continuously.
2. `revive(reason)` is explicit and buys a **fresh horizon**, independent of when the audit last ran.
3. `justification()` depends on weakest-link freshness; a single UNKNOWN ancestor zeroes the chain.
4. `attention` is multiplicative: any zero vetoes the bid, regardless of urgency/value.

**Attack sequence:**

1. Build a chain `Root -> A -> B -> C`.
2. Allow `B` to become stale but do **not** let it cross an audit boundary as ALIVE. Just before the audit,

## Decision gates (jev)

- after iteration 1: steer=('attack', 0.53, {'attack': 0.69, 'repair': 0.26, 'concede': 0.05}) severity=(2.12, 0.11)
- after iteration 2: steer=('attack', 0.44, {'attack': 0.63, 'repair': 0.37, 'concede': 0.0}) severity=(2.93, 0.93)
- after iteration 3: steer=('attack', 0.7, {'attack': 0.8, 'repair': 0.2, 'concede': 0.0}) severity=(2.93, 0.94)

---
*Recorded cost: $0.009087.*

## Build actions taken (same day)

- **Attestation provenance** (hole 1): `WhyNode.last_attested_by` records
  which component's winning act last stamped each node; persisted, tested.
- **Parole on revival** (hole 2): `revive()`, `resurrect()` and cascade
  revivals set `probation`; chains with any paroled node cap at
  justification 0.5 until a genuine win re-attests them. The experiment's
  idle revival now lands at 0.500 (was 1.000) — revival without service is
  visibly half-strength. Tested: `test_revive_is_parole_not_pardon`,
  `test_unknown_washing_never_beats_honest_service`.
- **Rebuttals recorded** (holes 3, 4): UNKNOWN discounts proportionally
  (it is not a bid veto), and freshness decays continuously per tick (the
  audit only formalizes lapse). See ADR-0007 amendments. The
  sibling-piggybacking variant that DOES hold is prevented by leaf→root
  stamp direction — pinned by `test_piggybacking_sibling_does_not_get_stamped`.

*Verifier note: iterations 2 and 4 were truncated by the 700-token cap —
the attack sequences stop mid-step. The build actions above address the
complete forms of the holes as best they can be reconstructed; severity
gates (jev: 2.93 "serious, not design-breaking") are the model's own
calibration.*