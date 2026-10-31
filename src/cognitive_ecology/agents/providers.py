"""Model providers — LLMs and decision models join as citizens.

Three rules for every provider in this kernel:

1. KEYS LIVE IN ENVIRONMENT VARIABLES ONLY. No constructor takes a key
   literal, no file stores one, no log prints one. If a key is missing we
   raise — we never fall back to a hardcoded credential.
2. MODELS ARE CITIZENS. A provider returns text; it never gets to decide
   what runs. The WHY tree and the attention market stay in charge.
3. CACHING IS A FIRST-CLASS CONCERN. ``StablePrefixSession`` enforces the
   stable-prefix / volatile-suffix discipline, journals every call's token
   usage and cache hits, and reports estimated savings.

Default endpoint is DeepInfra running ``tencent/Hy4-preview`` (770B MoE,
49B active, 1M context) — cheap, strong for long-horizon agentic work, and
with automatic prefix caching: cached input bills at ~1/20th of fresh
input. Point ``TYPESAFE_BASE_URL`` at any OpenAI-compatible decision-model
endpoint (e.g. OpenRouter) to use calibrated typed decisions instead of
free text — see docs/08_decision_models.md.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Optional

from ..util import stable_hash

# Default endpoints. Override any of them with <PREFIX>_BASE_URL,
# <PREFIX>_API_KEY, <PREFIX>_MODEL, <PREFIX>_CACHE_KEY in the environment.
DEFAULTS = {
    "DEEPINFRA": {
        "base_url": "https://api.deepinfra.com/v1/openai",
        "model": "tencent/Hy4-preview",
    },
    # typesafe.ai serves typed decisions with calibrated confidence
    # ("System One Models", e.g. Jev). It is reachable through OpenRouter's
    # OpenAI-compatible API — check the current model id on openrouter.ai.
    "TYPESAFE": {
        "base_url": "https://openrouter.ai/api/v1",
        "model": "typesafe/jev-1.0",
    },
}

# tencent/Hy4-preview on DeepInfra, USD per 1M tokens (checked 2026-10-31).
# Cached input is ~20x cheaper than fresh input: the entire reason the
# stable-prefix discipline exists.
HY4_PRICES = {"input": 0.834, "cached": 0.042, "output": 2.501}


@dataclass
class Completion:
    """One model turn, with the cache accounting attached."""

    text: str
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_tokens: int = 0
    latency_s: float = 0.0
    raw: Optional[dict] = None


class OpenAICompatProvider:
    """Any OpenAI-compatible /chat/completions endpoint.

    Works with DeepInfra, OpenRouter, and self-hosted vLLM/SGLang servers
    (Hy4-preview ships vLLM and SGLang deployment recipes). Uses stdlib
    urllib on purpose: the kernel stays dependency-free.
    """

    def __init__(self, base_url: str, api_key: str, model: str,
                 timeout: float = 180.0, retries: int = 3,
                 prompt_cache_key: Optional[str] = None) -> None:
        if not api_key:
            raise ValueError(
                "api_key is empty — providers read keys from the environment "
                "(e.g. DEEPINFRA_API_KEY); hardcoded keys are not supported"
            )
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.retries = retries
        self.prompt_cache_key = prompt_cache_key

    # ------------------------------------------------------------------
    @classmethod
    def from_env(cls, prefix: str = "DEEPINFRA") -> "OpenAICompatProvider":
        """Build a provider from <PREFIX>_BASE_URL/_API_KEY/_MODEL/_CACHE_KEY."""
        defaults = DEFAULTS.get(prefix, {"base_url": "", "model": "gpt"})
        base = os.environ.get(f"{prefix}_BASE_URL", defaults["base_url"])
        key = os.environ.get(f"{prefix}_API_KEY", "")
        model = os.environ.get(f"{prefix}_MODEL", defaults["model"])
        cache_key = os.environ.get(f"{prefix}_CACHE_KEY") or None
        return cls(base, key, model, prompt_cache_key=cache_key)

    @property
    def name(self) -> str:
        return f"{self.model} @ {self.base_url}"

    def complete(self, system: str, user: str, max_tokens: int = 800,
                 temperature: float = 0.7) -> Completion:
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if self.prompt_cache_key:
            # Session-scoped cache key: near-identical prompts always hit.
            body["prompt_cache_key"] = self.prompt_cache_key
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        last_err: Optional[Exception] = None
        for attempt in range(self.retries):
            try:
                t0 = time.time()
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    data = json.loads(resp.read())
                usage = data.get("usage") or {}
                details = usage.get("prompt_tokens_details") or {}
                return Completion(
                    text=data["choices"][0]["message"]["content"],
                    model=data.get("model", self.model),
                    prompt_tokens=int(usage.get("prompt_tokens", 0)),
                    completion_tokens=int(usage.get("completion_tokens", 0)),
                    cached_tokens=int(details.get("cached_tokens", 0) or 0),
                    latency_s=round(time.time() - t0, 2),
                    raw=data,
                )
            except urllib.error.HTTPError as e:
                last_err = e
                if e.code in (429, 500, 502, 503) and attempt < self.retries - 1:
                    time.sleep(2.0 * (attempt + 1))
                    continue
                raise
            except Exception as e:  # network blip
                last_err = e
                if attempt < self.retries - 1:
                    time.sleep(2.0 * (attempt + 1))
                    continue
                raise
        raise last_err  # pragma: no cover


class MockProvider:
    """Deterministic, zero-LLM provider — for tests, CI, and keyless demos.

    Also SIMULATES prefix caching (a repeated system prompt reports
    cached_tokens) so cache-economics demos run without an API key. The
    simulation is clearly marked in stats(): provider="mock".
    """

    def __init__(self, model: str = "mock-1") -> None:
        self.model = model
        self._seen_systems: set = set()

    @property
    def name(self) -> str:
        return f"{self.model} (mock)"

    def complete(self, system: str, user: str, max_tokens: int = 800,
                 temperature: float = 0.7) -> Completion:
        sys_hash = stable_hash(system)
        cached = len(system) // 4 if sys_hash in self._seen_systems else 0
        self._seen_systems.add(sys_hash)
        # Deterministic proposal set: same prompt neighborhood -> same ideas.
        seedling = int(stable_hash({"s": system[-64:], "u": user[-64:]}), 16)
        topics = ["cache-economics", "foraging-routes", "rare-events",
                  "sleep-scheduling", "why-audit", "novelty-metrics"]
        picks = [topics[(seedling >> (3 * i)) % len(topics)] for i in range(3)]
        proposals = [
            {
                "name": f"watch-{p}",
                "action": "search",
                "args": {"topic": p},
                "relieves": ["curiosity"],
                "focus": [f"topic:{p}"],
                "when_hint": "always",
            }
            for p in picks
        ][: 1 + seedling % 3]
        return Completion(
            text=json.dumps({"proposals": proposals}),
            model=self.model,
            prompt_tokens=(len(system) + len(user)) // 4,
            completion_tokens=120,
            cached_tokens=cached,
            latency_s=0.0,
        )


class StablePrefixSession:
    """The caching discipline, enforced and measured.

    Providers cache the LONGEST IDENTICAL PREFIX of your prompt. So:

    * the STABLE PREFIX (system prompt) is frozen for the session's life —
      identity, action library, output contract;
    * everything volatile (tensions, world digest, the current ask) goes
      in the USER message, appended after the prefix;
    * every call journals tokens / cached_tokens / hashes, so savings are
      measured, not assumed;
    * changing the prefix is possible only via ``set_prefix(reason)`` and
      is counted — every change is a cache bust you chose.
    """

    def __init__(self, provider, prefix: str,
                 journal_path: Optional[str] = None, label: str = "session",
                 prices: Optional[dict] = None) -> None:
        self.provider = provider
        self.prefix = prefix
        self._prefix_hash = stable_hash(prefix)
        self.journal_path = journal_path
        self.label = label
        self.prices = dict(prices or HY4_PRICES)
        # counters
        self.calls = 0
        self.prompt_tokens = 0
        self.cached_tokens = 0
        self.completion_tokens = 0
        self.prefix_changes = 0

    # ------------------------------------------------------------------
    def call(self, suffix: str, max_tokens: int = 800,
             temperature: float = 0.7) -> Completion:
        """One turn: frozen prefix + volatile suffix. Journaled."""
        current_hash = stable_hash(self.prefix)
        if current_hash != self._prefix_hash:
            # Only possible after set_prefix(); counted as a chosen bust.
            self._prefix_hash = current_hash
        c = self.provider.complete(
            self.prefix, suffix, max_tokens=max_tokens, temperature=temperature
        )
        self.calls += 1
        self.prompt_tokens += c.prompt_tokens
        self.cached_tokens += c.cached_tokens
        self.completion_tokens += c.completion_tokens
        self._journal({
            "label": self.label, "prefix_sha": self._prefix_hash,
            "suffix_sha": stable_hash(suffix), "model": c.model,
            "prompt_tokens": c.prompt_tokens,
            "cached_tokens": c.cached_tokens,
            "completion_tokens": c.completion_tokens,
            "latency_s": c.latency_s,
        })
        return c

    def set_prefix(self, new_prefix: str, reason: str = "deliberate drift") -> None:
        """The only sanctioned way to change the prefix. Counted + journaled."""
        self.prefix = new_prefix
        self.prefix_changes += 1
        self._prefix_hash = stable_hash(new_prefix)
        self._journal({"label": self.label, "prefix_change": reason})

    # ------------------------------------------------------------------
    def _journal(self, record: dict) -> None:
        if not self.journal_path:
            return
        directory = os.path.dirname(self.journal_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        record = dict(record)
        record["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        with open(self.journal_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, sort_keys=True) + "\n")

    def stats(self) -> dict:
        """Measured cache economics for this session (USD estimates)."""
        p = self.prices
        fresh = self.prompt_tokens - self.cached_tokens
        est_cost = (
            fresh * p["input"] + self.cached_tokens * p["cached"]
            + self.completion_tokens * p["output"]
        ) / 1_000_000
        est_no_cache = (
            self.prompt_tokens * p["input"]
            + self.completion_tokens * p["output"]
        ) / 1_000_000
        return {
            "provider": getattr(self.provider, "name", "mock"),
            "calls": self.calls,
            "prompt_tokens": self.prompt_tokens,
            "cached_tokens": self.cached_tokens,
            "cache_hit_rate": round(
                self.cached_tokens / self.prompt_tokens, 4
            ) if self.prompt_tokens else 0.0,
            "prefix_changes": self.prefix_changes,
            "est_cost_usd": round(est_cost, 6),
            "est_cost_without_cache_usd": round(est_no_cache, 6),
            "est_saved_usd": round(est_no_cache - est_cost, 6),
            "prices_per_1m": p,
        }
