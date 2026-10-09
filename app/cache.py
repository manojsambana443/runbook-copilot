"""Semantic cache: reuse an earlier answer when a new question is nearly identical in meaning."""
from typing import Any, Callable

import numpy as np


class SemanticCache:
    def __init__(self, embed_fn: Callable[[str], list[float]], threshold: float = 0.92, max_items: int = 256):
        self.embed_fn = embed_fn
        self.threshold = threshold
        self.max_items = max_items
        self._vecs: list[np.ndarray] = []
        self._values: list[Any] = []

    @staticmethod
    def _unit(vec) -> np.ndarray:
        arr = np.asarray(vec, dtype=float)
        norm = np.linalg.norm(arr)
        return arr / norm if norm else arr

    def get(self, query: str) -> Any | None:
        if not self._vecs:
            return None
        q = self._unit(self.embed_fn(query))
        sims = np.array([float(v @ q) for v in self._vecs])
        best = int(sims.argmax())
        return self._values[best] if sims[best] >= self.threshold else None

    def put(self, query: str, value: Any) -> None:
        if len(self._vecs) >= self.max_items:
            self._vecs.pop(0)
            self._values.pop(0)
        self._vecs.append(self._unit(self.embed_fn(query)))
        self._values.append(value)

    def __len__(self) -> int:
        return len(self._vecs)
