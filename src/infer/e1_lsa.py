"""E1: truy hồi dense LSA trên TF-IDF bigram tiếng Việt (đối chứng với BM25 E0).

Giả thuyết: LSA bắt cụm danh từ tài chính và từ đồng nghĩa tốt hơn BM25 unigram,
nên Recall@k cao hơn trên chunk tiếng Việt giữ dấu.
Không sinh văn bản, predicted_answer để trống như E0 để so sánh công bằng.

Đầu ra:
- evaluation/dev_predictions_E1.csv
- evaluation/test_predictions_E1.csv
- evaluation/lsa_index_E1.npz + evaluation/lsa_vocab_E1.json (cache index)

Ví dụ:
    python src/infer/e1_lsa.py
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import yaml

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.preprocess.normalize import normalize_query, tokenize_vi  # noqa: E402


def load_config(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> int:
    p = argparse.ArgumentParser(description="Chạy E1 dense LSA.")
    p.add_argument("--config", default=str(ROOT / "config" / "e1_tfidf.yaml"))
    p.add_argument("--gold", default=str(ROOT / "data" / "annotations" / "qa_gold.jsonl"))
    p.add_argument("--outdir", default=str(ROOT / "evaluation"))
    args = p.parse_args()

    cfg = load_config(Path(args.config))
    top_k = int(cfg["retrieval"]["top_k"])

    e0_cfg = load_config(ROOT / "config" / "e0_bm25.yaml")
    stopwords = set(e0_cfg.get("stopwords", []))

    chunks_path = ROOT / cfg["corpus"]["chunks"]
    chunks = [json.loads(line) for line in open(chunks_path, encoding="utf-8")]

    def tokenize(text: str) -> list[str]:
        toks = tokenize_vi(normalize_query(text))
        return [t for t in toks if t not in stopwords and len(t) > 1]

    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.decomposition import TruncatedSVD
    from sklearn.preprocessing import Normalizer
    import numpy as np

    doc_texts = [" ".join(tokenize(c["text"])) for c in chunks]
    ngram = tuple(cfg["model"].get("ngram_range", [1, 2]))
    vectorizer = TfidfVectorizer(
        tokenizer=str.split,
        preprocessor=None,
        lowercase=False,
        ngram_range=ngram,
        sublinear_tf=bool(cfg["model"].get("sublinear_tf", True)),
        min_df=int(cfg["model"].get("min_df", 2)),
        norm="l2",
    )
    X_tfidf = vectorizer.fit_transform(doc_texts)
    n_comp = int(cfg["model"].get("svd_components", 128))
    n_comp = min(n_comp, X_tfidf.shape[0] - 1, X_tfidf.shape[1])
    svd = TruncatedSVD(
        n_components=n_comp,
        random_state=int(cfg["model"].get("svd_random_state", 42)),
        algorithm="randomized",
    )
    X_dense = svd.fit_transform(X_tfidf)
    normalizer = Normalizer(copy=False)
    X_dense = normalizer.fit_transform(X_dense)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(outdir / "lsa_index_E1.npz", dense=X_dense,
                        explained=svd.explained_variance_ratio_)
    with open(outdir / "lsa_vocab_E1.json", "w", encoding="utf-8") as f:
        json.dump({"vocab_size": len(vectorizer.vocabulary_),
                   "n_components": n_comp,
                   "seed": 42}, f, ensure_ascii=False, indent=2)

    gold = [json.loads(line) for line in open(args.gold, encoding="utf-8")]
    fields = ["question_id", "question", "split", "gold_answer", "gold_chunk_ids",
              "predicted_chunk_ids", "predicted_top1_chunk_id", "predicted_company",
              "predicted_year", "predicted_report_version", "predicted_page",
              "predicted_n_tables", "retrieval_score_top1", "predicted_answer"]
    by_split: dict[str, list[dict]] = {"dev": [], "test": []}
    for g in gold:
        q_vec = normalizer.transform(svd.transform(vectorizer.transform([" ".join(tokenize(g["question"]))])))
        scores = (X_dense @ q_vec[0]).tolist()
        ranked = sorted(range(len(chunks)), key=lambda i: scores[i], reverse=True)[:top_k]
        top_chunks = [chunks[i] for i in ranked]
        top1 = top_chunks[0] if top_chunks else {}
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
               "retrieval_score_top1": f"{scores[ranked[0]]:.4f}" if ranked else "0.0000",
               "predicted_answer": ""}
        by_split.setdefault(g.get("split", "test"), []).append(row)

    for split in ("dev", "test"):
        out = outdir / f"{split}_predictions_E1.csv"
        with open(out, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(by_split.get(split, []))
        print(f"Đã ghi {len(by_split.get(split, []))} dòng {split} -> {out}")
    print(f"Config: {args.config} (tfidf {ngram}, svd={n_comp}, top_k={top_k}, corpus={len(chunks)} chunk)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
