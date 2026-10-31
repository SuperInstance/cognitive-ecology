"""TypeSafe (Jev) decision client — calibrated typed answers, not text.

The experimental piece (Law 4's sharpest edge): instead of asking a
language model "what do you think?", we ask a *decision model* typed
questions about a state and get calibrated probabilities:

- ``noul``   — P(yes): "is this proposal actually addressing the tension?"
- ``choice`` — pick one of N named options with confidence + full
  probabilities (used to rank panel proposals between rounds)
- ``score``  — rate against an ordered rubric (used for confidence gates)

Request/response shapes follow the OpenAPI spec at
https://api.typesafe.ai/openapi.json (v0.2.0, fetched 2026-10-31).
Pricing: input-only ($42/Btok), output tokens free — decisions are cheap
enough to sprinkle through every round.
"""

from __future__ import annotations

import time

import httpx

from ..config import Settings
from .base import DecisionAnswer, DecisionRequest, DecisionResponse, Usage
from .ledger import Ledger
from .resilience import CircuitBreaker, RetryPolicy, TokenBucket

BASE_URL = "https://api.typesafe.ai"


class TypeSafeError(RuntimeError):
    def __init__(self, status: int, body: str, retry_after: float | None = None):
        super().__init__(f"typesafe {status}: {body[:200]}")
        self.status = status
        self.retry_after = retry_after


def _retryable(exc: Exception) -> bool:
    status = getattr(exc, "status", None)
    if status is None:
        return isinstance(exc, (httpx.TransportError, httpx.TimeoutException))
    return status in (408, 409, 429, 500, 502, 503, 504, 529)  # 529 = overloaded (documented)


class TypeSafeClient:
    provider = "typesafe"

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
        self._client = client or httpx.Client(timeout=60)
        self.retry = retry or RetryPolicy()
        self.limiter = limiter or TokenBucket(rate=4.0, capacity=10.0)
        self.breaker = breaker or CircuitBreaker()

    @property
    def default_model(self) -> str:
        return self.settings.typesafe_model

    def decide(
        self, request: DecisionRequest, model: str | None = None, *, role: str = "decide"
    ) -> DecisionResponse:
        chosen = model or request.model or self.settings.typesafe_model
        if not self.settings.typesafe_api_key:
            raise RuntimeError("TYPESAFE_API_KEY not set")
        if not self.breaker.allow():
            raise RuntimeError("circuit open for typesafe (recent failures)")

        payload = {
            "model": chosen,
            "state": request.state,
            "questions": request.questions,
        }
        headers = {
            "Authorization": f"Bearer {self.settings.typesafe_api_key}",
            "content-type": "application/json",
        }

        def call() -> httpx.Response:
            self.limiter.acquire()
            response = self._client.post(f"{BASE_URL}/v1/systemone", headers=headers, json=payload)
            if response.status_code != 200:
                retry_after = response.headers.get("Retry-After")
                raise TypeSafeError(
                    response.status_code,
                    response.text,
                    float(retry_after) if retry_after else None,
                )
            return response

        started = time.monotonic()
        response = self.retry.run(call, _retryable)
        latency = int((time.monotonic() - started) * 1000)
        self.breaker.record_success()

        data = response.json()
        answers: dict[str, DecisionAnswer] = {}
        for name, raw in (data.get("answers") or {}).items():
            answer_type = raw.get("type", "")
            if answer_type == "noul":
                value = raw.get("noul")
            elif answer_type == "choice":
                value = (raw.get("choice"), raw.get("confidence"), raw.get("probabilities"))
            elif answer_type == "score":
                value = (raw.get("score"), raw.get("confidence"))
            else:
                value = raw
            answers[name] = DecisionAnswer(name=name, type=answer_type, value=value)

        usage_raw = data.get("usage", {}) or {}
        usage = Usage(
            prompt_tokens=usage_raw.get("input_tokens", 0),
            completion_tokens=usage_raw.get("output_tokens", 0),
        )
        result = DecisionResponse(
            answers=answers,
            model=data.get("model", chosen),
            provider=self.provider,
            usage=usage,
            latency_ms=latency,
        )
        if self.ledger is not None:
            self.ledger.record(
                provider=self.provider,
                model=result.model,
                role=role,
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                cached_tokens=0,
                cost_usd=None,
                latency_ms=latency,
            )
        return result

    # ---- convenience: typed question builders (the shapes the spec pins) ----

    @staticmethod
    def noul(name: str, instructions: str, criteria: dict | None = None) -> tuple[str, dict]:
        question: dict = {"type": "noul", "instructions": instructions}
        if criteria:
            question["criteria"] = criteria
        return name, question

    @staticmethod
    def choice(name: str, instructions: str, options: dict[str, str]) -> tuple[str, dict]:
        """``options`` maps choice name -> when-it-applies description."""
        return name, {"type": "choice", "instructions": instructions, "criteria": options}

    @staticmethod
    def score(name: str, instructions: str, rubric: list[str]) -> tuple[str, dict]:
        """Ordered rubric; each description's position is its score level."""
        return name, {"type": "score", "instructions": instructions, "criteria": rubric}
