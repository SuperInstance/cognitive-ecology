<!-- dogfood: model=tencent/Hy4-preview | prompt_tokens=1553 completion_tokens=2600 cached_tokens=0 latency_s=27.81 | date=2026-10-31 | tool=scripts/ideate.py -->

## D1. What is STILL confusing or missing for a smart newcomer

| # | Confusion / gap | Concrete fix |
|---|---|---|
| 1 | **“How does an agent actually do anything?”** The README lists layers, but never shows a script’s anatomy: how a script bids, runs, emits events, touches the graph, and dies. “Typed actions” is named but never defined. | Add a **“Script anatomy”** section with a 15-line example: `class Greeter(Script): def why_should_this_run(); def bid(ctx); def run(ctx)` using `ctx.emit(...)`, `ctx.graph.touch(...)`, and show the resulting necrology entry. Link to `examples/01`. |
| 2 | **WHY nodes are abstract.** Root/child, states, cascade-to-UNKNOWN, and revival are named, but there is no schema, no creation flow, and no example of a WHY tree outside the kill/resurrect snippet. | Add a **“WHY node schema + lifecycle”** block: JSON with `id, statement, parent, state, confidence, evidence, born_tick, last_evaluated`, plus a 4-row state-transition table: `alive -> dead`, `root dead -> descendants UNKNOWN`, `UNKNOWN -> alive on revival`, `absent`. |
| 3 | **Persistence is asserted, not shown.** “save/load/adopt” and “history in files” appear, but not the on-disk format, what is included, or how versioning/migration works. | Add a **“Saved organism layout”** tree: `events.jsonl`, `graph.json`, `why.json`, `scripts/`, `necrology.jsonl`, `identity.json`, `meta.json`. One sentence: “`load()` validates `schema_version`; `adopt()` replays events if the graph is missing.” |
| 4 | **Attention market is a formula, not a mechanism.** Factors are listed, but not who sets them, their ranges, normalization, top-k clearing, starvation threshold, or tie-breaking. | Add a **“Market clearing example”**: 3 bids with factor tuples, product scores, `top_k=2`, starvation cutoff, and one vetoed bid. Include 10-line executive pseudocode. Link to `docs/attention.md`. |
| 5 | **No operational envelope or failure modes.** “121 tests, deterministic” is good, but a newcomer cannot tell the performance limits, growth pathologies, or debugging story. | Add a **“Limits & observability”** section: tested graph size, events/sec, tick cost, `kernel.trace(tick)` output, how to cap script population, and known failure modes: log growth, attention collapse, WHY deadlock, zombie scripts. |

## D2. Overreaching or under-evidenced claims

| Claim | Why it is weak | Evidence needed |
|---|---|---|
| “Agents that persist like organisms.” | Organism is a metaphor; the README does not show behavioral continuity across sessions beyond save/load. | A before/after transcript: same organism, fresh process, same WHY tree, same identity hash, same script population, and a changed-but-continuous graph. |
| “WHY: a purpose that cannot be deleted.” | Conservation is implemented for WHY nodes, but not for the *agent’s* purpose if the code/root config is deleted. The claim needs scoping. | State precisely: WHY nodes are never deleted from state; root deletion cascades to UNKNOWN; revival requires the node record. Show `why.export()` / `why.audit()` proving no deletion path exists. |
| “Anti-RAG: no embedding index anywhere.” | Strong and useful, but unverified from the README alone. | A test or doc line: `grep -R "embedding|faiss|annoy|hnsw" src/` returns nothing, plus a benchmark: `walk()` returns causal/biographical paths, not nearest-neighbor chunks. |
| “Attention = product; any zero vetoes.” | Clear, but no evidence that this produces sane scheduling under load. | A simulation table: N scripts, factor distributions, top-k over 100 ticks, starvation rate, and comparison against additive scoring. |
| “LLMs are citizens, not kings.” | Rhetorically strong; the README does not show a proposal being rejected by WHY or starved by the market. | Example 02/03 should show: LLM proposes script → WHY rejects → necrology/audit records rejection → market starves a low-justification proposal. |
| “Cached input ~20x cheaper than fresh.” | A pricing claim with no measurement in the README. | A reproducible table: model, cached vs fresh token counts, measured hit rate over K ticks, cost delta, and the stable-prefix construction. |
| “v0.2.0 kernel complete and tested.” |
