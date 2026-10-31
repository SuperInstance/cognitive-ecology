# Providers — observed behavior, not documentation claims

*Everything below was observed live from this account on 2026-10-31
(probe receipts in the session journal; scripts in `scripts/`). Where a
provider's docs disagree with observation, observation wins and the
disagreement is noted.*

## DeepInfra — primary panel provider ✅

- Endpoint: `POST https://api.deepinfra.com/v1/openai/chat/completions` (Bearer).
- All 7 target models present: Seed-2.0-mini/pro, MiMo-V2.6-Pro,
  Nemotron-3-Ultra-550B-A55B, Qwen3.8-Max, Ling-3.1-flash, Hy4-preview.
- **Caching observed:** `usage.prompt_tokens_details.cached_tokens`
  (0 for a 59-token probe — below the ~1k cache floor; 6,560 tokens cached
  across round 001 where prefixes were large and append-only, ~9% of input
  on first-round-heavy traffic and rising as transcripts grow).
- **Cost observed:** `usage.estimated_cost` returned per call and recorded
  verbatim in the ledger. Round 001 (13 turns, 70,620 in / ~19k out across
  7 models): **$0.064**.
- Latency observed: 1.2–1.4s for tiny calls; 5–90s for panel turns
  (Nemotron and Hy4 are the slow seats; Ling-3.1-flash the fastest).

## TypeSafe (Jev) — decision gates ✅

- `GET /v1/models` → jev-latest → jev-1.14.0; `POST /v1/systemone` (Bearer).
- Latency observed: 178–213ms per gate. Pricing as documented: input-only,
  $0.042/Mtok — five gates in this session cost well under $0.001.
- **Schema lesson (learned by breaking it):** `choice` criteria is a map of
  `{option_name: "when it applies"}` — passing `{"options": [...]}` yields
  a degenerate answer (`choice: "options"`). The OpenAPI spec at
  `api.typesafe.ai/openapi.json` is the source of truth; the client now
  builds correct shapes and the round gates returned real distributions.
- Gates produced genuinely useful signal: round-001 coherence 2.12 → 2.22,
  next-focus converging on `architect` 0.51 → 0.89; devil's-advocate
  concreteness 0.34 → 0.50.

## MiniMax — blocked ❌ (key rejected)

- The provided `sk-cp-…` key returns **401 "login fail"** on every
  combination tried: `api.minimax.io/anthropic` (x-api-key, Bearer, both),
  `api.minimax.io/v1/chat/completions` (Bearer, x-api-key),
  `api.minimaxi.com` and `api.minimax.chat` variants. The endpoints
  respond (error shapes differ per protocol), so this is authentication,
  not reachability.
- Consequence: the panel's ideator seat is vacant; `MINIMAX_API_KEY` is
  commented out in `.env` with a note. Re-enable when a working key
  arrives — the client is implemented and tested against the documented
  anthropic-compatible shape (`x-api-key` header, `cache_read_input_tokens`
  parsing).

## Cost accounting

Ledger at `data/usage.db` (gitignored), report via `ecology usage`. All
panel rounds this session: **~$0.116 total**. The cache-first protocol is
the reason the 7-model panel is affordable: from round 2 onward, every
panelist's context is mostly a cache hit at 80–90% off.
