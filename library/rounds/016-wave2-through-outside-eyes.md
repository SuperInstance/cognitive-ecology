# Round 24 — ideation 016: rounds 21-23 through outside eyes

*Run: 2026-10-31T21:59:08Z — tencent/Hy4-preview x2 (cache-first, $0.006818, 1536 cached tokens) + typesafe jev (wave2-arbiter).*

## I. Red-team of rounds 21-23

**1. Market log lies by omission (round 21).** `keep=100k` is a ring buffer and the log is *not* in `state.json`. Run 250k ticks, or Ctrl-C + reload, and rows are gone silently — while the WHY chain and event hash chain continue. The arbiter scoring outcomes, or a seed sweep comparing runs, sees a log starting at tick 150k with no marker. *User:* the researcher who trusts `veto_reasons()` history to bench a delegate. *Test:* run `keep+1` ticks, compact, reload; assert the log carries `dropped_rows` / `resumed_at_tick` and that `log.last_tick == bus.last_tick`; fail if rows vanish without a recorded gap.

**2. Driver breaks WHEN/WHAT at the interrupt seam (round 22).** `rt.run(n)` is atomic per tick; the driver is not. Graceful Ctrl-C / checkpoint cadence can land mid-tick — after ingest, before narration, or after a WHY mutation, before the market row. Driven life is then *not* bit-identical to `rt.run(n)`, violating the pinned contract. *User:* FastAPI lifespan / cron operator who restarts and gets a half-applied tick. *Test:* inject a clock that raises `Interrupt` at every intra-tick boundary; assert post-reload state equals `rt.run(k)` exactly and no tick is partially persisted (checkpoint only at tick boundaries).

**3. Safe seam leaks identity via `when_hint` (round 23).** `spawn_unique` hashes owner+action+args+`when_hint`. Two genuinely distinct behaviors differing only in `when_hint` collide; conversely a duplicate with a mutated hint is accepted *and* silently creates a second WHY — duplicate by behavior, not by id. `accept_rate` counts spawns, so a hint-tweaking agent never starves. *User:* the agent that re-proposes with jittered hints. *Test:* assert two spawns with identical owner/action/args and different `when_hint` yield one WHY + one DEMOTION, and `accept_rate` denominator counts *proposals*, not spawns.

## II. The wave-2 cast

**Noor — market log, manifests, sweeps**
- Probe: Run a seeded `run_rounds.py` sweep; open one tick’s log row and the run manifest.
- Landed: Floats are EXACT, JSON round-trips bit-for-bit; row shows run/yield/starved/VETOED with `veto_reasons()`; manifest has seed/config/versions/git/sha256; sweep prints mean ± spread.
- Regressed: Any rounding, missing veto reason, absent manifest, or sweep without spread.

**Mateo — drivers + ingest law**
- Probe: Drive life with `WallClockDriver` + injected clock; Ctrl-C mid-run; push a fact through example-04.
- Landed: Driven life is bit-identical to `rt.run(n)`; checkpoint cadence + `DriverReport`; facts persist to graph at ingest, bus only narrates; Ctrl-C exits gracefully.
- Regressed: Driver changes WHAT, facts lost on ingest, crash on Ctrl-C, or bus mutates state.

**Ines — ensure_* rite + duplicate demotions**
- Probe: `ensure_why` same id twice, then same id with a different statement; call `spawn_unique` with a duplicate behavior signature.
- Landed: Re-ensure with same stmt is idempotent; different stmt raises; duplicate is a DEMOTION (counted, tailed, ERROR event), `accept_rate` counts spawns only, re-proposals starve.
- Regressed: Silent overwrite, no raise on statement change, duplicate accepted, or starve metric missing.

**Yuki — persistence trust**
- Probe: Save, kill, reload; tamper with an event; run snapshot+delta compaction.
- Landed: Atomic save; append-only events; hash chain verifies at load; tamper caught; books balanced after compaction.
- Regressed: Partial write, chain mismatch, hash not checked, or unbalanced books.

**Levi — fail-safes**
- Probe: Inject a `bid()` failure and an arbiter failure mid-tick.
- Landed: Degrades, never crashes; ERROR events carry reasons; tick completes.
- Regressed: Unhandled exception, silent no-op, or missing reason.

**Zara — docs/truth gate**
- Probe: Push a README count change that contradicts the tree.
- Landed: Gate fails; counts match tree exactly.
- Regressed: Push passes, or stale count ships.

## III. The arbiter's call (typesafe)

- first_probe: **E_docs_truth** (confidence 0.14)
- probe-set coverage: **0.95** (confidence 0.59)
- probes under consideration: A_read_model, B_driver_contract, C_safe_seam, D_persistence, E_docs_truth, F_ingest_law

---
*Triage: see JOURNAL round 24.*
