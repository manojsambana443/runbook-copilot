"""Prometheus metrics exposed at /metrics."""
from prometheus_client import Counter, Histogram

REQUESTS = Counter("copilot_requests_total", "Questions handled", ["status"])
LATENCY = Histogram(
    "copilot_request_latency_seconds",
    "End-to-end latency of /ask",
    buckets=(0.1, 0.5, 1, 2, 3, 5, 8, 13, 21),
)
TOKENS = Counter("copilot_llm_tokens_total", "LLM tokens used", ["type"])
CACHE_HITS = Counter("copilot_cache_hits_total", "Answers served from the semantic cache")
GUARDRAIL_BLOCKS = Counter("copilot_guardrail_blocks_total", "Proposals blocked by a guardrail", ["reason"])
