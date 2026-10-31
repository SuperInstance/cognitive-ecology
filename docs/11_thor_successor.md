# The Thor successor

*2026-11-01. If you're reading this repo for the first time: start here
for the family tree.*

**The laws live on in a purpose-built successor:**
[`SI-Thor/ecology-thor`](https://github.com/SI-Thor/ecology-thor)
(private; ask Casey) — the same WHY conservation law, re-attestation
economics and attention economy, rebuilt as a native Rust + CUDA/PTX
service for the **NVIDIA Jetson AGX Thor** box that runs the SI-Thor
world-creation stack (infinigen-thor, thor-world, builder-ide).

## Why a second repo instead of a v1.0 here

This repo is the *theory lineage*: pure Python, laptop-scale, zero
hardware assumptions, and the place where the laws were proven
(`why.py` v0.3 semantics are the reference the successor ports
bit-for-bit). The Thor box changed the engineering, not the philosophy:

| Concern | Here (cognitive-ecology) | ecology-thor |
|---|---|---|
| Kernel language | Python (std-only philosophy) | Rust, std-only, zero deps, one `unsafe` |
| Scale | dozens–hundreds of purposes | 100k+ purposes, preallocated arenas, zero steady-state allocation |
| Sweeps | Python loops | bit-exact CUDA kernels for Blackwell sm_110, unified-memory zero-copy |
| Time | best-effort | 100 Hz framed tick, rate-limited cascades, safe-mode degradation |
| Budgets | abstract attention | rails of GPU-seconds / joules / cents (builder-ide's units) |
| Determinism | seeded RNG | journal chain hash, golden tests, x86_64 == aarch64 bit-exactness policy |

## Where each piece went

- `why.py` four-state law + re-attestation economics →
  `ecology-core/src/why.rs` (+ `freshness.rs`), semantics ported exactly
  (weakest-link freshness, grace h/3, probation cap 0.5, lapse, revive).
- Attention economy (urgency · justification · opportunity · novelty ·
  expected_value, veto law) → `ecology-core/src/attention.rs` +
  `kernels/ecology.cu` (three implementations, bit-exact by contract).
- The L0–L8 layering → flattened into the module map
  (`docs/ARCHITECTURE.md` there); the mapping table is in its §7.

## What stays here

The research line: the manifesto, the decision-model work, the market
log, the playbooks, and the Python reference implementation teams can
read in an afternoon. The SI-Thor repos vendored the WHY kernel from
this lineage (builder-ide's `core/why` is a port of it); ecology-thor
is the native engine those teams deferred — their fit study
(`docs/research/cogeco.md` in builder-ide) and its follow-up
(`docs/research/ecology-thor.md`, on builder-ide's
`research/ecology-bridge` branch) tell the whole story.
