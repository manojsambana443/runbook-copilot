"""Orchestration: cache -> agent -> guardrails -> human-approval queue, with metrics."""
import time
import uuid
from typing import Optional

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from . import metrics
from .agent import run_agent
from .cache import SemanticCache
from .config import Settings
from .guardrails import decide
from .ingest import load_documents, load_fixes
from .retriever import HybridRetriever


class CopilotService:
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings()
        self.proposals: dict[str, dict] = {}
        self._build()

    def _build(self) -> None:
        s = self.settings
        key = s.openai_api_key or None
        self.embeddings = OpenAIEmbeddings(model=s.embedding_model, api_key=key)
        self.llm = ChatOpenAI(model=s.chat_model, temperature=0, api_key=key)
        self.docs = load_documents(s.data_dir, s.chunk_max_chars)
        self.fixes = load_fixes(s.data_dir)
        self.retriever = HybridRetriever(self.docs, self.embeddings, s.retrieval_mode)
        self.cache = (
            SemanticCache(self.embeddings.embed_query, s.cache_threshold) if s.cache_enabled else None
        )

    def reload(self) -> dict:
        """Re-read runbooks and rebuild the index (used by POST /ingest)."""
        self._build()
        return {"chunks": len(self.docs), "fixes": len(self.fixes)}

    def ask(self, question: str, logs: Optional[str] = None) -> dict:
        s = self.settings
        start = time.perf_counter()
        use_cache = self.cache is not None and not logs

        if use_cache:
            hit = self.cache.get(question)
            if hit:
                metrics.CACHE_HITS.inc()
                result = {**hit, "id": uuid.uuid4().hex[:12], "cached": True, "latency_s": 0.0}
                result["usage"] = {"input_tokens": 0, "output_tokens": 0, "est_cost_usd": 0.0}
                return self._finish(result, start)

        agent = run_agent(
            self.llm, self.retriever, self.fixes, question, logs, s.top_k, s.max_agent_steps
        )
        p = agent.proposal
        if p is None:  # the model failed to produce a valid structured answer
            decision_status, decision_fix, reason = "escalated", None, "invalid_model_output"
            answer, confidence, citations = "Could not produce a reliable answer. Escalating to an engineer.", 0.0, []
        else:
            d = decide(p.fix_id, p.confidence, self.fixes, agent.sources, s.min_confidence)
            decision_status, decision_fix, reason = d.status, d.fix_id, d.reason
            answer, confidence, citations = p.answer, p.confidence, p.citations

        fix = self.fixes.get(decision_fix) if decision_fix else None
        cost = s.estimate_cost(agent.input_tokens, agent.output_tokens)
        metrics.TOKENS.labels("input").inc(agent.input_tokens)
        metrics.TOKENS.labels("output").inc(agent.output_tokens)

        result = {
            "id": uuid.uuid4().hex[:12],
            "status": decision_status,
            "reason": reason,
            "answer": answer,
            "fix_id": decision_fix,
            "fix": {"title": fix["title"], "description": fix["description"]} if fix else None,
            "confidence": round(float(confidence), 2),
            "citations": citations,
            "retrieved_sources": sorted(agent.sources),
            "cached": False,
            "usage": {
                "input_tokens": agent.input_tokens,
                "output_tokens": agent.output_tokens,
                "est_cost_usd": round(cost, 6),
            },
        }
        if use_cache and decision_status != "escalated":
            self.cache.put(question, result)
        return self._finish(result, start)

    def _finish(self, result: dict, start: float) -> dict:
        latency = time.perf_counter() - start
        result["latency_s"] = round(latency, 3)
        metrics.LATENCY.observe(latency)
        metrics.REQUESTS.labels(result["status"]).inc()
        self.proposals[result["id"]] = dict(result)
        return result

    def approve(self, proposal_id: str) -> Optional[dict]:
        """Record a human approval. This service never executes fixes itself."""
        item = self.proposals.get(proposal_id)
        if item is None:
            return None
        if item["status"] != "pending_approval":
            return {"id": proposal_id, "error": f"cannot approve a proposal with status '{item['status']}'"}
        item["status"] = "approved"
        item["approved_at"] = time.time()
        return {"id": proposal_id, "status": "approved", "fix_id": item["fix_id"]}
