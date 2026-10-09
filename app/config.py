"""Central configuration, read from environment variables."""
import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _env(name: str, default: str) -> str:
    return os.getenv(name, default)


def _bool(name: str, default: bool) -> bool:
    return _env(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    openai_api_key: str = field(default_factory=lambda: _env("OPENAI_API_KEY", ""))
    chat_model: str = field(default_factory=lambda: _env("CHAT_MODEL", "gpt-4o-mini"))
    embedding_model: str = field(
        default_factory=lambda: _env("EMBEDDING_MODEL", "text-embedding-3-small")
    )
    data_dir: Path = field(default_factory=lambda: Path(_env("DATA_DIR", str(ROOT / "data"))))

    # Retrieval: "vector" | "bm25" | "hybrid"
    retrieval_mode: str = field(default_factory=lambda: _env("RETRIEVAL_MODE", "hybrid"))
    top_k: int = field(default_factory=lambda: int(_env("TOP_K", "3")))
    chunk_max_chars: int = field(default_factory=lambda: int(_env("CHUNK_MAX_CHARS", "700")))

    # Guardrails
    min_confidence: float = field(default_factory=lambda: float(_env("MIN_CONFIDENCE", "0.6")))
    max_agent_steps: int = field(default_factory=lambda: int(_env("MAX_AGENT_STEPS", "4")))

    # Semantic cache
    cache_enabled: bool = field(default_factory=lambda: _bool("CACHE_ENABLED", True))
    cache_threshold: float = field(default_factory=lambda: float(_env("CACHE_THRESHOLD", "0.92")))

    # Prices in USD per 1M tokens. Check the current OpenAI price list and update.
    price_in_per_1m: float = field(default_factory=lambda: float(_env("PRICE_IN_PER_1M", "0.15")))
    price_out_per_1m: float = field(default_factory=lambda: float(_env("PRICE_OUT_PER_1M", "0.60")))

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return (input_tokens * self.price_in_per_1m + output_tokens * self.price_out_per_1m) / 1_000_000
