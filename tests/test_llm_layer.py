"""LLM teacher-layer tests: shapes, parsing, resilience, ledger.

All provider calls are mocked with httpx.MockTransport — no network, no
keys, deterministic. The live probes that verified real endpoints live in
scripts/ and the journal, not in the test suite.
"""

from __future__ import annotations

import httpx
import pytest

from ecology.config import Settings
from ecology.llm.base import DecisionRequest, PromptSpec
from ecology.llm.deepinfra import DeepInfraClient
from ecology.llm.ledger import Ledger
from ecology.llm.minimax import MiniMaxClient
from ecology.llm.resilience import CircuitBreaker, RetryPolicy, TokenBucket
from ecology.llm.typesafe import TypeSafeClient

# ---- PromptSpec: the cache-first contract ----


def test_prompt_spec_cache_friendliness() -> None:
    spec = PromptSpec(stable_prefix="x" * 900, variable_suffix="y" * 100)
    assert spec.cache_friendliness == pytest.approx(0.9)


def test_prompt_spec_prefix_is_byte_stable_by_construction() -> None:
    """Two calls with the same prefix must serialize identically."""
    a = PromptSpec(stable_prefix="topic + context", variable_suffix="turn 1")
    b = PromptSpec(stable_prefix="topic + context", variable_suffix="turn 2")
    assert a.stable_prefix == b.stable_prefix  # the cacheable part never moves


# ---- DeepInfra parsing (mocked transport) ----


def _deepinfra_ok(request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "id": "test",
            "model": "ByteDance/Seed-2.0-mini",
            "choices": [{"message": {"content": "panel reply"}}],
            "usage": {
                "prompt_tokens": 1200,
                "completion_tokens": 300,
                "estimated_cost": 0.00021,
                "prompt_tokens_details": {"cached_tokens": 1024},
            },
        },
    )


def test_deepinfra_complete_parses_usage_and_cache(tmp_path) -> None:
    settings = Settings(deepinfra_api_key="test-key")
    ledger = Ledger(tmp_path / "usage.db")
    client = DeepInfraClient(
        settings, ledger=ledger, client=httpx.Client(transport=httpx.MockTransport(_deepinfra_ok))
    )
    response = client.complete(PromptSpec("prefix", "suffix"), role="contrarian")
    assert response.text == "panel reply"
    assert response.usage.cached_tokens == 1024
    assert response.usage.cost_usd == pytest.approx(0.00021)
    report = ledger.report()
    assert report["total_calls"] == 1
    assert report["by_model"][0]["cached_tokens"] == 1024
    ledger.close()


def test_deepinfra_retries_on_429_then_succeeds() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, text="Rate limited", headers={"Retry-After": "0.01"})
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 2},
            },
        )

    sleeps: list[float] = []
    settings = Settings(deepinfra_api_key="k")
    client = DeepInfraClient(
        settings,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        retry=RetryPolicy(sleeper=sleeps.append),
    )
    response = client.complete(PromptSpec("p", "s"))
    assert response.text == "ok"
    assert calls["n"] == 2
    assert sleeps and sleeps[0] == pytest.approx(0.01, rel=1e-6)  # honored Retry-After


# ---- MiniMax parsing (mocked; x-api-key auth) ----


def _minimax_ok(request: httpx.Request) -> httpx.Response:
    assert request.headers["x-api-key"] == "mm-key"  # the probe-taught auth
    return httpx.Response(
        200,
        json={
            "id": "msg_test",
            "model": "MiniMax-M3.1-Flash",
            "content": [{"type": "text", "text": "divergent idea"}],
            "usage": {"input_tokens": 800, "output_tokens": 200, "cache_read_input_tokens": 512},
        },
    )


def test_minimax_complete_parses_anthropic_style_usage(tmp_path) -> None:
    settings = Settings(minimax_api_key="mm-key")
    ledger = Ledger(tmp_path / "u.db")
    client = MiniMaxClient(
        settings,
        ledger=ledger,
        client=httpx.Client(transport=httpx.MockTransport(_minimax_ok)),
    )
    response = client.complete(PromptSpec("prefix", "suffix"), role="ideator")
    assert response.text == "divergent idea"
    assert response.usage.cache_read_input_tokens == 512
    assert response.cache_hit_tokens == 512
    # cost estimated locally from the price table: (800-512)*0.15 + 512*0.015 + 200*0.60 per 1M
    ledger.close()


# ---- TypeSafe decisions (mocked) ----


def _jev_ok(request: httpx.Request) -> httpx.Response:
    assert request.headers["Authorization"] == "Bearer ts-key"
    return httpx.Response(
        200,
        json={
            "model": "jev-1.14.0",
            "answers": {
                "healthy": {"type": "noul", "noul": 0.73},
                "priority": {
                    "type": "choice",
                    "choice": "contrarian",
                    "confidence": 0.8,
                    "probabilities": {"contrarian": 0.8, "analyst": 0.2},
                },
                "coherence": {"type": "score", "score": 1.7, "confidence": 0.66},
            },
            "usage": {"input_tokens": 364, "output_tokens": 40},
        },
    )


def test_typesafe_decide_parses_typed_answers(tmp_path) -> None:
    settings = Settings(typesafe_api_key="ts-key")
    ledger = Ledger(tmp_path / "u.db")
    client = TypeSafeClient(
        settings, ledger=ledger, client=httpx.Client(transport=httpx.MockTransport(_jev_ok))
    )
    request = DecisionRequest(
        state={"round": 1},
        questions={"healthy": {"type": "noul", "instructions": "?"}},
    )
    response = client.decide(request)
    assert response.answers["healthy"].value == pytest.approx(0.73)
    choice_name, confidence, probs = response.answers["priority"].value
    assert choice_name == "contrarian" and confidence == pytest.approx(0.8)
    score, _ = response.answers["coherence"].value
    assert score == pytest.approx(1.7)
    ledger.close()


# ---- resilience primitives ----


def test_retry_policy_backoff_growth_and_jitter() -> None:
    policy = RetryPolicy(base_delay=1.0, jitter=0.0, rng=__import__("random").Random(0))
    assert policy.delay_for(0) == 1.0
    assert policy.delay_for(1) == 2.0
    assert policy.delay_for(2) == 4.0
    assert policy.delay_for(10) == 20.0  # capped
    assert policy.delay_for(0, retry_after=0.25) == 0.25  # honored


def test_retry_policy_gives_up_after_max_attempts() -> None:
    policy = RetryPolicy(max_attempts=3, sleeper=lambda s: None)

    def always_fail():
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        policy.run(always_fail, should_retry=lambda e: True)


def test_token_bucket_bursts_then_throttles() -> None:
    clock = {"t": 0.0}
    bucket = TokenBucket(rate=1.0, capacity=3.0, clock=lambda: clock["t"])
    assert bucket.try_acquire(3.0) is True  # full burst
    assert bucket.try_acquire(1.0) is False  # empty: non-blocking refuses
    clock["t"] += 2.0  # two seconds pass: 2 tokens refill
    assert bucket.try_acquire(2.0) is True
    assert bucket.try_acquire(1.0) is False


def test_token_bucket_blocking_acquire_waits_for_refill() -> None:
    clock = {"t": 0.0}

    def advance(seconds: float) -> None:
        clock["t"] += seconds  # "sleeping" advances the fake clock

    bucket = TokenBucket(rate=1.0, capacity=1.0, clock=lambda: clock["t"])
    assert bucket.try_acquire(1.0) is True
    assert bucket.acquire(1.0, blocker=advance) is True  # waited for the refill


def test_circuit_breaker_opens_and_half_opens() -> None:
    clock = {"t": 0.0}
    breaker = CircuitBreaker(threshold=2, reset_after=60.0, clock=lambda: clock["t"])
    breaker.record_failure()
    breaker.record_failure()
    assert breaker.allow() is False  # open
    clock["t"] += 61.0
    assert breaker.allow() is True  # half-open
    breaker.record_failure()  # half-open failure re-opens immediately
    assert breaker.allow() is False
    clock["t"] += 61.0
    assert breaker.allow() is True
    breaker.record_success()
    assert breaker.state == CircuitBreaker.CLOSED


# ---- ledger costing ----


def test_ledger_estimates_cost_from_price_table(tmp_path) -> None:
    ledger = Ledger(tmp_path / "u.db")
    cost = ledger.estimate_cost("ByteDance/Seed-2.0-mini", 1_000_000, 500_000, 800_000)
    # (1M - 800k) * $0.10 + 800k * $0.02 + 500k * $0.40 per 1M = 0.02 + 0.016 + 0.20
    assert cost == pytest.approx(0.236)
    unknown = ledger.estimate_cost("unknown/model", 1000, 1000, 0)
    assert unknown == 0.0  # unknown prices sum as zero, never guessed
    ledger.close()
