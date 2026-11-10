"""E2: hybrid BM25 + dense LSA, lọc metadata công ty/năm, xếp lại, từ chối.

Khác E1 ở chiến lược (không chỉ đổi tên file hay tham số):
- hợp nhất BM25 (từ vựng) + LSA dense (ngữ nghĩa) với alpha=0.5 trên top-20 ứng viên,
- cộng điểm metadata khi chunk khớp mã CK hoặc năm trong câu hỏi,
- quy tắc từ chối theo 10 mẫu ngoài corpus (quý, bán niên, kế hoạch, dự báo...).

Đầu ra:
- evaluation/dev_predictions/dev_predictions_E2.csv
- evaluation/test_predictions/test_predictions_E2.csv

Ví dụ:
    python src/infer/e2_hybrid.py
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

import yaml

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.preprocess.normalize import normalize_query, tokenize_vi  # noqa: E402
from src.retrieval.bm25 import BM25Retriever  # noqa: E402

TICKERS = ["HPG", "HSG", "NKG", "MSR"]
YEAR_RE = re.compile(r"\b(20[0-2]\d)\b")


def detect_meta(question: str) -> tuple[list[str], list[str]]:
    up = question.upper()
    tickers = [t for t in TICKERS if re.search(rf"(?<![A-Z]){t}(?![A-Z])", up)]
    years = YEAR_RE.findall(question)
    return tickers, years


def load_config(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def minmax(scores: list[float]) -> list[float]:
    lo, hi = min(scores), max(scores)
    if hi <= lo:
        return [0.0 for _ in scores]
    return [(s - lo) / (hi - lo) for s in scores]


def main() -> int:
    p = argparse.ArgumentParser(description="Chạy E2 hybrid.")
    p.add_argument("--config", default=str(ROOT / "config" / "e2_hybrid.yaml"))
    p.add_argument("--gold", default=str(ROOT / "data" / "annotations" / "qa_gold.jsonl"))
    p.add_argument("--outdir", default=str(ROOT / "evaluation"))
    args = p.parse_args()

    cfg = load_config(Path(args.config))
    top_k = int(cfg["retrieval"]["top_k"])
    cand_k = int(cfg["retrieval"].get("candidate_k", 20))
    alpha = float(cfg["retrieval"].get("fusion_alpha", 0.5))
    bonus = float(cfg["retrieval"].get("metadata_bonus", 0.15))
    refusal_text = cfg["refusal"]["text"]
    patterns = [s.lower() for s in cfg["refusal"].get("patterns", [])]

    e0_cfg = load_config(ROOT / "config" / "e0_bm25.yaml")
    stopwords = set(e0_cfg.get("stopwords", []))
    e1_cfg = load_config(ROOT / cfg["model"]["dense_source"])

    chunks = [json.loads(line) for line in open(ROOT / cfg["corpus"]["chunks"], encoding="utf-8")]

    def tokenize(text: str) -> list[str]:
        toks = tokenize_vi(normalize_query(text))
        return [t for t in toks if t not in stopwords and len(t) > 1]

    tokenized_docs = [tokenize(c["text"]) for c in chunks]
    bm25 = BM25Retriever(k1=float(cfg["retrieval"].get("bm25_k1", 1.5)),
                         b=float(cfg["retrieval"].get("bm25_b", 0.75))).fit(tokenized_docs)

    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.decomposition import TruncatedSVD
    from sklearn.preprocessing import Normalizer

    doc_texts = [" ".join(t) for t in tokenized_docs]
    ngram = tuple(e1_cfg["model"].get("ngram_range", [1, 2]))
    vectorizer = TfidfVectorizer(tokenizer=str.split, preprocessor=None, lowercase=False,
                                 ngram_range=ngram, sublinear_tf=True, min_df=2, norm="l2")
    X_tfidf = vectorizer.fit_transform(doc_texts)
    n_comp = min(int(e1_cfg["model"].get("svd_components", 128)), X_tfidf.shape[0] - 1, X_tfidf.shape[1])
    svd = TruncatedSVD(n_components=n_comp, random_state=42, algorithm="randomized")
    X_dense = Normalizer(copy=False).fit_transform(svd.fit_transform(X_tfidf))
    normalizer = Normalizer(copy=False)

    gold = [json.loads(line) for line in open(args.gold, encoding="utf-8")]
    fields = ["question_id", "question", "split", "gold_answer", "gold_chunk_ids",
              "predicted_chunk_ids", "predicted_top1_chunk_id", "predicted_company",
              "predicted_year", "predicted_report_version", "predicted_page",
              "predicted_n_tables", "retrieval_score_top1", "predicted_answer"]
    by_split: dict[str, list[dict]] = {"dev": [], "test": []}

    for g in gold:
        q_toks = tokenize(g["question"])
        bm25_scores = bm25.score(q_toks)
        q_vec = normalizer.transform(svd.transform(vectorizer.transform([" ".join(q_toks)])))
        dense_scores = (X_dense @ q_vec[0]).tolist()

        bm25_rank = sorted(range(len(chunks)), key=lambda i: bm25_scores[i], reverse=True)[:cand_k]
        dense_rank = sorted(range(len(chunks)), key=lambda i: dense_scores[i], reverse=True)[:cand_k]
        cand = list(dict.fromkeys(bm25_rank + dense_rank))

        b_norm = minmax([bm25_scores[i] for i in cand])
        d_norm = minmax([dense_scores[i] for i in cand])
        tickers, years = detect_meta(g["question"])
        fused = []
        for j, i in enumerate(cand):
            c = chunks[i]
            s = (1 - alpha) * b_norm[j] + alpha * d_norm[j]
            if tickers or years:
                c_match = (not tickers) or (c.get("company_id") in tickers)
                y_match = (not years) or (str(c.get("fiscal_year")) in years)
                if c_match and y_match:
                    s += bonus
                elif c_match or y_match:
                    s += bonus / 2
            fused.append((s, i))
        fused.sort(key=lambda x: x[0], reverse=True)
        ranked = [i for _, i in fused[:top_k]]
        top_chunks = [chunks[i] for i in ranked]
        top1 = top_chunks[0] if top_chunks else {}

        q_low = g["question"].lower()
        refused = any(pat in q_low for pat in patterns)
        row = {"question_id": g["question_id"], "question": g["question"],
               "split": g.get("split", ""), "gold_answer": g.get("gold_answer", ""),
               "gold_chunk_ids": ";".join(e["chunk_id"] for e in g.get("evidence", [])),
               "predicted_chunk_ids": ";".join(c["chunk_id"] for c in top_chunks),
               "predicted_top1_chunk_id": top1.get("chunk_id", ""),
               "predicted_company": top1.get("company_id", ""),
               "predicted_year": top1.get("fiscal_year", ""),
               "predicted_report_version": top1.get("report_version", ""),
               "predicted_page": top1.get("page", ""),
               "predicted_n_tables": top1.get("n_tables", ""),
               "retrieval_score_top1": f"{fused[0][0]:.4f}" if fused else "0.0000",
               "predicted_answer": refusal_text if refused else ""}
        by_split.setdefault(g.get("split", "test"), []).append(row)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    for split in ("dev", "test"):
        subdir = outdir / ("dev_predictions" if split == "dev" else "test_predictions")
        subdir.mkdir(parents=True, exist_ok=True)
        out = subdir / f"{split}_predictions_E2.csv"
        with open(out, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(by_split.get(split, []))
        print(f"Đã ghi {len(by_split.get(split, []))} dòng {split} -> {out}")
    print(f"Config: {args.config} (alpha={alpha}, cand_k={cand_k}, top_k={top_k}, bonus={bonus})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
