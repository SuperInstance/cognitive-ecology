# Example 07 — The Proof-Carrying Organism (audit + cold storage)

**What this teaches:** v0.3's two trust mechanics:

1. **The conservation auditor** (ADR-0008). Every WhyTree carries a
   replay basis — genesis block + necrology + attestation journal —
   and `ConservationAuditor.verify()` replays it from nothing and
   demands bit-for-bit equivalence with the living tree. You will print
   a valid receipt, then attack it twice: flip a state off the books
   (caught by `state_equivalence`), and rewrite one word of history
   (caught by the hash chain head).
2. **Honest archival** (ADR-0010). An ancient DEAD subtree moves to
   cold storage — the books stay balanced (hot + cold == ever declared),
   the manifest carries full biographies, and the auditor verifies the
   cold against the replay too. Restoration is a recorded two-act
   ceremony: restore-with-reason (still DEAD, in the necrology), then
   resurrect-with-parole.

**Run it:**

```bash
python examples/07_audit_and_archive/main.py
```

No API keys. No network. No dependencies beyond the kernel.

**The receipt object** (`ConservationReceipt`) carries per-check
results, live/replay digests, and the chain head — `Runtime.save()`
embeds one in every `state.json`, so a saved organism vouches for its
own history.

**Where to look next:** `make audit` (a live receipt on the ten-minute
organism), `experiments/soak.py` (10,000 ticks with verification every
thousand), ADR-0008 and ADR-0010.
