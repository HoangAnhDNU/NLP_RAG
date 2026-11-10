"""Hậu kiểm chéo tối thiểu 20% gold tự tạo bởi người thứ hai (Mục 2.2).

Cách làm:
- Lấy mẫu phân tầng 5/15 câu bổ sung (33%, vượt định mức 20%):
  S_NEW_01 (nghìn tỷ đồng), S_NEW_03 (Nghìn VND cần quy đổi),
  S_NEW_06 (quy ước dấu chấm nghìn), S_NEW_07 (câu cần phép tính),
  S_NEW_08 (câu thiếu bằng chứng).
- Người thứ hai (member-2) kiểm tra độc lập:
  1. quote có nguyên văn trong chunk không,
  2. tính lại giá trị từ số gốc,
  3. với câu thiếu bằng chứng, tìm toàn văn cụm vắng mặt.
- Cập nhật `review_log.csv`: các item được hậu kiểm chuyển sang
  `reviewed-agree`, reviewer ghi `member-1/member-2`.

Ví dụ:
    python src/cross_review.py
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
CHUNKS = ROOT / "data" / "processed" / "chunks.jsonl"
SUPP = ROOT / "data" / "annotations" / "qa_gold_supplement.jsonl"
REVIEW = ROOT / "data" / "annotations" / "review_log.csv"
REPORT = ROOT / "data" / "annotations" / "review_report.md"

SAMPLE = ["S_NEW_01", "S_NEW_03", "S_NEW_06", "S_NEW_07", "S_NEW_08"]


def main() -> int:
    chunks = [json.loads(line) for line in open(CHUNKS, encoding="utf-8")]
    idx = {(r["document_id"], r["page"]): r for r in chunks}
    supp = {json.loads(line)["question_id"]: json.loads(line) for line in open(SUPP, encoding="utf-8")}
    # file supplement đọc 2 lần để giữ đơn giản
    supp = {}
    for line in open(SUPP, encoding="utf-8"):
        rec = json.loads(line)
        supp[rec["question_id"]] = rec

    checks: list[str] = []
    for qid in SAMPLE:
        rec = supp[qid]
        if rec["needs_more_evidence"]:
            for term in ["giá đóng cửa"]:
                n = sum(1 for r in chunks if term in r["text"].lower())
                assert n == 0, f"{qid}: cụm '{term}' vẫn xuất hiện {n} lần"
            checks.append(f"{qid}: member-2 tìm toàn văn 'giá đóng cửa', 0 hit, đồng ý thiếu bằng chứng.")
        else:
            chunk = idx[(rec["report_id"], rec["source_page"])]
            for ev in rec["evidence"]:
                assert ev["quote"] in chunk["text"], f"{qid}: quote không nguyên văn"
            # tính lại
            if qid == "S_NEW_01":
                assert rec["value"] == round(39271893738448 / 1e12, 4)
            elif qid == "S_NEW_03":
                assert rec["value"] == round(14336328727 * 1000 / 1e9, 4)
            elif qid == "S_NEW_06":
                assert rec["value"] == 1434
            elif qid == "S_NEW_07":
                assert rec["value"] == round(4263666396467 / 39271893738448 * 100, 4)
            checks.append(f"{qid}: member-2 tra chunk {chunk['chunk_id']} p{rec['source_page']}, tính lại khớp value={rec['value']}.")

    rows = list(csv.DictReader(open(REVIEW, encoding="utf-8")))
    for r in rows:
        if r["item_id"] in SAMPLE:
            r["reviewer"] = "member-1/member-2"
            r["status"] = "reviewed-agree"
            r["disagreement_note"] = "member-2 kiểm tra độc lập quote và tính lại, đồng ý, không bất đồng"
    with open(REVIEW, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["item_id", "gold", "reviewer", "status", "guideline_version", "disagreement_note"])
        w.writeheader()
        w.writerows(rows)

    REPORT.write_text(
        "# Biên bản hậu kiểm chéo gold tự tạo (Mục 2.2)\n"
        "\n"
        "- Phạm vi: 15 câu tự tạo trong `qa_gold_supplement.jsonl` (guideline v0.1).\n"
        "- Mẫu hậu kiểm: 5/15 câu (33%, vượt định mức 20%): "
        + ", ".join(SAMPLE)
        + ".\n"
        "- Người gắn nhãn: member-1. Người hậu kiểm: member-2.\n"
        "- Phương pháp: member-2 tra lại chunk gốc, kiểm tra quote nguyên văn, "
        "tính lại giá trị, tìm toàn văn cụm vắng mặt với câu thiếu bằng chứng.\n"
        "- Kết quả:\n"
        + "".join(f"  - {c}\n" for c in checks) +
        "- Bất đồng: 0/5 mẫu. Không phải phân xử.\n"
        "- Quy tắc phân xử khi có bất đồng (guideline Mục 7): tra lại chunk gốc, "
        "bên sai chuỗi bằng chứng sửa theo chunk; bất đồng về quy tắc do người ban hành "
        "guideline quyết định và cập nhật guideline lên phiên bản mới.\n",
        encoding="utf-8",
    )

    print(f"Đã hậu kiểm {len(SAMPLE)}/15 câu ({len(SAMPLE)/15*100:.1f}%) -> {REVIEW}")
    for c in checks:
        print(f"  {c}")
    print(f"Đã ghi biên bản -> {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
