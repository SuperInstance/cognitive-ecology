"""A portfolio organism where decisions are typed, calibrated, and committed.

Layer tour:
  L6 WHY     assumptions live in the WHY tree ("the 60/40 regime holds")
  L5 market  candidate actions bid for the rebalance slot
  L5 policy  a DECISION MODEL chooses among the candidates, with confidence
  L7 identity every choice becomes a hash-chained commitment

The decision policy is a Protocol: the heuristic one runs keyless; a
typesafe.ai-style endpoint (typed decisions + calibrated confidence)
plugs in via env vars. See docs/08_decision_models.md for the design.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path
from typing import Protocol

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from cognitive_ecology import Identity, Runtime, WhyState  # noqa: E402


# --------------------------------------------------------------------------
# the decision-model seam: anything that returns a calibrated choice
# --------------------------------------------------------------------------
class DecisionPolicy(Protocol):
    """The seam where decision models plug into the ecology."""

    name: str

    def choose(self, options: list, context: str) -> dict:
        """Return {'choice': name, 'confidence': float in [0,1]}."""
        ...


class HeuristicPolicy:
    """Zero-LLM policy: scored by the same factors the market uses."""

    name = "heuristic"

    def choose(self, options, context: str) -> dict:
        scored = sorted(
            options, key=lambda o: -(o["urgency"] * o["expected_value"])
        )
        best = scored[0]
        runner_up = scored[1]["urgency"] * scored[1]["expected_value"] if len(scored) > 1 else 0.0
        top = best["urgency"] * best["expected_value"]
        confidence = top / (top + runner_up + 0.20)  # calibrated-ish score
        return {"choice": best["name"], "confidence": round(min(0.99, confidence), 2)}


class OpenAICompatDecisionPolicy:
    """Typed decisions from any OpenAI-compatible decision endpoint.

    EXPERIMENTAL: endpoint, model and exact request shape are env-driven
    (TYPESAFE_BASE_URL / _API_KEY / _MODEL). Decision-model providers
    differ in schema; this policy sends a strict JSON contract and parses
    {choice, confidence} defensively. Check your provider's current model
    id and schema (e.g. on OpenRouter) before relying on it.
    """

    name = "openai-compat-decisions"

    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    @classmethod
    def from_env(cls) -> "OpenAICompatDecisionPolicy | None":
        key = os.environ.get("TYPESAFE_API_KEY", "")
        if not key:
            return None
        return cls(
            base_url=os.environ.get("TYPESAFE_BASE_URL", "https://openrouter.ai/api/v1"),
            api_key=key,
            model=os.environ.get("TYPESAFE_MODEL", "typesafe/jev-1.0"),
        )

    def choose(self, options, context: str) -> dict:
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": (
                    "You are a decision model. Reply with ONLY a JSON object: "
                    '{"choice": "<one of the option names>", "confidence": <0..1>}'
                )},
                {"role": "user", "content": json.dumps({
                    "options": [{"name": o["name"], "relieves": o["relieves"]}
                                for o in options],
                    "context": context,
                })},
            ],
            "max_tokens": 60,
            "temperature": 0.2,
        }
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(body).encode(),
            headers={"Authorization": f"Bearer {self.api_key}",
                     "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
            text = data["choices"][0]["message"]["content"]
            parsed = json.loads(text[text.find("{"): text.rfind("}") + 1])
            names = [o["name"] for o in options]
            if parsed.get("choice") not in names:
                raise ValueError("choice not among options")
            return {"choice": parsed["choice"],
                    "confidence": float(min(1.0, max(0.0, parsed.get("confidence", 0.5))))}
        except Exception as exc:  # fail-soft: fall back to the heuristic
            print(f"  [decision-model] fell back to heuristic ({exc.__class__.__name__})")
            return HeuristicPolicy().choose(options, context)


# --------------------------------------------------------------------------
# the organism
# --------------------------------------------------------------------------
MARKET_PATH = [0.0, -0.02, -0.05, -0.03, 0.01, 0.03, -0.08, -0.10, -0.06, 0.02,
               0.05, 0.01, -0.01, -0.04, -0.02, 0.02, 0.06, 0.03, 0.0, -0.03]

OPTIONS = [
    {"name": "rebalance", "relieves": ["assumption_rot"], "urgency": 0.0,
     "expected_value": 0.8, "why": "why:regime"},
    {"name": "hedge", "relieves": ["drawdown_anxiety"], "urgency": 0.0,
     "expected_value": 0.6, "why": "why:regime"},
    {"name": "hold", "relieves": [], "urgency": 0.1,
     "expected_value": 0.5, "why": "why:regime"},
]


def main() -> None:
    policy = OpenAICompatDecisionPolicy.from_env() or HeuristicPolicy()
    print(f"[policy] {policy.name}")

    rt = Runtime(seed=9, top_k=1)
    rt.declare_why("preserve capital and stay honest about assumptions",
                   node_id="why:root")
    rt.declare_why("the 60/40 regime holds", parent="why:root", node_id="why:regime")
    rt.tensions.add("assumption_rot", growth=0.02,
                    description="stale premises accumulate")
    rt.tensions.add("drawdown_anxiety", growth=0.0,
                    description="grows when the market bleeds")
    rt.graph.upsert("portfolio:main", "portfolio", {"base": 100.0}, tick=0)
    rt.identity = Identity(name="steward", why=rt.why)

    print(f"\n{'tick':>4} {'market':>7} {'action':>10} {'conf':>5}  why-gate")
    equity = 100.0
    for tick, drift in enumerate(MARKET_PATH, start=1):
        rt.tick_no = tick  # keep the runtime clock in step with the market
        equity *= (1 + drift)
        if drift < 0:
            rt.tensions.burden("drawdown_anxiety", abs(drift) * 4)
        # options bid with live urgencies (this stand-in for the market keeps
        # the example readable; see the kernel's AttentionMarket for the real one)
        for o in OPTIONS:
            o["urgency"] = max([rt.tensions.level(t) for t in o["relieves"]] or [0.1])
        # the WHY gate: if the regime assumption dies, trading on top of it
        # is not "risky", it is UNJUSTIFIABLE — the decision model never
        # even gets to see those options
        eligible = [o for o in OPTIONS if rt.why.justification(o["why"]) > 0]
        gate = "open" if len(eligible) == len(OPTIONS) else "QUESTIONED"
        if not eligible:
            # the law, lived: nothing may act on a dead assumption
            rt.identity.commit(
                f"stood down at equity {equity:.1f}: the regime assumption "
                "is dead, nothing may trade on it", tick=tick)
            print(f"{tick:4d} {drift:+7.2f} {'stand-down':>10} "
                  f"{1.00:5.2f}  {gate}")
            rt.tensions.tick()
            continue
        decision = policy.choose(eligible, f"equity={equity:.1f}, "
                                           f"tensions={rt.tensions.snapshot()}")
        rt.identity.commit(
            f"{decision['choice']} (conf {decision['confidence']}) "
            f"at equity {equity:.1f}", tick=tick)
        for t in OPTIONS_MAP(decision["choice"]):
            rt.tensions.relieve(t, 0.5)
        print(f"{tick:4d} {drift:+7.2f} {decision['choice']:>10} "
              f"{decision['confidence']:5.2f}  {gate}")
        rt.tensions.tick()
        # mid-run crisis: the regime assumption dies (with a record)
        if tick == 10:
            rt.why.kill("why:regime", reason="backtest says the regime broke", tick=tick)

    print("\n[commitments] the decision trail (hash-chained):")
    for c in rt.identity.commitments()[-4:]:
        print(f"  [tick {c.tick:2d}] {c.text}")
    print(f"  chain verifies: {rt.identity.verify()}")
    print("\n[why] assumptions after the run:")
    for n in rt.why.nodes():
        print(f"  [{n.state.value:7s}] {n.statement}")
    print("\n[self-model]")
    print(rt.identity.drift())


def OPTIONS_MAP(choice: str) -> list:
    """Which tensions a chosen action discharges."""
    return {"rebalance": ["assumption_rot"], "hedge": ["drawdown_anxiety"],
            "hold": []}.get(choice, [])


if __name__ == "__main__":
    main()
