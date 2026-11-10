"""Baseline E0: BM25 + trích đoạn nguồn (không sinh văn bản).

Đọc config `config/e0_bm25.yaml`, index toàn bộ `chunks.jsonl` cố định,
với mỗi câu trong `qa_gold.jsonl` trả về top-k đoạn/bảng nguồn kèm trích dẫn
(company, year, report_version, page, table, chunk_id).

Theo Mục 4.6.3, baseline không bắt buộc sinh văn bản nên `predicted_answer`
để trống; hệ thống không từ chối câu thiếu bằng chứng ở E0.

Đầu ra:
- evaluation/dev_predictions/dev_predictions_E0.csv (10 dòng dev)
- evaluation/test_predictions/test_predictions_E0.csv (40 dòng test, file bắt buộc Mục 3)

Ví dụ:
    python src/infer/e0_bm25.py
    python src/infer/e0_bm25.py --config config/e0_bm25.yaml --top_k 5
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
from src.retrieval.bm25 import BM25Retriever  # noqa: E402


def load_config(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> int:
    p = argparse.ArgumentParser(description="Chay baseline E0 BM25.")
    p.add_argument("--config", default=str(ROOT / "config" / "e0_bm25.yaml"))
    p.add_argument("--top_k", type=int, default=None)
    p.add_argument("--gold", default=str(ROOT / "data" / "annotations" / "qa_gold.jsonl"))
    p.add_argument("--outdir", default=str(ROOT / "evaluation"))
    args = p.parse_args()

    cfg = load_config(Path(args.config))
    top_k = args.top_k or int(cfg["retrieval"]["top_k"])
    stopwords = set(cfg.get("stopwords", []))

    chunks_path = ROOT / cfg["corpus"]["chunks"]
    chunks = [json.loads(line) for line in open(chunks_path, encoding="utf-8")]

    def tokenize(text: str) -> list[str]:
        toks = tokenize_vi(normalize_query(text))
        return [t for t in toks if t not in stopwords and len(t) > 1]

    retriever = BM25Retriever(
        k1=float(cfg["retrieval"].get("k1", 1.5)),
        b=float(cfg["retrieval"].get("b", 0.75)),
    ).fit([tokenize(c["text"]) for c in chunks])

    gold = [json.loads(line) for line in open(args.gold, encoding="utf-8")]

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    fields = [
        "question_id",
        "question",
        "split",
        "gold_answer",
        "gold_chunk_ids",
        "predicted_chunk_ids",
        "predicted_top1_chunk_id",
        "predicted_company",
        "predicted_year",
        "predicted_report_version",
        "predicted_page",
        "predicted_n_tables",
        "bm25_score_top1",
        "predicted_answer",
    ]

    by_split: dict[str, list[dict]] = {"dev": [], "test": []}
    for g in gold:
        ranked = retriever.top_k(tokenize(g["question"]), top_k)
        top_chunks = [chunks[i] for i, _ in ranked]
        top1 = top_chunks[0] if top_chunks else {}
        row = {
            "question_id": g["question_id"],
            "question": g["question"],
            "split": g.get("split", ""),
            "gold_answer": g.get("gold_answer", ""),
            "gold_chunk_ids": ";".join(e["chunk_id"] for e in g.get("evidence", [])),
            "predicted_chunk_ids": ";".join(c["chunk_id"] for c in top_chunks),
            "predicted_top1_chunk_id": top1.get("chunk_id", ""),
            "predicted_company": top1.get("company_id", ""),
            "predicted_year": top1.get("fiscal_year", ""),
            "predicted_report_version": top1.get("report_version", ""),
            "predicted_page": top1.get("page", ""),
            "predicted_n_tables": top1.get("n_tables", ""),
            "bm25_score_top1": f"{ranked[0][1]:.4f}" if ranked else "0.0000",
            "predicted_answer": "",
        }
        by_split.setdefault(g.get("split", "test"), []).append(row)

    for split in ("dev", "test"):
        subdir = outdir / ("dev_predictions" if split == "dev" else "test_predictions")
        subdir.mkdir(parents=True, exist_ok=True)
        out = subdir / f"{split}_predictions_E0.csv"
        with open(out, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(by_split.get(split, []))
        print(f"Đã ghi {len(by_split.get(split, []))} dòng {split} -> {out}")

    print(f"Config: {args.config} (k1={retriever.k1}, b={retriever.b}, top_k={top_k}, corpus={len(chunks)} chunk)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
