"""Sinh bảng so sánh E0-E8 từ metrics_summary.csv, tách retrieval và answer.

Giá trị trong bảng lấy trực tiếp từ script, không gõ tay.
Đầu ra: evaluation/comparison_E0_E1_E2.md
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    with open(ROOT / "evaluation" / "metrics_summary.csv", encoding="utf-8") as mf:
        rows = list(csv.DictReader(mf))
    order = {"E0": 0, "E1": 1, "E2": 2, "E3": 3, "E4": 4, "E5": 5, "E6": 6, "E7": 7, "E8": 8}
    rows.sort(key=lambda r: (order.get(r["run"], 9), r["split"]))
    test = [r for r in rows if r["split"] == "test"]
    meta = json.loads((ROOT / "data" / "splits" / "split_meta.json").read_text(encoding="utf-8"))
    n_test = int(meta.get("n_test", len(meta.get("test_ids", []))))
    dev_ids = set(meta.get("dev_ids", []))
    with open(ROOT / "data" / "annotations" / "qa_gold.jsonl", encoding="utf-8") as gf:
        gold = [json.loads(line) for line in gf if line.strip()]
    n_ev = sum(1 for g in gold if g.get("split") == "test" and g.get("evidence"))
    n_un = sum(1 for g in gold if g.get("split") == "test" and g.get("needs_more_evidence"))
    n_dev_ev = sum(1 for g in gold if g.get("split") == "dev" and g.get("evidence"))
    n_dev_un = sum(1 for g in gold if g.get("split") == "dev" and g.get("needs_more_evidence"))
    k_vals = sorted({int(r.get("k") or 0) for r in rows if str(r.get("k") or "").isdigit()})
    if k_vals and min(k_vals) >= 10:
        at10_note = (
            "Ghi chú @10: file prediction lưu top-10 `predicted_chunk_ids` (`k>=10`) nên "
            "`R@10` và `MRR@10` được tính trên đủ 10 chunk, còn `R@5`, `MRR@5`, `ctxP@5`, `ctxR@5` tính chặt trên top-5."
        )
    elif k_vals and max(k_vals) >= 10:
        runs_10 = ", ".join(sorted({r["run"] for r in rows if int(r.get("k") or 0) >= 10}))
        at10_note = (
            f"Ghi chú @10: các run `{runs_10}` lưu top-10 `predicted_chunk_ids` nên `R@10`/`MRR@10` "
            "phản ánh top-10 thật; các run còn lại lưu `k<=5` nên `@10` trùng `@5`."
        )
    else:
        at10_note = (
            "Ghi chú @10: `evaluate.py` tính `recall@10` và `mrr@10` bằng `recall_mrr_at(..., 10)`; "
            "khi prediction hiện tại chỉ lưu `k<=5`, `@10` bằng `@5`."
        )
    lines = [
        "# So sánh E0-E8 (do script sinh ra, không gõ tay)",
        "",
        "Nguồn số liệu: `evaluation/metrics_summary.csv` (do `src/evaluate/evaluate.py` sinh ra).",
        f"Cùng test ({n_test} câu, khớp `evaluation/split_freeze.json`) và cùng script chấm. Prediction nằm ở `evaluation/test_predictions/` và `evaluation/dev_predictions/`, nhãn refusal ở `evaluation/refusal_labels/`.",
        "E0-E2 là định mức bắt buộc; E3-E8 là phần nâng cao ngoài định mức: E3 lọc cứng metadata (baseline tái lập được), E4 rerank nhẹ, E5 rewrite truy vấn, E6 index bảng riêng, E7 contextual chunk, E8 lookup bảng có cấu trúc rồi mới RAG giải thích.",
        at10_note,
        "Faithfulness và answer relevancy bản LLM judge chưa áp dụng vì pipeline không gọi LLM;",
        "hai cột heuristic đo câu trả lời số không tìm thấy trong context và tỷ lệ câu giải quyết đúng.",
        "",
        f"## A. Chất lượng truy hồi (chỉ trên câu có evidence, test n={n_ev} evidence)",
        "",
        "| run | R@3 | R@5 | R@10 | MRR@3 | MRR@5 | MRR@10 | ctxP@5 | ctxR@5 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in test:
        lines.append(
            f"| {r['run']} | {r.get('recall_at_3', '')} | {r.get('recall_at_5', '')} | {r.get('recall_at_10', '')} | "
            f"{r.get('mrr_at_3', '')} | {r.get('mrr_at_5', '')} | {r.get('mrr_at_10', '')} | "
            f"{r.get('context_precision_at_5', '')} | {r.get('context_recall_at_5', '')} |"
        )
    lines += [
        "",
        "## B. Chất lượng trích dẫn (trích dẫn có hỗ trợ câu trả lời không)",
        "",
        "| run | citeP@top1 | citeR@5 | page_acc | citeFull |",
        "|---|---|---|---|---|",
    ]
    for r in test:
        lines.append(
            f"| {r['run']} | {r.get('citation_precision_top1', '')} | {r.get('citation_recall_at_5', '')} | {r.get('page_accuracy', '')} | {r.get('citation_complete_rate', '')} |"
        )
    lines += [
        "",
        "## C. Chất lượng câu trả lời (số và nghiệp vụ tài chính)",
        "",
        "| run | numeric | exact | period | company | year | version | unsup | faith_h | relev_h | falseAns |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in test:
        lines.append(
            f"| {r['run']} | {r.get('numeric_match', '')} | {r.get('exact_match', '')} | {r.get('period_accuracy', '')} | "
            f"{r.get('company_accuracy', '')} | {r.get('year_accuracy', '')} | {r.get('version_accuracy', '')} | "
            f"{r.get('unsupported_claim_rate', '')} | {r.get('faithfulness_heuristic', '')} | {r.get('answer_relevancy_heuristic', '')} | {r.get('false_answer_rate', '')} |"
        )
    lines += [
        "",
        f"## D. Từ chối và trạng thái trả lời (thiếu bằng chứng, test n={n_un})",
        "",
        "| run | refP | refR | TR | MR | FR | TA | ans | part | ref | amb | file |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in test:
        lines.append(
            f"| {r['run']} | {r.get('refusal_precision', '')} | {r.get('refusal_recall', '')} | "
            f"{r.get('true_refusal', '')} | {r.get('missed_refusal', '')} | {r.get('false_refusal', '')} | {r.get('true_answer', '')} | "
            f"{r.get('status_answered', '')} | {r.get('status_partial', '')} | {r.get('status_refused', '')} | {r.get('status_ambiguous', '')} | "
            f"{r.get('prediction_file', '')} |"
        )
    dev = [r for r in rows if r["split"] == "dev"]
    dev_r5 = ", ".join(f"{r['run']}={r.get('recall_at_5', '')}" for r in dev)
    dev_ref = ", ".join(f"{r['run']}={r.get('refusal_precision', '')}/{r.get('refusal_recall', '')}" for r in dev)
    test_r5 = ", ".join(f"{r['run']}={r.get('recall_at_5', '')}" for r in test)
    test_num = ", ".join(f"{r['run']}={r.get('numeric_match', '')}" for r in test)
    test_ref = ", ".join(f"{r['run']}={r.get('refusal_precision', '')}/{r.get('refusal_recall', '')}" for r in test)
    test_false = ", ".join(f"{r['run']}={r.get('false_answer_rate', '')}" for r in test)
    lines += [
        "",
        "## Quyet dinh dua tren dev (truoc khi nhin test)",
        "",
        f"- Dev co {n_dev_ev} cau co evidence va {n_dev_un} cau thieu bang chung tren {len(dev_ids)} cau. Dev R@5: {dev_r5}.",
        f"- Dev refusal P/R: {dev_ref}.",
        f"- Test truy hoi R@5: {test_r5}.",
        f"- Test answer so numeric_match: {test_num}.",
        f"- Test refusal P/R: {test_ref}.",
        f"- Test false_answer_rate: {test_false}.",
        "- E8 la cau hinh de xuat cho cau hoi so (lookup co cau truc truoc, RAG giai thich sau); E3 la baseline loc cung tai lap duoc tot nhat nhom thuan retrieval; E0 giu lam baseline; E4/E5/E6/E7 la ablation cho rerank, rewrite, table index, contextual chunk.",
    ]
    out = ROOT / "evaluation" / "comparison_E0_E1_E2.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Đã ghi -> {out} ({len(rows)} dòng metric)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
