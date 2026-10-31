# cognitive-ecology

**A zero-dependency Python kernel for agents that persist like organisms.**
A body with a heartbeat. A purpose that cannot be deleted. An economy of
attention. A world the agent inhabits and remembers. Models as citizens,
not kings.

```
Python >= 3.10  ·  zero runtime dependencies  ·  zero LLM required to run
179 tests       ·  deterministic (seeded)     ·  MIT license
```

---

## The problem

Every session, a conventional agent is born, answers, and dies. Three
specific failure modes follow from that:

1. **Stateless oracles.** The "agent" is a function: prompt in, text
   out. Between calls it does not exist. Everything it "learned" lives
   in a context window that evaporates.
2. **RAG amnesia.** Retrieval is not memory. Chunk-embed-fetch gives you
   documents *similar to the question*, not a world with history — and
   the agent retains nothing from having retrieved them.
3. **Prompt mortality.** The agent's purpose lives in a prompt someone
   edits, a ticket someone closes. Purpose that can be deleted will be
   deleted, and the agent dies with it — usually without anyone
   noticing.

## What this is instead

A small kernel (one package, stdlib only) that treats an agent as an
**organism**:

- a **body** (L0 runtime) that ticks like a heartbeat and never calls a
  model itself;
- a **nervous system** (L1 events): MIDI-sized, immutable, append-only,
  causally chained — every effect walkable back to its decision;
- a **world** (L2 graph) the agent inhabits, where every node has a
  biography and recall is *traversal*, not similarity search (anti-RAG);
- **memory** (L3) that consolidates events into that world every tick;
- behavior as an **ecology** (L4): an agent is a population of small
  scripts that compete, starve, die — into a permanent necrology — and
  mutate in dreams;
- an **economy** (L5): attention = `urgency × justification ×
  opportunity × novelty × expected_value`, multiplicative, where any
  zero factor vetoes;
- a **conserved purpose** (L6 WHY): four states — alive, dead, unknown,
  absent — never deleted, always auditable, revivable; liveness is a
  *subscription* (serve it or lapse), and the conservation law is
  *proof-carrying* (the replay basis reconstructs the living tree, and
  every tamper vector is caught);
- an **identity** (L7): a slowly-drifting self-model with a hash-chained
  commitment ledger;
- **sleep** (L8): replay, prune, dream — offline consolidation on
  idleness.

LLMs and decision models join as **citizens**: they may propose
parameterized behaviors from an audited action library; the WHY tree
decides what may exist, and the attention market decides what runs.

## The stack

```
            ┌────────────────────────────────────────────┐
   L8       │  Sleep & Dreams — replay, prune, mutate     │   sleep.py
            ├────────────────────────────────────────────┤
   L7       │  Identity — the slowly-drifting self        │   identity.py
            ├────────────────────────────────────────────┤
   L6       │  WHY — purpose, conserved forever    ★      │   why.py
            ├────────────────────────────────────────────┤
   L5       │  Attention Market + Executive               │   attention.py
            ├────────────────────────────────────────────┤   executive.py
   L4       │  Script Ecology — agents are populations    │   scripts.py
            ├────────────────────────────────────────────┤
   L3       │  Memory — events consolidate into world     │   memory.py
            ├────────────────────────────────────────────┤
   L2       │  World Graph — anti-RAG knowledge           │   graph.py
            ├────────────────────────────────────────────┤
   L1       │  Events — MIDI-style, ~100 bytes            │   events.py
            ├────────────────────────────────────────────┤
   L0       │  Runtime — process, not agent (zero-LLM)    │   runtime.py
            └────────────────────────────────────────────┘
```

Not a call stack: the runtime rotates through all layers on every tick;
no layer calls a model.

## Four ideas in four code blocks

**1. Purpose is conserved (L6).** Killing a root cascades descendants to
*questionable*, never deletion:

```python
rt.declare_why("the field is worth inhabiting", node_id="why:root")
rt.declare_why("the critter stays alive", parent="why:root")

rt.why.kill("why:root", reason="mandate withdrawn")
rt.why.conservation()
# {'alive': 0, 'dead': 1, 'unknown': 2, 'ever_declared': 3, 'invariant_ok': True}
# nothing runs until... :
rt.why.resurrect("why:root", reason="a new mandate arrived with evidence")
```

**2. Attention is a market with vetoes (L5).** Any zero factor kills the
bid — no urgency can buy past a dead purpose (worked example with real
numbers: [docs/05](docs/05_attention_economics.md)):

```python
AttentionBid(src="critter", label="forage",
             urgency=0.8, justification=0.0,   # WHY chain broken
             opportunity=1.0, novelty=1.0, expected_value=1.0)
bid.attention   # 0.0 — vetoed, and the market will not clear it, ever
```

**3. Recall is traversal, not search (L2).** No embeddings anywhere:

```python
walked = rt.graph.walk(["concept:tired", "concept:thursday"], budget=10)
# -> the sleep/deadline/coffee neighborhood: the STORY, not the string
```

**4. Agents are populations (L4).** A script is a trigger + action +
track record; death is a record, not an erasure:

```python
rt.ecology.spawn(Script(name="forage", why_node="why:critter",
                        relieves=("energy",), when=..., act=...))
rt.ecology.necrology()   # every script that ever died, with its stats
```

**The life of a script:** it is spawned (BIRTH event) → bids every tick
(five live factors) → wins and fires (EMA-updated track record) or
starves (counted) → fails honestly when its moment passes → starves
past the limit → dies into the necrology with its full record → may
still be re-adopted from a save. A full worked example with numbers
sits in [docs/05](docs/05_attention_economics.md); a population living
and dying is [Tutorial 02](docs/tutorials/tutorial_02_script_ecology.md).

## 60-second quickstart

```bash
git clone <your-fork-url> && cd cognitive-ecology
pip install -e ".[dev]"
python examples/01_zero_llm_heartbeat/main.py
```

No keys, no network, no model. Watch the attention market price a
behavior every tick, then kill the purpose and bring it back.

## The ten-minute tour (do this one)

```bash
python experiments/minimal_world.py
```

A complete story: an organism forages under the attention market → its
root WHY is killed (nothing runs, nothing is deleted) → resurrection →
sleep with dreams → save to disk → **load into a fresh process and keep
living**. The file is written to be read top-to-bottom afterwards.

## Add a model (optional, and cheaper than you think)

```bash
export DEEPINFRA_API_KEY=...      # env-only; never a file, never a commit
python examples/02_research_assistant/main.py
```

The model answers from the *walked* subgraph under a **stable-prefix
cache session** that measures hit rates and savings (on
`tencent/Hy4-preview`, cached input is ~20× cheaper than fresh input —
the prompt's shape is a cost decision, so the kernel enforces the
discipline and journals the results).

## Examples (seven, all runnable keyless)

| Example | What it shows | Run |
|---|---|---|
| [01_zero_llm_heartbeat](examples/01_zero_llm_heartbeat/) | the whole kernel in 80 lines; kill & resurrect purpose | `python examples/01_zero_llm_heartbeat/main.py` |
| [02_research_assistant](examples/02_research_assistant/) | anti-RAG recall + a cached LLM citizen | `python examples/02_research_assistant/main.py` |
| [03_decision_desk](examples/03_decision_desk/) | decision models, hash-chained commitments, WHY-gated trading | `python examples/03_decision_desk/main.py` |
| [04_game_npc](examples/04_game_npc/) | a NPC whose memory survives server restarts | `python examples/04_game_npc/main.py` |
| [05_personal_journal](examples/05_personal_journal/) | memory that finds the story, not the string | `python examples/05_personal_journal/main.py` |
| [06_attestation_economy](examples/06_attestation_economy/) | use it or lose it: served vs unserved purpose, lapse, parole | `python examples/06_attestation_economy/main.py` |
| [07_audit_and_archive](examples/07_audit_and_archive/) | tamper with history and get caught; cold storage that is not deletion | `python examples/07_audit_and_archive/main.py` |
| [08_society](examples/08_society/) | delegated purpose: treaties, soft neglect, hard death, federation receipts | `python examples/08_society/main.py` |

## Documentation

| Doc | For |
|---|---|
| [docs/01_quick_start.md](docs/01_quick_start.md) | install + first organism |
| [docs/02_architecture.md](docs/02_architecture.md) | the stack, tick pipeline, design decisions |
| [docs/03_layers_reference.md](docs/03_layers_reference.md) | every layer's API and invariants |
| [docs/04_why_conservation.md](docs/04_why_conservation.md) | the WHY law, completely |
| [docs/05_attention_economics.md](docs/05_attention_economics.md) | the five factors, tuning, anti-patterns |
| [docs/06_agents_and_providers.md](docs/06_agents_and_providers.md) | LLMs as citizens + caching economics |
| [docs/07_playbook.md](docs/07_playbook.md) | how to play-test (and what play-testing found) |
| [docs/08_decision_models.md](docs/08_decision_models.md) | typed-decision synergy + experiment plan |
| [docs/ADRs/](docs/ADRs/) | 13 architecture decision records (the law, the economics, the proofs, the society, the DAG, the judgment) |
| [docs/tutorials/](docs/tutorials/) | four hands-on tutorials (first world → LLM agents) |

## FAQ (read this if you read nothing else)

**Is L0–L8 a pipeline where higher layers call lower ones?**
No — L0 is a tick scheduler that never calls a model; each layer is a
constraint or capability evaluated every tick.

**Does "WHY conservation" mean WHY nodes can't change?**
No — they can be killed, questioned, parked and revived freely. They
simply can never be *deleted*: no deletion API exists, the runtime
audits the invariant every 25 ticks (a violation raises), and the test
suite hammers it with randomized kill/revive storms. Every transition
is recorded in an append-only necrology.

**Isn't attention just a weighted score?**
It is a product, not a sum: `urgency × justification × opportunity ×
novelty × expected_value`. Any zero factor vetoes — that is the point.

**Is "anti-RAG" just a knowledge graph with vector search bolted on?**
No — there is no embedding or vector-index *code* in the kernel; the
only matches for `rg -i "embedding|faiss|annoy|hnsw" src/` are
docstrings denying it. Recall is best-first *traversal* scored by
weight and recency; relevance comes from co-occurrence, repetition and
attention, not similarity.

**Is script ecology genetic programming?**
No — scripts parameterize an audited action library (especially
LLM-proposed ones); mutation jitters numbers, not code; and dead scripts
are recorded, never garbage-collected.

**Why ticks instead of wall-clock?** Reproducibility: same seed, same
code, same life. Time inside the organism is a tick count.

**How does persistence actually work?** `Runtime.save()` writes two
files — `state.json` (why tree + necrology, graph, tensions, script
track records, identity + commitment chain, market stats) and
`events.jsonl` (the append-only event log). `Runtime.load(path,
attach)` rebuilds the organism — `attach()` re-declares your components
in code (closures are code, not data) and `adopt()` re-attaches saved
track records. Behavior is code; history is files. A before/after
restart transcript you can run yourself: `examples/04_game_npc`.

## Repository layout

```
cognitive-ecology/
├── src/cognitive_ecology/       the kernel (11 modules + agents/)
│   └── agents/                  providers, orchestrator, stable_prefix.md
├── experiments/                 minimal_world.py + dogfood/ artifacts
├── examples/                    seven runnable organisms
├── templates/                   agent template + play-test scenario template
├── docs/                        8 guides + 4 tutorials
├── scripts/                     run_rounds.py (telemetry), ideate.py (dogfood)
├── tests/                       121 tests incl. conservation storms
├── bootstrap.sh                 create the GitHub repo + first push (PAT via env)
├── Makefile                     setup / test / world / examples / guard
└── .github/workflows/ci.yml     test matrix + secret scan
```

## Security posture

- **API keys live in environment variables only.** No constructor
  accepts a key literal; nothing logs keys; `.env` is gitignored and
  `.env.example` ships names, not values.
- **CI fails on secret-shaped strings** (`ghp_…`, `sk-di-…`, `apikey_…`)
  anywhere in the tree — see `.github/workflows/ci.yml`.
- **`bootstrap.sh` uses an askpass shim** so the GitHub PAT transits
  memory, not disk.
- **LLM proposals cannot execute code** — typed actions from an audited
  library, validated and sanitized, dropped on any mismatch.

## Two development lines, one repo

This tree carries two implementations of the same manifesto:

- **`src/cognitive_ecology/` — v0.2.0, the subject of this README.** The
  documented kernel: L0–L8, conserved WHY, attention market, script
  ecology, agents-as-citizens, save/load persistence. All docs,
  tutorials and `examples/01–05` target this package.
- **`src/ecology/` — the v0.1 research line, kept intact as provenance.**
  A parallel implementation with a different WHY formalism (a parseable
  graph + attestation DSL), an LLM teacher layer (DeepInfra multi-model
  panel with `prompt_cache_key`, MiniMax, a TypeSafe Jev decision
  client, retry/backoff + circuit breaker, and a SQLite usage ledger —
  `data/usage.db`), a research panel harness (`src/ecology/research/`),
  ADRs (`docs/ADRs/`), its own examples (`examples/tiny_mud.py`,
  `examples/week_in_a_box.py`), and a library of live panel rounds with
  receipts (`library/rounds/` — including a devil's-advocate round).

Both packages install from this repo and both test suites run green
together (`pytest tests/` → 121 passing: 40 from the v0.2 kernel, 81
from the v0.1 line). New work should target `cognitive_ecology`; the
v0.1 line is preserved as research history.

## Status & roadmap

v0.3.0 — the economics of persistence: liveness as a subscription
(re-attestation, lapse, parole on revival), conservation as a receipt
(genesis + necrology + journal replay, hash-chained, self-vouching
saves), honest cold storage for ancient dead purposes, delegated
tie-breaking for calibrated decision models, and a calibration log that
measures who is confidently wrong. Soak-proven at 10,000 ticks.

The v0.4 frontier (from live ideation round 009, see
[library/rounds/](library/rounds/)) — item 1 landed as ADR-0011:

1. **SOCIETY-BASIS** — **SHIPPED (ADR-0011):** treaties are foreign
   purpose references that route attestation between organisms;
   service keeps the beneficiary's books fresh through its own
   re-attestation economics; provider death propagates hard (question
   + exchange receipt), neglect propagates soft (the beneficiary's own
   reaper); the federation auditor detects forged service and missed
   propagations; delegation chains flow one hop per exchange.
2. **WHY-DAG** — **SHIPPED (ADR-0012):** `declare(parents=(a, b))`;
   best-path verdict/justification (a jointly-justified purpose is as
   strong as its best living basis); path-survivor cascades with a
   fixpoint (no over-cascade, no under-cascade); stamping serves the
   whole DAG lineage; the auditor replays DAG bases and catches
   off-books re-parenting; trees keep bit-for-bit v0.2 semantics.
3. **OUTCOME-ARBITER** — **SHIPPED (ADR-0013):** the delegated
   tie-break is scored by realized outcomes — the arbiter's picks are
   probabilistic claims in the calibration immune system, overrides
   are compared against the action base rate, and a miscalibrated or
   value-destroying arbiter is benched to the deterministic shadow
   with a receipt (live round 014: jev benched at tick 25 on Brier
   0.307 while its overrides were value-positive).
4. **Journal compaction** — per-epoch rolling digests for the growing
   attestation journal (OPEN_QUESTIONS #13).

See [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) for the full ledger.

## License

MIT — see [LICENSE](LICENSE).
