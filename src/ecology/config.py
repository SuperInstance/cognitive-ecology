"""Environment-driven settings.

Keys are read from the environment or a local ``.env`` (gitignored — the
file never ships, the values never print). No dependency on dotenv: the
format we write is the format we parse.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def load_env_file(path: str | Path = ".env") -> dict[str, str]:
    """Parse a .env file into a dict (never prints values)."""
    values: dict[str, str] = {}
    try:
        for line in Path(path).read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip()
    except OSError:
        pass
    return values


def _lookup(name: str, env_file: str | Path | None = None) -> str | None:
    if name in os.environ:
        return os.environ[name]
    for candidate in [env_file] if env_file else [".env", Path(__file__).parents[2] / ".env"]:
        value = load_env_file(candidate).get(name)
        if value:
            return value
    return None


@dataclass
class Settings:
    """Provider settings; every field has a working default model choice."""

    deepinfra_api_key: str | None = None
    deepinfra_model: str = "ByteDance/Seed-2.0-mini"
    minimax_api_key: str | None = None
    minimax_model: str = "MiniMax-M3.1-Flash"
    typesafe_api_key: str | None = None
    typesafe_model: str = "jev-latest"
    ledger_path: str = "data/usage.db"
    #: prices per 1M tokens (in, out, cache-read) as of 2026-10-31;
    #: DeepInfra reports its own estimated_cost per call, which wins when present
    prices: dict[str, tuple[float, float, float]] = field(
        default_factory=lambda: {
            # DeepInfra (from the models API, 2026-10-31)
            "ByteDance/Seed-2.0-mini": (0.10, 0.40, 0.02),
            "ByteDance/Seed-2.0-pro": (0.50, 3.00, 0.10),
            "XiaomiMiMo/MiMo-V2.6-Pro": (0.43, 0.87, 0.0036),
            "nvidia/NVIDIA-Nemotron-3-Ultra-550B-A55B": (0.50, 2.20, 0.10),
            "Qwen/Qwen3.8-Max": (1.65, 4.95, 0.206),
            "inclusionAI/Ling-3.1-flash": (0.075, 0.225, 0.015),
            "tencent/Hy4-preview": (0.834, 2.501, 0.042),
            # MiniMax (from platform.minimax.io pricing, 2026-10-31)
            "MiniMax-M3.1-Flash": (0.15, 0.60, 0.015),
            # TypeSafe: input-only billing ($42/Btok), output free
            "jev-latest": (0.042, 0.0, 0.0),
        }
    )

    @classmethod
    def from_env(cls, env_file: str | Path | None = None) -> Settings:
        return cls(
            deepinfra_api_key=_lookup("DEEPINFRA_API_KEY", env_file),
            deepinfra_model=_lookup("DEEPINFRA_MODEL", env_file) or "ByteDance/Seed-2.0-mini",
            minimax_api_key=_lookup("MINIMAX_API_KEY", env_file),
            minimax_model=_lookup("MINIMAX_MODEL", env_file) or "MiniMax-M3.1-Flash",
            typesafe_api_key=_lookup("TYPESAFE_API_KEY", env_file),
            typesafe_model=_lookup("TYPESAFE_MODEL", env_file) or "jev-latest",
            ledger_path=_lookup("ECOLOGY_LEDGER", env_file) or "data/usage.db",
        )
