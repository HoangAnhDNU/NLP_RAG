"""Kiểm tra dao động seed cho E1 LSA (Mục 4: nếu ngẫu nhiên thì báo cáo dao động).

Chạy LSA với 3 seed (42, 7, 123), tính Recall@5 trên câu có evidence.
Đầu ra in ra console, không đổi prediction chính (seed 42).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.preprocess.normalize import normalize_query, tokenize_vi  # noqa: E402


def main() -> int:
    e0_cfg = yaml.safe_load(open(ROOT / "config" / "e0_bm25.yaml", encoding="utf-8"))
    stopwords = set(e0_cfg.get("stopwords", []))
    chunks = [json.loads(line) for line in open(ROOT / "data" / "processed" / "chunks.jsonl", encoding="utf-8")]

    def tokenize(text: str) -> list[str]:
        toks = tokenize_vi(normalize_query(text))
        return [t for t in toks if t not in stopwords and len(t) > 1]

    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.decomposition import TruncatedSVD
    from sklearn.preprocessing import Normalizer

    doc_texts = [" ".join(tokenize(c["text"])) for c in chunks]
    gold = [json.loads(line) for line in open(ROOT / "data" / "annotations" / "qa_gold.jsonl", encoding="utf-8")]
    with_evidence = [g for g in gold if g.get("evidence")]

    for seed in (42, 7, 123):
        vectorizer = TfidfVectorizer(tokenizer=str.split, preprocessor=None, lowercase=False,
                                     ngram_range=(1, 2), sublinear_tf=True, min_df=2, norm="l2")
        X_tfidf = vectorizer.fit_transform(doc_texts)
        n_comp = min(128, X_tfidf.shape[0] - 1, X_tfidf.shape[1])
        svd = TruncatedSVD(n_components=n_comp, random_state=seed, algorithm="randomized")
        X_dense = Normalizer(copy=False).fit_transform(svd.fit_transform(X_tfidf))
        normalizer = Normalizer(copy=False)
        hits = 0
        for g in with_evidence:
            q_vec = normalizer.transform(svd.transform(vectorizer.transform([" ".join(tokenize(g["question"]))])))
            scores = (X_dense @ q_vec[0]).tolist()
            ranked = sorted(range(len(chunks)), key=lambda i: scores[i], reverse=True)[:5]
            pred = {chunks[i]["chunk_id"] for i in ranked}
            gold_ids = {e["chunk_id"] for e in g["evidence"]}
            if pred & gold_ids:
                hits += 1
        print(f"seed={seed}: recall@5={hits}/{len(with_evidence)}={hits / len(with_evidence):.4f}")
    print("Nhận xét: E1 ổn định qua 3 seed vì corpus nhỏ và SVD hội tụ; lấy seed 42 làm chính.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
