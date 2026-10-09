import json
from pathlib import Path

import numpy as np

from app.cache import SemanticCache
from app.guardrails import decide
from app.ingest import chunk_text, load_documents, load_fixes
from app.retriever import rrf_fuse, tokenize
from app.tools import dedupe_logs, normalize_log_line

DATA = Path(__file__).resolve().parent.parent / "data"
FIXES = load_fixes(DATA)


def test_chunking_respects_size_and_overlaps():
    text = "\n\n".join(f"paragraph {i} " + "x" * 200 for i in range(6))
    chunks = chunk_text(text, max_chars=500, overlap_blocks=1)
    assert len(chunks) > 1
    # last paragraph of a chunk is repeated at the start of the next one
    assert chunks[0].split("\n\n")[-1] in chunks[1]


def test_documents_load_with_metadata():
    docs = load_documents(DATA)
    kinds = {d.metadata["kind"] for d in docs}
    assert kinds == {"runbook", "incident"}
    assert all(d.metadata["source"].startswith(("runbooks/", "incidents/")) for d in docs)


def test_every_fix_points_at_an_existing_runbook():
    for fix in FIXES.values():
        for src in fix["supported_by"]:
            assert (DATA / src).exists(), src


def test_every_eval_question_references_valid_data():
    questions = json.loads((Path(__file__).resolve().parent.parent / "eval" / "questions.json").read_text())
    for q in questions:
        if q["type"] == "answerable":
            assert (DATA / q["expected_doc"]).exists()
            assert q["expected_fix"] in FIXES


def test_rrf_prefers_items_ranked_high_in_both_lists():
    fused = rrf_fuse([[1, 2, 3], [3, 1, 4]])
    assert fused[0] == 1
    assert set(fused) == {1, 2, 3, 4}


def test_tokenize():
    assert tokenize("OOMKilled, exit-code 137!") == ["oomkilled", "exit", "code", "137"]


def test_log_normalisation_and_dedup():
    a = "2026-10-01T10:00:01Z ERROR db timeout after 30s host 10.0.0.5"
    b = "2026-10-01T10:00:09Z ERROR db timeout after 31s host 10.0.0.9"
    assert normalize_log_line(a) == normalize_log_line(b)
    groups = dedupe_logs("\n".join([a, b, "INFO started"]))
    assert groups[0]["count"] == 2 and len(groups) == 2


def test_semantic_cache_hit_and_miss():
    vectors = {"a": [1.0, 0.0], "a2": [0.99, 0.05], "b": [0.0, 1.0]}
    cache = SemanticCache(lambda q: vectors[q], threshold=0.95)
    cache.put("a", {"answer": 1})
    assert cache.get("a2") == {"answer": 1}
    assert cache.get("b") is None


def test_guardrail_allows_a_grounded_confident_fix():
    d = decide("FIX-003", 0.9, FIXES, {"runbooks/aks-pod-high-cpu.md"}, 0.6)
    assert d.status == "pending_approval" and d.fix_id == "FIX-003"


def test_guardrail_blocks_unknown_fix_id():
    d = decide("FIX-999", 0.99, FIXES, {"runbooks/aks-pod-high-cpu.md"}, 0.6)
    assert d.status == "escalated" and d.fix_id is None and d.reason == "not_in_allow_list"


def test_guardrail_blocks_fix_not_supported_by_retrieved_docs():
    d = decide("FIX-003", 0.99, FIXES, {"runbooks/vm-disk-full.md"}, 0.6)
    assert d.status == "escalated" and d.reason == "not_grounded_in_retrieved_runbooks"


def test_guardrail_escalates_low_confidence():
    d = decide("FIX-003", 0.3, FIXES, {"runbooks/aks-pod-high-cpu.md"}, 0.6)
    assert d.status == "escalated" and d.reason == "low_confidence"


def test_guardrail_refuses_when_no_fix_selected():
    assert decide(None, 0.9, FIXES, set(), 0.6).status == "refused"
