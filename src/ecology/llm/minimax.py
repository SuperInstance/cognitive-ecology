"""MiniMax client — the divergent-ideation panelist.

A different lineage from the DeepInfra panel (per the owner's intent:
ideation that is genuinely *not like* the other models). Uses the
Anthropic-compatible endpoint; the probe taught us auth wants the
``x-api-key`` header (not Bearer), and prompt caching is automatic with
hits reported as ``usage.cache_read_input_tokens``.
"""

from __future__ import annotations

import httpx

from ..config import Settings
from .base import LLMResponse, PromptSpec, Usage
from .ledger import Ledger
from .resilience import CircuitBreaker, RetryPolicy, TokenBucket

BASE_URL = "https://api.minimax.io/anthropic"


class MiniMaxError(RuntimeError):
    def __init__(self, status: int, body: str, retry_after: float | None = None):
        super().__init__(f"minimax {status}: {body[:200]}")
        self.status = status
        self.retry_after = retry_after


def _retryable(exc: Exception) -> bool:
    status = getattr(exc, "status", None)
    if status is None:
        return isinstance(exc, (httpx.TransportError, httpx.TimeoutException))
    return status in (408, 409, 429, 500, 502, 503, 504, 529)


class MiniMaxClient:
    provider = "minimax"

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
        self._client = client or httpx.Client(timeout=180)
        self.retry = retry or RetryPolicy()
        self.limiter = limiter or TokenBucket(rate=2.0, capacity=6.0)
        self.breaker = breaker or CircuitBreaker()

    @property
    def default_model(self) -> str:
        return self.settings.minimax_model

    def complete(
        self, spec: PromptSpec, model: str | None = None, *, role: str = ""
    ) -> LLMResponse:
        chosen = model or self.settings.minimax_model
        if not self.settings.minimax_api_key:
            raise RuntimeError("MINIMAX_API_KEY not set")
        if not self.breaker.allow():
            raise RuntimeError("circuit open for minimax (recent failures)")

        payload = {
            "model": chosen,
            "max_tokens": spec.max_tokens,
            "messages": [
                {
                    "role": "user",
                    "content": spec.stable_prefix + "\n\n" + spec.variable_suffix,
                }
            ],
            # thinking is on by default for M3.1-Flash; low effort keeps
            # panel turns snappy without disabling it outright
            # thinking is on by default for M3.1-Flash; low effort keeps
            # panel turns snappy without disabling it outright
            "output_config": {"effort": "low"},  # keep thinking short
        }
        headers = {
            "x-api-key": self.settings.minimax_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        def call() -> httpx.Response:
            self.limiter.acquire()
            response = self._client.post(f"{BASE_URL}/v1/messages", headers=headers, json=payload)
            if response.status_code != 200:
                retry_after = response.headers.get("Retry-After")
                raise MiniMaxError(
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
        usage = Usage(
            prompt_tokens=usage_raw.get("input_tokens", 0),
            completion_tokens=usage_raw.get("output_tokens", 0),
            cache_read_input_tokens=usage_raw.get("cache_read_input_tokens", 0) or 0,
        )
        blocks = data.get("content", [])
        text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
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
                cost_usd=None,  # estimated locally from the price table
                latency_ms=latency,
            )
        return result
