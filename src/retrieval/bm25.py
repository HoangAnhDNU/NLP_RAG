"""BM25 truy hồi trên corpus cố định, tái lập được.

Tự cài đặt BM25 (không phụ thuộc rank_bm25) để chạy được trong môi trường NLP.
Tokenize dùng `src/preprocess/normalize.py` (NFC, giữ dấu tiếng Việt).
"""

from __future__ import annotations

import math
from collections import Counter


class BM25Retriever:
    """BM25 cơ bản với k1, b cố định."""

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.docs: list[list[str]] = []
        self.doc_len: list[int] = []
        self.avgdl = 0.0
        self.df: Counter = Counter()
        self.idf: dict[str, float] = {}
        self.n_docs = 0

    def fit(self, docs: list[list[str]]) -> "BM25Retriever":
        self.docs = docs
        self.n_docs = len(docs)
        self.doc_len = [len(d) for d in docs]
        self.avgdl = sum(self.doc_len) / self.n_docs if self.n_docs else 0.0
        self.df = Counter()
        for d in docs:
            for t in set(d):
                self.df[t] += 1
        self.idf = {}
        for t, df in self.df.items():
            self.idf[t] = math.log((self.n_docs - df + 0.5) / (df + 0.5) + 1.0)
        return self

    def score(self, query: list[str]) -> list[float]:
        scores = [0.0] * self.n_docs
        qtf = Counter(query)
        for i, doc in enumerate(self.docs):
            if not doc:
                continue
            tf = Counter(doc)
            dl = self.doc_len[i]
            norm = 1.0 - self.b + self.b * dl / self.avgdl if self.avgdl else 1.0
            s = 0.0
            for t in qtf:
                if t not in self.idf or t not in tf:
                    continue
                f = tf[t]
                s += self.idf[t] * f * (self.k1 + 1.0) / (f + self.k1 * norm)
            scores[i] = s
        return scores

    def top_k(self, query: list[str], k: int) -> list[tuple[int, float]]:
        scores = self.score(query)
        ranked = sorted(range(self.n_docs), key=lambda i: scores[i], reverse=True)
        return [(i, scores[i]) for i in ranked[:k]]
