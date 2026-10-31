# Example 06 — The Attestation Economy (use it or lose it)

**What this teaches:** v0.3's re-attestation economics (ADR-0007). In
v0.2, liveness was a purchase — attest a purpose once and it stayed
maximally justified forever. Here liveness is a **subscription**:

- **running under a purpose re-attests its whole lineage** (serving a
  child keeps its root fresh),
- **stale chains bid progressively weaker** (weakest-link freshness
  discount — unserved purposes lose market contention before anything
  formal happens to them),
- **an unattended purpose lapses** to UNKNOWN ("questionable, never
  deleted") at the conservation audit,
- **revival is parole, not pardon** — a revived purpose bids at half
  strength until a genuine winning act re-attests it.

You will watch a served purpose hold justification 1.000 for 480 ticks
while its unserved sibling strangles economically (1.0 → 0.5 → 0.0),
lapses, is revived *without* service (and immediately drops to the 0.5
parole cap before lapsing again), and finally is revived *with* service
— and holds.

**Run it:**

```bash
python examples/06_attestation_economy/main.py
```

No API keys. No network. No dependencies beyond the kernel.

**The two lessons printed at the end:**

1. Revival without service buys exactly one more horizon — the archive
   lapsed twice.
2. Revival WITH service holds — the archivist kept it fresh to the end.

**Where to look next:** `experiments/reattestation_economics.py` (the
fuller version with receipts), `docs/04_why_conservation.md` (the
economics section), ADR-0007 (design + the live red-team round that
hardened it).
