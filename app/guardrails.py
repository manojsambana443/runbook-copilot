"""Independent safety checks applied to every proposal before it reaches a human.

Check 1 (allow-list):  the fix ID must exist in data/approved_fixes.json.
Check 2 (grounding):   the runbook that supports that fix must have been retrieved in this run,
                       so the model cannot name a fix it never saw evidence for.
Check 3 (confidence):  below the threshold, the case is escalated to a human instead of guessed.
"""
from dataclasses import dataclass

from . import metrics


@dataclass
class Decision:
    status: str  # pending_approval | escalated | refused
    fix_id: str | None
    reason: str | None = None


def check_allow_list(fix_id: str, fixes: dict[str, dict]) -> bool:
    return fix_id in fixes


def check_grounding(fix_id: str, fixes: dict[str, dict], retrieved_sources: set[str]) -> bool:
    return any(src in retrieved_sources for src in fixes[fix_id].get("supported_by", []))


def decide(
    fix_id: str | None,
    confidence: float,
    fixes: dict[str, dict],
    retrieved_sources: set[str],
    min_confidence: float,
) -> Decision:
    if not fix_id:
        return Decision("refused", None, "no_approved_fix_applies")

    if not check_allow_list(fix_id, fixes):
        metrics.GUARDRAIL_BLOCKS.labels("not_in_allow_list").inc()
        return Decision("escalated", None, "not_in_allow_list")

    if not check_grounding(fix_id, fixes, retrieved_sources):
        metrics.GUARDRAIL_BLOCKS.labels("not_grounded").inc()
        return Decision("escalated", None, "not_grounded_in_retrieved_runbooks")

    if confidence < min_confidence:
        metrics.GUARDRAIL_BLOCKS.labels("low_confidence").inc()
        return Decision("escalated", None, "low_confidence")

    return Decision("pending_approval", fix_id, None)
