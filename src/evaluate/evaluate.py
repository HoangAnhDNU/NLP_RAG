"""Chấm metric E0/E1/E2 bằng cùng một script (Mục 3, Mục 4.6.5).

Đọc prediction CSV của một run và `qa_gold.jsonl`, tính trên dev và test:
- retrieval: Recall@k, MRR@k (k = số chunk dự đoán trong file).
- citation: trích dẫn đúng khi top-1 chunk nằm trong evidence gold
  (chỉ tính trên câu có evidence).
- answer: numeric match khi predicted_answer khớp gold sau chuẩn hóa
  (E0 để trống nên luôn 0, ghi rõ để E1/E2 so sánh).
- refusal: tỷ lệ từ chối đúng trên nhóm thiếu bằng chứng.

Ví dụ:
    python src/evaluate/evaluate.py --run E0
    python src/evaluate/evaluate.py --run E0 --pred evaluation/test_predictions_E0.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.build_chunks import normalize_number  # noqa: E402

REFUSAL_TEXT = "Không đủ bằng chứng trong corpus để trả lời."


def norm_answer(text: str) -> str:
    text = (text or "").strip().lower()
    return " ".join(text.split())


def main() -> int:
    p = argparse.ArgumentParser(description="Cham metric retrieval/answer/citation.")
    p.add_argument("--run", default="E0")
    p.add_argument("--pred", default=None)
    p.add_argument("--gold", default=str(ROOT / "data" / "annotations" / "qa_gold.jsonl"))
    p.add_argument("--out", default=str(ROOT / "evaluation" / "metrics_summary.csv"))
    args = p.parse_args()

    gold = {json.loads(line)["question_id"]: json.loads(line) for line in open(args.gold, encoding="utf-8")}
    pred_path = Path(args.pred) if args.pred else ROOT / "evaluation" / f"test_predictions_{args.run}.csv"
    rows = list(csv.DictReader(open(pred_path, encoding="utf-8")))

    by_split: dict[str, list[dict]] = {"dev": [], "test": []}
    dev_path = pred_path.parent / pred_path.name.replace("test_", "dev_")
    all_rows = rows
    if dev_path.exists() and dev_path != pred_path:
        all_rows = list(csv.DictReader(open(dev_path, encoding="utf-8"))) + rows
    for r in all_rows:
        by_split.setdefault(r.get("split", "test"), []).append(r)

    summary: list[dict] = []
    for split in ("dev", "test"):
        items = by_split.get(split, [])
        n = len(items)
        recalls, mrrs = [], []
        cit_hit, cit_den = 0, 0
        ans_hit, ans_den = 0, 0
        ref_hit, ref_den = 0, 0
        for r in items:
            g = gold.get(r["question_id"], {})
            pred_chunks = [c for c in (r.get("predicted_chunk_ids") or "").split(";") if c]
            gold_chunks = [c for c in (r.get("gold_chunk_ids") or "").split(";") if c]
            if gold_chunks:
                hit = any(c in pred_chunks for c in gold_chunks)
                recalls.append(1.0 if hit else 0.0)
                rank = next((i + 1 for i, c in enumerate(pred_chunks) if c in gold_chunks), None)
                mrrs.append(1.0 / rank if rank else 0.0)
                cit_den += 1
                if pred_chunks and pred_chunks[0] in gold_chunks:
                    cit_hit += 1
            if g.get("needs_more_evidence"):
                ref_den += 1
                if norm_answer(r.get("predicted_answer", "")) == norm_answer(REFUSAL_TEXT):
                    ref_hit += 1
            elif g.get("gold_answer"):
                ans_den += 1
                if norm_answer(r.get("predicted_answer", "")) == norm_answer(g.get("gold_answer", "")):
                    ans_hit += 1
        k = max((len((r.get("predicted_chunk_ids") or "").split(";")) for r in items), default=0)
        summary.append(
            {
                "run": args.run,
                "split": split,
                "n": n,
                "k": k,
                "recall_at_k": round(sum(recalls) / len(recalls), 4) if recalls else 0.0,
                "mrr_at_k": round(sum(mrrs) / len(mrrs), 4) if mrrs else 0.0,
                "citation_correctness": round(cit_hit / cit_den, 4) if cit_den else 0.0,
                "numeric_match": round(ans_hit / ans_den, 4) if ans_den else 0.0,
                "refusal_rate": round(ref_hit / ref_den, 4) if ref_den else 0.0,
                "refusal_den": ref_den,
                "prediction_file": pred_path.name,
            }
        )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
        w.writeheader()
        w.writerows(summary)

    for s in summary:
        print(f"{s['run']}/{s['split']}: n={s['n']} R@{s['k']}={s['recall_at_k']} "
              f"MRR={s['mrr_at_k']} cite={s['citation_correctness']} "
              f"ans={s['numeric_match']} refusal={s['refusal_rate']}({s['refusal_den']})")
    print(f"Đã ghi -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
