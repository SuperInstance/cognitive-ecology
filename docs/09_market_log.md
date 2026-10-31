# The Market Log: Watching an Organism Think

*The observation boundary — exact, non-perturbing, deletable
(ADR-0015).*

Wave-1's researcher persona said it best: the five attention factors
are the platform's core scientific object, and they were invisible.
Every clearing is now serialized as it happens:

```python
import cognitive_ecology as ce
from experiments.minimal_world import build_world

rt = build_world(seed=7)
rt.run(100)

rt.market_log.bids()[0]
# {'kind': 'bid', 'tick': 1, 'src': 'critter', 'label': 'forage',
#  'urgency': ..., 'justification': ..., 'opportunity': ...,
#  'novelty': ..., 'expected_value': ..., 'attention': ...,
#  'resource': None, 'success_p': None, 'status': 'run', 'seq': 14}
```

## The three laws (why you can trust these numbers)

1. **Exact.** The floats written are the floats the market scored —
   no rounding, no re-derivation. `json` roundtrips them bit-for-bit,
   so your analysis sees what the organism saw.
2. **Not a second source of truth.** Rows serialize the market's own
   `ClearResult` and the executive's own decisions. Delete the log
   whenever you like; the organism loses nothing.
3. **Non-perturbing.** Reading it changes nothing — pinned by
   bit-identical twin runs in the test suite. Observation that cannot
   perturb cannot break you.

## Reading a clearing

Every bid of every tick gets one row. `status` is the market's
verdict:

| status | meaning |
|---|---|
| `run` | cleared and executed |
| `yield` | cleared but lost an exclusive `resource` to a stronger bid |
| `starved` | live (attention > 0) but below the top-k cut |
| `vetoed` | attention ≤ 0 — the veto law refused it |

When the delegated arbiter truly arbitrated (contention, a valid
answer), one extra row records its pick, confidence, and whether it
diverged from the deterministic shadow. A degraded or uncontended
arbiter writes nothing.

## The analyst's first three calls

```python
log = rt.market_log

log.summary()
# {'clears': 100, 'bids': 412, 'run': 196, 'yield': 0, 'starved': 195,
#  'vetoed': 21, 'clear_rate': ..., 'mean_winner_attention': ...,
#  'top_winners': [...], 'most_starved': [...], 'most_vetoed': [...],
#  'arbiter': {'calls': 0, 'divergent': 0, 'last_pick': None}}

log.veto_reasons()
# {'w:work': {'count': 3, 'zero_factors': ['justification']}}
# ^ the veto law with its evidence: WHICH factor was zero, in the
#   market's own numbers. Fix the factor; don't bypass the market.

rows = log.bids()          # pandas-friendly: pd.DataFrame(rows)
```

A truth worth knowing: the script ecology pre-gates its own scripts
upstream of the market (a dead-purpose script never bids at all), so
vetoed rows come from components that submit raw bids — LLM proposal
agents, custom components. The veto law protects the market no matter
who speaks.

## Durable copies and provenance: `run_rounds.py`

The in-memory log is a bounded tail (default: most recent 100k rows —
`MarketLog(keep=...)` to change, `keep=None` for unbounded). The
durable copy is the host's:

```bash
python scripts/run_rounds.py --ticks 300 --out runs/exp1
# -> telemetry.jsonl  per-tick life signs
# -> market.jsonl     the read model, exact floats
# -> manifest.json    seed, config, versions, git commit, output digests
# -> state.json, events.jsonl

python scripts/run_rounds.py --ticks 300 --sweep 5 --out runs/sweep1
# five seeds, one aggregate: mean ± spread per metric
```

The manifest is the answer to "which seed, which code, which config
produced these files?" — outputs carry sha256 digests, so a modified
file is a detectable file. Sweeps separate properties of the SCENARIO
(tight spread across seeds) from properties of the SEED (wide spread).
Its first use discovered that `minimal_world` is seed-invariant —
nothing in the demo consumes randomness — which is exactly the kind of
truth an instrument should surface about its own calibration.

## Persistence

The market log is observation, not organism state: it never rides in
`state.json`, and a loaded organism starts a fresh log
(`MarketLog.from_jsonl(text)` loads a durable copy back for analysis).
Observation history belongs to the observer.

## Test evidence

`tests/test_marketlog.py` (17 cases): bit-for-bit float roundtrips,
all four statuses, veto reasons naming the zero factor, arbiter rows
only when arbitration truly happened, bounded retention, jsonl
roundtrips, bit-identical non-perturbation twins, determinism of the
log itself, and the fresh-log-on-load contract.
