# Round 11 — the society-basis federation under attack

*Run: 2026-10-31T19:03:34Z — tencent/Hy4-preview red-teaming ADR-0011, gated by jev. Cost $0.008607; 5124 prompt tokens (2432 cached, 47% cache hit).*

## Iterations

### iteration 1

ATTACK: Non-sole stacking evades hard propagation. A gives node `a` two ACTIVE treaties: `b1` (B) and `b2` (C). `a` is never "sole_basis" on either, so when B’s provider node dies, HARD PROPAGATION only breaks `b1`; no `question()` fires. Meanwhile `b2` keeps `a` fresh via Exchange, so neglect never lapses it. A keeps a cheap dead-end treaty alive purely as a sole_basis shield. Auditor checks “no ACTIVE treaty with a dead endpoint” (b1 becomes broken, OK) and “each treaty stamp matches provider stamp” (b2 is real), so the lie passes.

REPAIR: In `Society.step()` / Exchange, compute effective basis per beneficiary node as the set of ACTIVE treaties whose provider chain actually stamped it this tick. If any provider endpoint is DEAD/UNKNOWN and the node’s *sole remaining effective* basis is empty, force `question(nid, "sole_basis_lost")` on A’s books. Module: `society_basis/hard_propagation.py` (or `Exchange` basis resolver). Track “effective sole” not “declared sole.”

### iteration 2

ITERATION 2 — REPAIR THE HOLE: “SHIELD TREATY” / NON-SOLE STACKING

The gate says the hole is real. Here is the concrete repair, written as a red-team hardening patch.

---

## 1. The precise bug

The exploit works because ADR-0011 v0.4 confuses two different notions:

- **Declared sole basis:** “at most one ACTIVE treaty per beneficiary node, so `served only by` cannot be said twice.”
- **Effective basis:** the set of ACTIVE treaties whose provider chain actually stamped the beneficiary node this tick.

The attacker creates two ACTIVE treaties for beneficiary `a`:

- `t1`: `a` ← `b1` (provider B)
- `t2`: `a` ← `b2` (provider C)

Neither treaty is “declared sole” in the naive sense, so when `b1` dies:

1. `t1` breaks.
2. No `question()` fires, because the rule only fires when the treaty was the node’s *declared* sole basis.
3. `t2` is still ACTIVE and still stamps `a`, so `a` stays fresh.
4. The auditor sees:
   - no ACTIVE treaty with a dead endpoint — `t1` is broken, fine;
   - every treaty-provenance stamp on `a` matches a provider stamp — `t2` is real;
   - each member’s own books balance — A’s books say `a` is ALIVE and being served.

So the federation auditor passes a lie: `a` is effectively served only by a dead-end shield treaty.

---

## 2. Repair principle

Replace “declared sole basis” with “effective sole

### iteration 3

ITERATION 3 — REPAIR: EFFECTIVE-BASIS HARD PROPAGATION

The gate is right: the “declared sole basis” rule is unsound. ADR-0011 v0.4 cannot let a beneficiary escape hard propagation by holding multiple ACTIVE treaties where only one is a real provider and the others are cheap shields. The repair is to make hard propagation depend on **effective basis**, not declared basis, and to make the Exchange the only place where effective basis is computed.

---

## 1. Core invariant to enforce

For every beneficiary node `a` on member A’s books, at every exchange tick:

> If `a` has at least one ACTIVE treaty whose provider endpoint is now DEAD/UNKNOWN, and after removing all such dead-end treaties and all treaties that did **not** stamp `a` this tick, the remaining effective basis is empty, then A must call `question(a, "sole_basis_lost")` on A’s own books.

This removes the shield-treaty hole: a shield treaty only protects `a` if it actually delivers a provider stamp in the same tick. A dead-end treaty that is broken, or an ACTIVE treaty whose provider chain did not stamp `a` this tick, contributes nothing to effective basis.

---

## 2. Where the fix lives

Put the resolver in:

`society_basis/hard_propagation.py`

Exposed through `Exchange.resolve_effective_basis()` and consumed by `Society.step()` after the exchange stamp phase.

The Exchange already consumes frozen log slices and performs one-hop delegation. It is the correct place to compute effective basis because it is the only component that sees:

- the frozen provider-side stamp for each treaty this tick;
- the ACTIVE/BROKEN/REVOKED state of each

### iteration 4

ATTACK — ITERATION 4: “FRESHNESS-LAUNDERING VIA CROSS-MEMBER SHADOW STAMPS”

The gate is right that the effective-basis repair is necessary, but it is not sufficient. The new invariant still says, in effect:

> If `a` has at least one ACTIVE treaty whose provider endpoint is DEAD/UNKNOWN, and after removing dead-end treaties and treaties that did NOT stamp `a` this tick, the remaining effective basis is empty, then `question(a, "sole_basis_lost")`.

That rule is still too weak, because it only inspects treaties **on `a`’s own books** and only asks whether `a` was stamped **this tick**. It does not ask whether the stamp that saved `a` is *the same service* the treaty claims to route, nor whether that stamp is cryptographically/economically attributable to the provider endpoint named in the still-ACTIVE treaty. ADR-0011 says the Exchange “consumes only frozen log slices” and that a treaty-provenance stamp on a beneficiary’s journal must match a provider stamp on the provider node at the same tick. The federation auditor checks:

- no ACTIVE treaty with a dead endpoint;
- every treaty-provenance stamp on a beneficiary’s journal matches a provider stamp on the provider node at the same tick;
- provider-side sole breaks have their question() receipt;
- each member’s own books balance;
- hash chain over the ledger.

None of those checks bind the *content* of the provider stamp to the *purpose* of the beneficiary node `a`, nor to the specific provider component under the named provider endpoint `b`, nor to the treaty id. So the hole is: **A can keep a dead-end “real” treaty alive by having

## Decision gates (jev)

- after iteration 1: steer=('repair', 0.35, {'attack': 0.39, 'repair': 0.57, 'concede': 0.04}) severity=(2.56, 0.56)
- after iteration 2: steer=('repair', 0.64, {'attack': 0.23, 'repair': 0.76, 'concede': 0.01}) severity=(2.73, 0.72)
- after iteration 3: steer=('attack', 0.35, {'attack': 0.57, 'repair': 0.39, 'concede': 0.04}) severity=(2.03, 0.45)

---
*Recorded cost: $0.008607. Build actions taken in response: see JOURNAL round 11.*