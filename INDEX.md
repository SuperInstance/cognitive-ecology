# Index — the map of everything

Start with README.md (the pitch + FAQ), then docs/ in numbered order.
This file is for finding things fast.

## The kernel (`src/cognitive_ecology/`)

| File | Layer | One line |
|---|---|---|
| `runtime.py` | L0 | the body: ticks, gates, audits; never calls a model |
| `events.py` | L1 | MIDI-sized immutable events, causal chains, append-only |
| `graph.py` | L2 | anti-RAG world graph: biography + traversal recall |
| `memory.py` | L3 | events → graph (Hebbian co-occurrence, replay) |
| `scripts.py` | L4 | script ecology: spawn/fire/starve/die/mutate/necrology |
| `attention.py` | L5 | the market: five multiplicative factors, veto law |
| `executive.py` | L5 | clears top-k, resolves resources, cause-chains |
| `why.py` | L6 ★ | conserved purpose: 4 states, cascades, necrology |
| `identity.py` | L7 | self-model, hash-chained commitments, stable introspect |
| `sleep.py` | L8 | replay / prune / dream on idleness |
| `tension.py` | — | homeostatic drives (where urgency comes from) |
| `simulations.py` | — | heuristic forecasts / rollouts for expected_value |
| `util.py` | — | clamp, EMA, stable_hash, slug |
| `agents/providers.py` | — | OpenAI-compatible + mock providers, cache session |
| `agents/orchestrator.py` | — | LLMAgent: proposals from the safe action library |
| `agents/stable_prefix.md` | — | the caching discipline + prompt template |

## Experiments & tools

| Path | What it is |
|---|---|
| `experiments/minimal_world.py` | the ten-minute organism (the tour — read it) |
| `experiments/dogfood/` | artifacts + token/cache journals from ideating with real models |
| `scripts/run_rounds.py` | headless runner with per-tick JSONL telemetry |
| `scripts/ideate.py` | dogfood ideation loop (stable prefix, env-only keys) |
| `templates/agent_template.py` | fill-in-the-blanks organism |
| `templates/scenario_template.md` | play-test plan template + 8 seeded scenarios |

## Examples

| Path | Domain | Teaches |
|---|---|---|
| `examples/01_zero_llm_heartbeat/` | tutorial | the 60-second kernel; kill & resurrect |
| `examples/02_research_assistant/` | research | anti-RAG recall; cached LLM citizen |
| `examples/03_decision_desk/` | finance | decision models; commitments; WHY-gated action |
| `examples/04_game_npc/` | games | memory across restarts (save/load/adopt) |
| `examples/05_personal_journal/` | personal | memory finds the story; nag with manners |
| `examples/06_attestation_economy/` | economics | use it or lose it: served vs unserved purpose, lapse, parole |
| `examples/07_audit_and_archive/` | audit | tamper with history and get caught; cold storage that is not deletion |
| `examples/08_society/` | society | delegated purpose: treaties, soft neglect, hard death, federation receipts |
| `examples/09_host_drivers/` | hosting | game loop / wall-clock / cron + checkpoint rotation |
## Docs

| Path | Subject |
|---|---|
| `docs/01_quick_start.md` | install → first organism in 5 minutes |
| `docs/02_architecture.md` | stack, tick pipeline, decisions, misconceptions |
| `docs/03_layers_reference.md` | per-layer API + invariants |
| `docs/04_why_conservation.md` | the WHY law completely |
| `docs/05_attention_economics.md` | the five factors + tuning guide |
| `docs/06_agents_and_providers.md` | models as citizens; caching economics |
| `docs/07_playbook.md` | play-testing method + findings log |
| `docs/08_decision_models.md` | decision-model synergy + experiments |
| `docs/09_market_log.md` | the observation read model + run provenance |
| `docs/10_host_integration.md` | hosting: drivers, recipes, the world-not-bus ingest law |
| `docs/tutorials/tutorial_01_first_world.md` | build a lighthouse keeper |
| `docs/tutorials/tutorial_02_script_ecology.md` | birth, starvation, death, dreams |
| `docs/tutorials/tutorial_03_attention_market.md` | controlled experiments on the factors |
| `docs/tutorials/tutorial_04_llm_agents_and_caching.md` | LLM citizens + the caching game |
| `docs/ADRs/` | 15 architecture decision records (the law, the economics, the proofs, the society, the DAG, the judgment, the ballast, the read model) |
| `docs/MIGRATIONS.md` | upgrading organisms across versions |

## The v0.1 research line (`src/ecology/` — kept as provenance)

A parallel implementation from an earlier line of work; installed and
tested alongside the kernel (81 of the 324 tests). Preserved intact.

| Path | What it is |
|---|---|
| `src/ecology/why/` | an alternative WHY formalism: parseable graph + attestation DSL |
| `src/ecology/llm/` | teacher layer: DeepInfra panel (`prompt_cache_key`, cached-token accounting), MiniMax, TypeSafe Jev decision client, retry/backoff, circuit breaker |
| `src/ecology/research/` | panel + discussion harness for live model debates |
| `src/ecology/` (rest) | its own runtime, scripts, sleep, identity, briefing, sim, world, CLI |
| `data/usage.db` | SQLite usage ledger — real spend receipts from the panel rounds |
| `library/` | research library: rounds, reflections, originals, open-questions ledger |
| `library/rounds/` | 3 live panel rounds incl. a devil's-advocate round (receipts) |
| `docs/ADRs/` (0001–0006) | the ADRs written during that line's era; 0007 onward belong to the kernel line (14 total, machine-checked) |
| `docs/ARCHITECTURE.md`, `PROVIDERS.md`, `JOURNAL.md`, `PROCESS.md`, `docs/MANIFESTO.md` | that line's docs |
| `examples/tiny_mud.py`, `examples/week_in_a_box.py` | its demo organisms (may need API keys) |

## Root

| Path | Subject |
|---|---|
| `README.md` | the pitch, quickstarts, FAQ |
| `MANIFESTO.md` | why this exists |
| `AUDIT.md` | self-audit matrix + external-audit section |
| `OPEN_QUESTIONS.md` | the honest research frontier |
| `CHANGELOG.md` | 0.1.0 → 0.4.0 (+ Unreleased) |
| `CONTRIBUTING.md` | small steps, tests, no secrets, play-tests |
| `bootstrap.sh` | create the GitHub repo + first push (PAT from env) |
| `Makefile` | setup / test / world / examples / guard |
