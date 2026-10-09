"""Tools the agent can call: runbook search, past-incident search, log triage, approved-fix list."""
import re
from collections import OrderedDict
from dataclasses import dataclass, field

from langchain_core.tools import tool

_PATTERNS = [
    (re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?Z?"), "<TS>"),
    (re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I), "<UUID>"),
    (re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b"), "<IP>"),
    (re.compile(r"\b0x[0-9a-f]+\b", re.I), "<HEX>"),
    (re.compile(r"(?<![A-Za-z])\d+"), "<N>"),
]


def normalize_log_line(line: str) -> str:
    """Replace timestamps, ids, IPs and numbers so repeated messages collapse into one pattern."""
    for pattern, token in _PATTERNS:
        line = pattern.sub(token, line)
    return re.sub(r"\s+", " ", line).strip()


def dedupe_logs(text: str, max_patterns: int = 15) -> list[dict]:
    """Group repeated log lines by pattern. One entry per unique pattern, with a count."""
    groups: "OrderedDict[str, dict]" = OrderedDict()
    for raw in text.splitlines():
        if not raw.strip():
            continue
        key = normalize_log_line(raw)
        if key in groups:
            groups[key]["count"] += 1
        else:
            groups[key] = {"pattern": key, "count": 1, "example": raw.strip()}
    return sorted(groups.values(), key=lambda g: -g["count"])[:max_patterns]


@dataclass
class RunContext:
    """Collects which sources the agent actually retrieved during one run (used by the grounding guardrail)."""

    sources: set[str] = field(default_factory=set)


def _format_docs(docs, ctx: RunContext) -> str:
    if not docs:
        return "No matching documents found."
    parts = []
    for d in docs:
        ctx.sources.add(d.metadata["source"])
        parts.append(f"[{d.metadata['source']}#{d.metadata['chunk']}]\n{d.page_content}")
    return "\n\n".join(parts)


def make_tools(retriever, fixes: dict[str, dict], ctx: RunContext, top_k: int = 3):
    @tool
    def search_runbooks(query: str) -> str:
        """Search the runbook knowledge base for troubleshooting steps. Input: a short description of the symptom."""
        return _format_docs(retriever.search(query, k=top_k, kind="runbook"), ctx)

    @tool
    def search_past_incidents(query: str) -> str:
        """Search past incident write-ups for similar problems and what resolved them."""
        return _format_docs(retriever.search(query, k=top_k, kind="incident"), ctx)

    @tool
    def triage_logs(logs: str) -> str:
        """Deduplicate raw log lines into unique patterns with counts, so noisy logs are easy to read."""
        groups = dedupe_logs(logs)
        if not groups:
            return "No log lines provided."
        return "\n".join(f"x{g['count']}  {g['pattern']}  (e.g. {g['example'][:160]})" for g in groups)

    @tool
    def list_approved_fixes() -> str:
        """List the approved fixes. Only these fix IDs may ever be proposed."""
        return "\n".join(f"{f['id']}: {f['title']} - {f['description']}" for f in fixes.values())

    return [search_runbooks, search_past_incidents, triage_logs, list_approved_fixes]
