# ADR-0015 — The observation boundary is a read model

- status: accepted (v0.4 round 21)
- date: 2026-11-01
- closes: wave-1 finding 3 (Ana: "the organism is invisible"); ideation 015 verdict

## Context

The wave-1 play-tests judged the kernel PILOT-grade with one design gap
named repeatedly: the five attention factors — the platform's core
scientific object — were never logged. Telemetry had no provenance (no
seed or config echo, orphaned output files), there was no experiment
harness above single runs, and every later observability need had
arrived as a bolt-on. The ideation-015 round diagnosed the root cause:
the kernel lacked a first-class OBSERVATION BOUNDARY, which is why
observation kept accreting onto organs that were never designed for it.

## Decision

### 1. Observation is a read model, not a feature

The market log (`marketlog.py`) is a serialization of the market's own
clearings — never a participant. It has no effect on any bid, any
decision, any event, or any state; it can be deleted at any moment and
the organism loses nothing but its observer's history. The wave-1
promise "degrades, never crashes" extends: observation that cannot
perturb cannot break anything either.

### 2. Three laws of the discipline (the 015 verdict, adopted in full)

1. **EXACT.** Serialize the exact floats of the very bids the market
   cleared — no re-computation from world state, no rounding at write
   time. `1/3` is written as the float it was; json roundtrips
   bit-for-bit (pinned).
2. **NOT A SECOND SOURCE OF TRUTH.** Rows are derived from the
   `ClearResult` and the `Decision` objects the executive already
   produced. The market log can answer questions about the market
   because it IS the market's output, serialized.
3. **NON-PERTURBING.** Attaching or reading the log changes nothing —
   pinned by a bit-identical twin run (identical event streams, log
   read every tick vs never touched) and by the whole pre-existing
   suite passing unchanged with the log wired in.

### 3. What a row is

One row per bid per tick: the five factors, the attention product, the
resource and claimed success probability, and the market's verdict —
`run` / `yield` / `starved` / `vetoed`, with vetoed separated from
starved (the pre-existing event stream mixes them). One extra row when
the delegated arbiter truly arbitrated (pick, confidence, divergence);
a degraded or uncontended arbiter writes nothing. `veto_reasons()`
reads only the stored floats to name WHICH factor was zero — the
"fix the factor; don't bypass the market" guidance, with evidence.

### 4. Memory is bounded; durability is the host's

The in-memory log keeps the most recent `keep` rows (default 100k) —
it is an observation tail for live processes, not a ledger. The
durable copy is the host's `market.jsonl` (see `run_rounds.py`), and
it never rides in `state.json`: a loaded organism starts a fresh log.
Observation history belongs to the observer, not the organism.

### 5. Provenance is a first-class output

Every `run_rounds.py` run writes a `manifest.json`: kernel version,
python, platform, git commit, seed, config, wall time, and a size +
sha256 digest of every output file. A run directory can never be an
orphan again. `--sweep N` runs the scenario across N seeds and
aggregates mean and spread — distinguishing properties of the SCENARIO
(tight spread) from properties of the SEED (wide spread). Its first
use found that `experiments/minimal_world.py` is seed-invariant
(nothing consumes randomness) — the instrument paid for itself on
day one by measuring its own demo.

## Consequences

- `Runtime.market_log` exists on every organism (wired in both the
  constructor and `load()`); the cost is one dict per bid, paid only
  by runs that submit bids.
- `EventKind.DECISION` keeps its rounded 4-decimal payload (the
  MIDI-size budget); the exact floats live in the read model, where
  size discipline is the host's choice. Two channels, two contracts.
- The arbiter's divergences are now observable per tick, not just
  counted — the scorecard judges outcomes (ADR-0013); the read model
  shows the judgment as it happened.
- Follow-ons shaped by 015 and deferred deliberately: exporting to
  hosts as a push-stream (sink callback) rather than a pull-tail;
  factor-level histograms over time; the physiology round (OQ #15)
  will consume `summary()` as its health surface.
