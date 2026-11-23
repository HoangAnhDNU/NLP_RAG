"""Gộp 35 câu ViFinQA khớp corpus và 15 câu tự tạo thành bộ gold 50 câu,
chia split dev/test và sinh các file hồ sơ gắn nhãn.

Quy tắc chia split (ghi nhận để tái lập):
- seed cố định 42, xáo trộn danh sách câu trả lời được rồi cắt 10 câu đầu làm dev.
- Toàn bộ 8 câu thiếu bằng chứng nằm ở test (định mức tối thiểu 08 câu).
- Không chia câu paraphrase gần trùng sang hai split: kiểm tra trùng lặp
  câu hỏi theo chuẩn hóa chữ thường, báo cáo nếu trùng khớp hoàn toàn.

Đầu ra:
- data/annotations/qa_gold.jsonl   (50 dòng, schema thống nhất)
- data/annotations/gold_labels.csv  (bản CSV gọn để chấm thủ công)
- data/annotations/review_log.csv   (khởi tạo, 15 câu bổ sung chờ hậu kiểm)
- data/splits/dev.json, test.json, split_meta.json (đóng băng, có hash)

Ví dụ:
    python src/build_gold.py
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
ANNOT = ROOT / "data" / "annotations"
SPLITS = ROOT / "data" / "splits"

SEED = 42
QA_JSONL = ANNOT / "qa_gold.jsonl"
LABELS_CSV = ANNOT / "gold_labels.csv"
REVIEW_CSV = ANNOT / "review_log.csv"

LABEL_FIELDS = [
    "question_id",
    "question",
    "company_id",
    "fiscal_year",
    "unit",
    "answer_type",
    "source",
]


def norm_question(text: str) -> str:
    return " ".join(text.lower().split())


def main() -> int:
    parser = argparse.ArgumentParser(description="Build v1 synthetic gold QA set and splits.")
    parser.add_argument(
        "--force-v1",
        action="store_true",
        help="Allow overwriting an existing qa_gold.jsonl with > 50 rows.",
    )
    args = parser.parse_args()

    if QA_JSONL.exists():
        with open(QA_JSONL, encoding="utf-8") as f:
            existing_count = sum(1 for line in f if line.strip())
        if existing_count > 50 and not args.force_v1:
            print(
                f"Refusing to overwrite {QA_JSONL} ({existing_count} rows > 50). "
                "Pass --force-v1 to explicitly regenerate v1.",
                file=sys.stderr,
            )
            return 1

    matched = list(csv.DictReader(open(PROCESSED / "questions_matched.csv", encoding="utf-8")))
    supplement = [json.loads(line) for line in open(ANNOT / "qa_gold_supplement.jsonl", encoding="utf-8")]

    records: list[dict] = []
    for row in matched:
        records.append(
            {
                "question_id": row["source_question_id"],
                "question": row["question"],
                "gold_answer": "",
                "answer_type": row["answer_type"],
                "value": "",
                "unit": row["unit"],
                "company_id": row["company_id"],
                "fiscal_year": row["years_in_corpus"],
                "report_id": "",
                "evidence": [],
                "computation": "",
                "source_page": "",
                "needs_more_evidence": False,
                "reviewer_id": "",
                "review_status": "pending-answer",
                "source": "vifinqa",
            }
        )
    for rec in supplement:
        records.append({**rec, "source": "supplement"})

    assert len(records) == 50, f"Bộ gold phải có 50 câu, hiện có {len(records)}"

    # kiểm tra trùng câu hỏi
    seen: dict[str, str] = {}
    for rec in records:
        key = norm_question(rec["question"])
        if key in seen:
            print(f"CẢNH BÁO trùng câu hỏi: {rec['question_id']} trùng với {seen[key]}", file=sys.stderr)
        seen.setdefault(key, rec["question_id"])

    answerable = [r for r in records if not r["needs_more_evidence"]]
    unanswerable = [r for r in records if r["needs_more_evidence"]]
    assert len(unanswerable) == 8, f"Cần 8 câu thiếu bằng chứng, hiện có {len(unanswerable)}"

    rng = random.Random(SEED)
    rng.shuffle(answerable)
    dev = answerable[:10]
    test_answerable = answerable[10:]
    test = test_answerable + unanswerable
    rng.shuffle(test)

    assert len(dev) == 10 and len(test) == 40
    assert {r["question_id"] for r in unanswerable} <= {r["question_id"] for r in test}, \
        "Toàn bộ 8 câu thiếu bằng chứng phải nằm ở test"
    n_test_unanswerable = sum(1 for r in test if r["needs_more_evidence"])
    n_test_numeric = sum(1 for r in test if r["unit"])
    assert n_test_unanswerable >= 8, f"Test cần ít nhất 8 câu thiếu bằng chứng, hiện có {n_test_unanswerable}"
    assert n_test_numeric >= 10, f"Test cần ít nhất 10 câu số/đơn vị, hiện có {n_test_numeric}"

    split_of = {r["question_id"]: "dev" for r in dev}
    split_of.update({r["question_id"]: "test" for r in test})
    for rec in records:
        rec["split"] = split_of[rec["question_id"]]

    ANNOT.mkdir(parents=True, exist_ok=True)
    SPLITS.mkdir(parents=True, exist_ok=True)

    with open(QA_JSONL, "w", encoding="utf-8", newline="\n") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    with open(LABELS_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LABEL_FIELDS)
        writer.writeheader()
        for rec in records:
            writer.writerow({k: rec.get(k, "") for k in LABEL_FIELDS})

    with open(REVIEW_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "item_id",
                "gold",
                "reviewer",
                "status",
                "guideline_version",
                "disagreement_note",
            ],
        )
        writer.writeheader()
        for rec in supplement:
            writer.writerow(
                {
                    "item_id": rec["question_id"],
                    "gold": rec["gold_answer"],
                    "reviewer": rec["reviewer_id"],
                    "status": "needs-second-reviewer",
                    "guideline_version": "v0.1",
                    "disagreement_note": "",
                }
            )
        for rec in matched:
            writer.writerow(
                {
                    "item_id": rec["source_question_id"],
                    "gold": "",
                    "reviewer": "",
                    "status": "pending-answer",
                    "guideline_version": "v0.1",
                    "disagreement_note": "chưa gắn nhãn đáp án",
                }
            )

    meta = {
        "version": "v1",
        "seed": SEED,
        "n_dev": len(dev),
        "n_test": len(test),
        "dev_ids": sorted(r["question_id"] for r in dev),
        "test_ids": sorted(r["question_id"] for r in test),
        "rule": "8 câu thiếu bằng chứng đều nằm ở test; dev gồm 10 câu trả lời được",
    }
    with open(SPLITS / "dev.json", "w", encoding="utf-8") as f:
        json.dump(sorted(r["question_id"] for r in dev), f, ensure_ascii=False, indent=2)
    with open(SPLITS / "test.json", "w", encoding="utf-8") as f:
        json.dump(sorted(r["question_id"] for r in test), f, ensure_ascii=False, indent=2)
    meta_text = json.dumps(meta, ensure_ascii=False, sort_keys=True)
    meta["sha256"] = hashlib.sha256(meta_text.encode("utf-8")).hexdigest()
    with open(SPLITS / "split_meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"Bộ gold: {len(records)} câu (35 ViFinQA chờ gắn nhãn + 15 bổ sung có đáp án)")
    print(f"Dev: {len(dev)} | Test: {len(test)} (thiếu bằng chứng: {n_test_unanswerable}, có đơn vị: {n_test_numeric})")
    print(f"  {QA_JSONL}")
    print(f"  {LABELS_CSV}")
    print(f"  {REVIEW_CSV}")
    print(f"  {SPLITS / 'dev.json'}, test.json, split_meta.json (sha256={meta['sha256'][:16]}...)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
