"""DeepInfra chat client — the multi-model panel workhorse.

OpenAI-compatible endpoint with automatic prefix caching:
- stable content first (our PromptSpec guarantees byte-stable prefixes),
- ``prompt_cache_key`` scopes the cache to the session,
- cache hits are reported in ``usage.prompt_tokens_details.cached_tokens``,
- DeepInfra also reports ``usage.estimated_cost`` per call, which we record
  verbatim (it beats our price table).

Confirmed present on the account (2026-10-31): ByteDance/Seed-2.0-mini,
ByteDance/Seed-2.0-pro, XiaomiMiMo/MiMo-V2.6-Pro,
nvidia/NVIDIA-Nemotron-3-Ultra-550B-A55B, Qwen/Qwen3.8-Max,
inclusionAI/Ling-3.1-flash, tencent/Hy4-preview.
"""

from __future__ import annotations

import httpx

from ..config import Settings
from .base import LLMResponse, PromptSpec, Usage
from .ledger import Ledger
from .resilience import CircuitBreaker, RetryPolicy, TokenBucket

BASE_URL = "https://api.deepinfra.com/v1/openai"


class DeepInfraError(RuntimeError):
    def __init__(self, status: int, body: str, retry_after: float | None = None):
        super().__init__(f"deepinfra {status}: {body[:200]}")
        self.status = status
        self.retry_after = retry_after


def _retryable(exc: Exception) -> bool:
    status = getattr(exc, "status", None)
    if status is None:
        return isinstance(exc, (httpx.TransportError, httpx.TimeoutException))
    return status in (408, 409, 425, 429, 500, 502, 503, 504, 529)


class DeepInfraClient:
    provider = "deepinfra"

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        ledger: Ledger | None = None,
        client: httpx.Client | None = None,
        retry: RetryPolicy | None = None,
        limiter: TokenBucket | None = None,
        breaker: CircuitBreaker | None = None,
    ):
        self.settings = settings or Settings.from_env()
        self.ledger = ledger
        self._client = client or httpx.Client(timeout=120)
        self.retry = retry or RetryPolicy()
        # DeepInfra's documented limit is concurrency, not RPM; 2 rps is a
        # polite steady-state for a sequential panel.
        self.limiter = limiter or TokenBucket(rate=2.0, capacity=6.0)
        self.breaker = breaker or CircuitBreaker()

    @property
    def default_model(self) -> str:
        return self.settings.deepinfra_model

    def complete(
        self, spec: PromptSpec, model: str | None = None, *, role: str = ""
    ) -> LLMResponse:
        chosen = model or self.settings.deepinfra_model
        if not self.settings.deepinfra_api_key:
            raise RuntimeError("DEEPINFRA_API_KEY not set")
        if not self.breaker.allow():
            raise RuntimeError("circuit open for deepinfra (recent failures)")

        payload = {
            "model": chosen,
            # cache-first message order: stable system prefix, then the
            # (append-only) prefix content, then the variable suffix last
            "messages": [
                {"role": "system", "content": spec.stable_prefix},
                {"role": "user", "content": spec.variable_suffix},
            ],
            "max_tokens": spec.max_tokens,
            "prompt_cache_key": f"ecology-{role or 'panel'}",
        }
        if spec.temperature is not None:
            payload["temperature"] = spec.temperature
        headers = {"Authorization": f"Bearer {self.settings.deepinfra_api_key}"}

        def call() -> httpx.Response:
            self.limiter.acquire()
            response = self._client.post(
                f"{BASE_URL}/chat/completions", headers=headers, json=payload
            )
            if response.status_code != 200:
                retry_after = response.headers.get("Retry-After")
                raise DeepInfraError(
                    response.status_code,
                    response.text,
                    float(retry_after) if retry_after else None,
                )
            return response

        import time as _time

        started = _time.monotonic()
        response = self.retry.run(call, _retryable)
        latency = int((_time.monotonic() - started) * 1000)
        self.breaker.record_success()

        data = response.json()
        usage_raw = data.get("usage", {}) or {}
        details = usage_raw.get("prompt_tokens_details") or {}
        usage = Usage(
            prompt_tokens=usage_raw.get("prompt_tokens", 0),
            completion_tokens=usage_raw.get("completion_tokens", 0),
            cached_tokens=details.get("cached_tokens") or 0,
            cost_usd=usage_raw.get("estimated_cost"),
        )
        text = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
        result = LLMResponse(
            text=text,
            model=data.get("model", chosen),
            provider=self.provider,
            usage=usage,
            latency_ms=latency,
            raw={"id": data.get("id")},
        )
        if self.ledger is not None:
            self.ledger.record(
                provider=self.provider,
                model=result.model,
                role=role or None,
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                cached_tokens=result.cache_hit_tokens,
                cost_usd=usage.cost_usd,
                latency_ms=latency,
            )
        return result
