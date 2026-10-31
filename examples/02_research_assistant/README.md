# Example 02 — Research Assistant with an Anti-RAG Memory (LLM citizen)

**What this teaches:** the anti-RAG loop. A small corpus is ingested into
the **World Graph**; questions are answered by *walking* the graph from
cue entities (attention-guided traversal) — no embeddings, no vector
store. When an LLM is available it answers *from the walked context*,
under a **stable-prefix cache session** that measures real token savings.
Without a key it falls back to the deterministic MockProvider, so the
example always runs.

**Run it:**

```bash
# keyless (mock model, simulated caching):
python examples/02_research_assistant/main.py

# with a real model (tencent/Hy4-preview on DeepInfra):
export DEEPINFRA_API_KEY=...        # env-only; never a file
python examples/02_research_assistant/main.py
```

**What you should see:**

```
[ingest] 10 notes -> 24 graph nodes, 31 edges (Hebbian co-occurrence)
[walk]   cue: [caching, attention] -> visited: caching, attention, cost, ...
[answer] (model output grounded in the walked context)
[cached] hit_rate=87.5%  cached=...tok  est_saved=$0.00xx
```

**The point:** recall quality here comes from co-occurrence, repetition
and recency — the same signals attention uses — not from vector
similarity. And because the system prompt (persona + rules) is frozen,
every question after the first reuses the provider's prompt cache.
