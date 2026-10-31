# Provider & decision-model research — 2026-10-31

*Compiled by a research subagent (web-verified, sources cited). Ground
truth for live behavior is the probe receipts in docs/PROVIDERS.md; this
document is the map, that one is the territory.*

## TypeSafe AI — Jev, "System One" decision models

- Base `https://api.typesafe.ai`; OpenAPI 3.1 at `/openapi.json` (v0.2.0).
- `POST /v1/systemone` with `{model, state, questions, assets?}`;
  `GET /v1/models`. Auth: `Authorization: Bearer <key>`.
- Question types: `noul` (P(yes)), `choice` (criteria = map of option name →
  when-it-applies description; answer carries choice + confidence + full
  probabilities), `score` (criteria = ordered rubric array; answer is an
  expected score that may fall between levels), `box` (images; needs the
  `TypeSafe-Danger-Zone-Images` header).
- Answers are typed and calibrated (RLCD training); ~70-500ms; all
  questions in a request are evaluated in parallel.
- Pricing: **$42/Btok input ($0.042/Mtok), output tokens free** — cheap
  enough to gate every panel round. 429 and 529 (Overloaded) are the
  retry-worthy statuses; SDKs honor `retry-after`.
- Models: `jev-latest` → jev-1.14.0 (2026-10-22) at probe time.
- Real-world usage patterns worth copying: confidence-thresholded routing
  (Vercel replaced a safety classifier — 5-18× faster at higher accuracy);
  per-row noul gates in document review (Unsiloed); speculative fan-out;
  composite scoring; hierarchical classification via beam search over
  choice probabilities (official cookbooks).

## MiniMax (international)

- Anthropic-compatible: `https://api.minimax.io/anthropic` → `POST
  /anthropic/v1/messages`; OpenAI-compatible `…/v1/chat/completions` also
  exists. Auth wants `x-api-key` (anthropic-style) or Bearer (openai-style).
- Models: `MiniMax-M3.1-Flash` (1M ctx, multimodal, tunable thinking depth
  via `output_config.effort`), `MiniMax-M3`.
- Pricing: M3.1-Flash $0.15 in / $0.60 out / $0.015 cache-read per Mtok.
  Automatic prompt caching, reported as `usage.cache_read_input_tokens`.
- **Live status for this repo: the provided key authenticates nowhere**
  (401 on every host/auth combination — see docs/PROVIDERS.md). The panel
  runs without it; the ideator seat is vacant until a working key arrives.

## DeepInfra

- OpenAI-compatible: `POST https://api.deepinfra.com/v1/openai/chat/completions`.
- **Prompt caching is automatic** (prefix KV reuse, no cache_control
  markers): stable content first; optional `prompt_cache_key` scopes the
  cache to a session; hits reported in
  `usage.prompt_tokens_details.cached_tokens`; cache-read is 80-87.5% off
  list on the panel models. Note: prompts under ~1k tokens will show zero
  cached tokens (below the cache floor) — the panel's shared context is
  comfortably above it.
- Panel models (all confirmed present, prices $/Mtok in/out/cache-read):
  Seed-2.0-mini 0.10/0.40/0.02 · Seed-2.0-pro 0.50/3.00/0.10 ·
  MiMo-V2.6-Pro 0.43/0.87/0.0036 · Nemotron-3-Ultra 0.50/2.20/0.10 ·
  Qwen3.8-Max 1.65/4.95/0.206 · Ling-3.1-flash 0.075/0.225/0.015 ·
  Hy4-preview 0.834/2.501/0.042.
- 429 = "Rate limited" (retry after a short delay; limit is concurrent
  requests per model, default 200). DeepInfra also returns
  `usage.estimated_cost` per call — recorded verbatim in our ledger.

## Decision-model landscape (beyond TypeSafe)

OpenAI Decisions API (`gpt-6-luna`, predicate/choice/score — public beta
2026-09-29) · Vercel AI Gateway Decisions (routes Jev, Luna, Microsoft
Decision-1, Laya, Liquid d1 in one format) · **Cloudflare Clef** on
DeepInfra (`POST /v1/decisions`, Jev/SystemOne-compatible, $0.24/Mtok) —
a drop-in second decision provider for this repo's `DecisionClient` ·
Ollaya (local, Ollama-for-decision-models) · open Jev-family (Kev on
Qwen3.5/3.8, Jeff 0.8B, von sub-15ms) · classics: AHPy, scikit-criteria,
pgmpy, Decision Transformer.

*Sources: docs.typesafe.ai, techcrunch.com (2026-09-18 Jev launch),
platform.minimax.io, docs.deepinfra.com, vercel.com/i/what-is-openai-decisions-api,
github.com/jaredpalmer/kev, ollaya.dev — full URLs in the session receipts.*
