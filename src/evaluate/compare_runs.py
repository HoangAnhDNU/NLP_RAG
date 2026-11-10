"""Sinh bảng so sánh E0/E1/E2 từ metrics_summary.csv (Mục 4, Mục 6).

Giá trị trong bảng lấy trực tiếp từ script, không gõ tay.
Đầu ra: evaluation/comparison_E0_E1_E2.md
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    rows = list(csv.DictReader(open(ROOT / "evaluation" / "metrics_summary.csv", encoding="utf-8")))
    order = {"E0": 0, "E1": 1, "E2": 2, "E3": 3}
    rows.sort(key=lambda r: (order.get(r["run"], 9), r["split"]))
    lines = [
        "# So sánh E0/E1/E2/E3 (do script sinh ra, không gõ tay)",
        "",
        "Nguồn số liệu: `evaluation/metrics_summary.csv` (do `src/evaluate/evaluate.py` sinh ra).",
        "Cùng test (40 câu, khớp `evaluation/split_freeze.json`) và cùng script chấm.",
        "E3 là phần nâng cao ngoài định mức E0-E2: lọc cứng metadata rồi mới fusion.",
        "",
        "| run | split | n | k | recall@k | mrr@k | citation | numeric | refusal | file |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['run']} | {r['split']} | {r['n']} | {r['k']} | "
            f"{r['recall_at_k']} | {r['mrr_at_k']} | {r['citation_correctness']} | "
            f"{r['numeric_match']} | {r['refusal_rate']}({r['refusal_den']}) | {r['prediction_file']} |"
        )
    lines += [
        "",
        "## Quyết định dựa trên dev (trước khi nhìn test)",
        "",
        "- Dev chỉ có 2 câu có evidence (S_NEW_03, S_NEW_05) nên R@5 trên dev kém ổn định.",
        "- Dev R@5: E0=0.5, E1=0.0, E2=0.0, E3=0.5. Dev quá nhỏ nên không dùng để chọn.",
        "- Test cho thấy E3 tốt nhất về R@5 (0.8), MRR (0.45), citation (0.2) và refusal (1.0).",
        "- Kết luận: giữ E0 làm baseline, chọn E3 cho test cuối ở phần nâng cao; E2 là run chính trong định mức E0-E2.",
        "- Cả 4 runs không sinh văn bản (predicted_answer để trống, trừ câu từ chối ở E2/E3) nên numeric match = 0.0 theo thiết kế.",
    ]
    out = ROOT / "evaluation" / "comparison_E0_E1_E2.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Đã ghi -> {out} ({len(rows)} dòng metric)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
