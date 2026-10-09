"""Hybrid retrieval: vector search (LangChain in-memory vector store) + BM25 keyword search, fused with Reciprocal Rank Fusion."""
import re
from collections import defaultdict

from langchain_core.documents import Document


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def rrf_fuse(rank_lists: list[list[int]], k: int = 60) -> list[int]:
    """Reciprocal Rank Fusion over several ranked lists of document indices."""
    scores: dict[int, float] = defaultdict(float)
    for ranks in rank_lists:
        for pos, idx in enumerate(ranks):
            scores[idx] += 1.0 / (k + pos + 1)
    return [idx for idx, _ in sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))]


class HybridRetriever:
    def __init__(self, docs: list[Document], embeddings, mode: str = "hybrid"):
        from langchain_core.vectorstores import InMemoryVectorStore
        from rank_bm25 import BM25Okapi

        self.docs = docs
        self.mode = mode
        self._index = {(d.metadata["source"], d.metadata["chunk"]): i for i, d in enumerate(docs)}
        self.bm25 = BM25Okapi([tokenize(d.page_content) for d in docs])
        self.store = InMemoryVectorStore.from_documents(docs, embeddings)

    def _vector_ranks(self, query: str, n: int) -> list[int]:
        results = self.store.similarity_search(query, k=n)
        return [self._index[(d.metadata["source"], d.metadata["chunk"])] for d in results]

    def _bm25_ranks(self, query: str, n: int) -> list[int]:
        scores = self.bm25.get_scores(tokenize(query))
        order = sorted(range(len(scores)), key=lambda i: -scores[i])
        return [i for i in order[:n] if scores[i] > 0]

    def search(
        self,
        query: str,
        k: int = 3,
        kind: str | None = None,
        mode: str | None = None,
        unique_sources: bool = False,
    ) -> list[Document]:
        mode = mode or self.mode
        n = max(k * 4, 12)
        if mode == "vector":
            ranked = self._vector_ranks(query, n)
        elif mode == "bm25":
            ranked = self._bm25_ranks(query, n)
        else:
            ranked = rrf_fuse([self._vector_ranks(query, n), self._bm25_ranks(query, n)])

        out: list[Document] = []
        seen: set[str] = set()
        for i in ranked:
            doc = self.docs[i]
            if kind and doc.metadata["kind"] != kind:
                continue
            if unique_sources and doc.metadata["source"] in seen:
                continue
            seen.add(doc.metadata["source"])
            out.append(doc)
            if len(out) == k:
                break
        return out
