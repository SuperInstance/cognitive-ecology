<!-- dogfood: model=tencent/Hy4-preview | prompt_tokens=678 completion_tokens=2800 cached_tokens=256 latency_s=54.21 | date=2026-10-31 | tool=scripts/ideate.py -->

## TASK B — Newcomer comprehension: top 5 misconceptions

| # | Misconception / confusion | One-sentence README/docs fix |
|---|---|---|
| 1 | **“L0–L8 is a call stack / pipeline / OSI-style hierarchy.”** They assume L0 invokes models, L8 is a background service, and higher layers call lower layers in sequence. | “L0–L8 are not a call stack or pipeline: L0 is a tick scheduler that never calls a model, and each layer is a constraint or capability evaluated every tick, with LLMs and decision models as citizens that propose actions rather than drive execution.” |
| 2 | **“WHY conservation law means WHY nodes are immutable or always alive.”** They hear “never deleted” and think WHY roots cannot be killed or that state never changes. | “The WHY conservation law means a WHY node is never deleted from the log; it can be marked dead or questionable (UNKNOWN) and later revived, but its history and causal links always remain.” |
| 3 | **“Attention economics is a priority queue or weighted score.”** They expect `score = sum(weights)` and assume a zero factor can be compensated by others. | “Attention is a multiplicative market, not a weighted sum: a bid is `urgency × justification × opportunity × novelty × expected_value`, so any factor of zero vetoes the bid entirely, and only the top-k surviving bids are cleared each tick.” |
| 4 | **“Anti-RAG means ‘no retrieval’ or ‘just a knowledge graph with vector search.’”** They assume embeddings are still the retrieval mechanism, or that anti-RAG means no recall at all. | “Anti-RAG means recall is attention-guided traversal of a typed graph whose nodes carry biographies (`born_tick`, `last_seen`, `weight`); there is no embedding index, and relevance comes from co-occurrence, repetition, decay, and current attention, not vector similarity.” |
| 5 | **“Script ecology is genetic programming / free-form code evolution.”** They assume scripts are arbitrary code, dead scripts are deleted, and mutation is unrestricted rewriting. | “Script ecology is a population of small, parameterized scripts drawn from a safe action library that compete for attention, starve, and die with an immutable necrology entry; mutations are proposed variants, often during sleep, and the WHY tree—not raw fitness—decides what may exist.” |

---

## TASK C — Cache economics experiments

**Baseline arithmetic constants**

- Stable prefix: **6,000 tokens**
- Iterations: **100**
- Model: `tencent/Hy4-preview` on DeepInfra
- Prices per 1M tokens:
  - Input: **$0.834**
  - Cached input: **$0.042**
  - Output: **$2.501**
- Context window: **1M tokens**
- Automatic prefix caching; optional `prompt_cache_key`

**Core unit economics for the 6,000-token prefix**

| Quantity | Value |
|---|---|
| Prefix tokens | 6,000 |
| Prefix cost if uncached | `6,000 / 1,000,000 × $0.834 = $0.005004` |
| Prefix cost if cached | `6,000 / 1,000,000 × $0.042 = $0.000252` |
| Per-iteration prefix saving | `$0.005004 − $0.000252 = $0.004752` |
| 100-iteration prefix saving | `100 × $0.004752 = $0.4752` |
| Cache-hit ratio needed to break even vs. no cache | any hit avoids the $0.005004 uncached charge; cached is ~**95.0% cheaper** per prefix token |

**Assumed non-prefix workload per iteration**

- New user/agent input: **1,500 tokens**
- Tool/state/context delta: **2,500 tokens**
- Output: **800 tokens**
- Non-prefix input per iteration: `1,500 + 2,500 = 4,000 tokens`

Uncached input cost per iteration:  
`(6,000 + 4,000) / 1,000,000 × $0.834 = $0.00834`

Cached-input cost per iteration:  
`(6,000 / 1,000,000 × $0.042) + (4,000 / 1,000,000 × $0.834) = $0.000252 + $0.003336 = $0.003588`

Output cost per iteration:  
`800 / 1,000,000 × $2.501 = $0.0020008`

| Per-iteration total | Uncached prefix | Cached prefix |
|---|---|---|
| Input | $0.008340 | $0.003588 |
| Output | $0.002001 | $0.002001 |
| **Total** | **$0.010341** | **$0.005589** |
| **Saving** | — | **$0.004752** |

**100-iteration totals**

| Scenario | Input | Output | Total |
|---|---|---|---|
| No prefix caching | $0.8340 | $0
