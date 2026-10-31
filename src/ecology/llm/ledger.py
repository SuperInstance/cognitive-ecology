"""The usage ledger: every provider call, its tokens, its cost.

Attention is not the only scarce resource — money is too. Every call is
recorded (provider, model, role, tokens, cached tokens, cost, latency,
status) in SQLite under ``data/usage.db``; ``ecology usage`` prints the
aggregate. DeepInfra reports ``estimated_cost`` per call, which is recorded
when present; otherwise cost is computed from the price table (marked as
estimates, dated, env-overridable).
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from ..config import Settings

_SCHEMA = """
CREATE TABLE IF NOT EXISTS usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    role TEXT,
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    cached_tokens INTEGER NOT NULL DEFAULT 0,
    cost_usd REAL,
    latency_ms INTEGER,
    status TEXT NOT NULL DEFAULT 'ok',
    meta TEXT
);
CREATE INDEX IF NOT EXISTS idx_usage_provider ON usage(provider, model);
"""


class Ledger:
    def __init__(self, path: str | Path = "data/usage.db", settings: Settings | None = None):
        self.path = Path(path)
        self.settings = settings or Settings()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    # ---- recording ----

    def record(
        self,
        *,
        provider: str,
        model: str,
        role: str | None = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        cached_tokens: int = 0,
        cost_usd: float | None = None,
        latency_ms: int | None = None,
        status: str = "ok",
        meta: str | None = None,
    ) -> None:
        if cost_usd is None:
            cost_usd = self.estimate_cost(model, prompt_tokens, completion_tokens, cached_tokens)
        self._conn.execute(
            "INSERT INTO usage (ts, provider, model, role, prompt_tokens, completion_tokens,"
            " cached_tokens, cost_usd, latency_ms, status, meta)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                time.time(),
                provider,
                model,
                role,
                prompt_tokens,
                completion_tokens,
                cached_tokens,
                cost_usd,
                latency_ms,
                status,
                meta,
            ),
        )
        self._conn.commit()

    # ---- costing ----

    def estimate_cost(
        self, model: str, prompt_tokens: int, completion_tokens: int, cached_tokens: int
    ) -> float:
        """Cost from the price table ($/1M tokens); 0 for unknown models
        (never a guess presented as a number — unknowns sum as zero and the
        report says which models had no price)."""
        price_in, price_out, price_cache = self.settings.prices.get(model, (0.0, 0.0, 0.0))
        billable_input = max(0, prompt_tokens - cached_tokens)
        return (
            billable_input * price_in / 1_000_000
            + cached_tokens * price_cache / 1_000_000
            + completion_tokens * price_out / 1_000_000
        )

    # ---- reporting ----

    def report(self) -> dict:
        rows = self._conn.execute(
            "SELECT provider, model, COUNT(*), SUM(prompt_tokens), SUM(completion_tokens),"
            " SUM(cached_tokens), SUM(cost_usd), AVG(latency_ms)"
            " FROM usage WHERE status='ok' GROUP BY provider, model ORDER BY SUM(cost_usd) DESC"
        ).fetchall()
        return {
            "total_cost_usd": sum(r[6] or 0 for r in rows),
            "total_calls": sum(r[2] for r in rows),
            "by_model": [
                {
                    "provider": r[0],
                    "model": r[1],
                    "calls": r[2],
                    "prompt_tokens": r[3] or 0,
                    "completion_tokens": r[4] or 0,
                    "cached_tokens": r[5] or 0,
                    "cost_usd": round(r[6] or 0, 6),
                    "avg_latency_ms": round(r[7] or 0),
                }
                for r in rows
            ],
        }

    def close(self) -> None:
        self._conn.close()


def usage_cli(ledger_path: str = "data/usage.db") -> int:
    ledger = Ledger(ledger_path)
    report = ledger.report()
    ledger.close()
    print(f"total: {report['total_calls']} calls, ${report['total_cost_usd']:.4f}")
    for row in report["by_model"]:
        cache_pct = (
            100 * row["cached_tokens"] / row["prompt_tokens"] if row["prompt_tokens"] else 0
        )
        print(
            f"  {row['provider']:>10} {row['model']:<42} calls={row['calls']:>3}"
            f" in={row['prompt_tokens']:>7} out={row['completion_tokens']:>6}"
            f" cached={row['cached_tokens']:>7} ({cache_pct:.0f}%)"
            f" ${row['cost_usd']:.4f} avg={row['avg_latency_ms']}ms"
        )
    return 0
