"""Offline end-to-end test of the agent loop, guardrails and service wiring using fake models (no API calls)."""
import hashlib
from pathlib import Path

import numpy as np
from langchain_core.embeddings import Embeddings
from langchain_core.messages import AIMessage

from app.agent import Proposal
from app.cache import SemanticCache
from app.config import Settings
from app.ingest import load_documents, load_fixes
from app.retriever import HybridRetriever, tokenize
from app.service import CopilotService

DATA = Path(__file__).resolve().parent.parent / "data"


class BagOfWordsEmbeddings(Embeddings):
    """Deterministic hashed bag-of-words vectors, good enough to test retrieval plumbing."""

    def _vec(self, text: str) -> list[float]:
        v = np.zeros(256)
        for tok in tokenize(text):
            v[int(hashlib.md5(tok.encode()).hexdigest(), 16) % 256] += 1.0
        return (v / (np.linalg.norm(v) or 1.0)).tolist()

    def embed_documents(self, texts):
        return [self._vec(t) for t in texts]

    def embed_query(self, text):
        return self._vec(text)


class ScriptedLLM:
    """Calls search_runbooks once, then finishes with a fixed proposal."""

    def __init__(self, fix_id, confidence=0.9):
        self.fix_id, self.confidence, self.calls = fix_id, confidence, 0

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        self.calls += 1
        if self.calls == 1:
            return AIMessage(
                content="",
                tool_calls=[{"name": "search_runbooks", "args": {"query": "high cpu pods"}, "id": "t1"}],
                usage_metadata={"input_tokens": 100, "output_tokens": 10, "total_tokens": 110},
            )
        return AIMessage(content="done", usage_metadata={"input_tokens": 50, "output_tokens": 5, "total_tokens": 55})

    def with_structured_output(self, schema, **kwargs):
        outer = self

        class _S:
            def invoke(self, messages):
                return {
                    "raw": AIMessage(content="", usage_metadata={"input_tokens": 30, "output_tokens": 20, "total_tokens": 50}),
                    "parsed": Proposal(
                        answer="Scale out.", fix_id=outer.fix_id, confidence=outer.confidence,
                        citations=["runbooks/aks-pod-high-cpu.md"],
                    ),
                }

        return _S()


def make_service(llm) -> CopilotService:
    settings = Settings()
    svc = CopilotService.__new__(CopilotService)
    svc.settings, svc.proposals = settings, {}
    svc.embeddings = BagOfWordsEmbeddings()
    svc.llm = llm
    svc.docs = load_documents(DATA)
    svc.fixes = load_fixes(DATA)
    svc.retriever = HybridRetriever(svc.docs, svc.embeddings, "hybrid")
    svc.cache = SemanticCache(svc.embeddings.embed_query, 0.99)
    return svc


def test_hybrid_retrieval_finds_the_right_runbook_offline():
    svc = make_service(ScriptedLLM("FIX-003"))
    docs = svc.retriever.search("Terraform error acquiring the state lock", k=3, kind="runbook", unique_sources=True)
    assert "runbooks/terraform-state-lock.md" in [d.metadata["source"] for d in docs]


def test_grounded_fix_goes_to_human_approval_then_can_be_approved():
    svc = make_service(ScriptedLLM("FIX-003"))
    res = svc.ask("Pods are at 95% CPU and the HPA is maxed out")
    assert res["status"] == "pending_approval" and res["fix_id"] == "FIX-003"
    assert res["usage"]["input_tokens"] == 180 and res["usage"]["output_tokens"] == 35
    assert svc.approve(res["id"])["status"] == "approved"
    assert "error" in svc.approve(res["id"])  # cannot approve twice


def test_invented_fix_is_never_returned():
    svc = make_service(ScriptedLLM("FIX-999"))
    res = svc.ask("Please wipe the audit logs")
    assert res["status"] == "escalated" and res["fix_id"] is None
    assert "error" in svc.approve(res["id"])


def test_no_fix_means_refused_and_not_cached_as_an_action():
    svc = make_service(ScriptedLLM(None))
    res = svc.ask("What is the best pizza topping?")
    assert res["status"] == "refused" and res["fix_id"] is None


def test_semantic_cache_serves_repeat_question_without_llm_calls():
    llm = ScriptedLLM("FIX-003")
    svc = make_service(llm)
    first = svc.ask("Pods are at 95% CPU and the HPA is maxed out")
    calls_after_first = llm.calls
    second = svc.ask("Pods are at 95% CPU and the HPA is maxed out")
    assert second["cached"] is True and second["usage"]["est_cost_usd"] == 0.0
    assert llm.calls == calls_after_first and second["id"] != first["id"]
