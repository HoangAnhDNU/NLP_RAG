"""Dựng hồ sơ dữ liệu mục 1.3: data_manifest.csv, kiểm tra data/splits.

Đọc:
- data/processed/corpus_manifest.csv (40 báo cáo, có sha256 và retrieved_at)
- data/annotations/qa_gold.jsonl (bộ gold v2, có split dev/test)

Ghi:
- data/data_manifest.csv với đúng 13 cột chuẩn:
  item_id, document_id, source_name, source_url, source_version,
  retrieved_at, published_at, language, original_category, task_label,
  license_status, split, notes

Kiểm tra:
- data/splits/dev.json, test.json, split_meta.json tồn tại và khớp bộ gold.

Quy tắc:
- published_at chỉ ghi ngày phát hành thực từ nguồn. Nguồn ViFinQA không
  công bố ngày phát hành từng báo cáo nên luôn để trống, không suy ra từ
  ID hay ngày crawl.
- original_category (nhãn gốc của nguồn) và task_label (nhãn nhiệm vụ nhóm
  dùng) không đánh đồng, ghi riêng hai cột.

Ví dụ:
    python src/build_data_docs.py
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
ANNOT = ROOT / "data" / "annotations"
DATA = ROOT / "data"
SPLITS_DIR = ROOT / "data" / "splits"

MANIFEST_FIELDS = [
    "item_id",
    "document_id",
    "source_name",
    "source_url",
    "source_version",
    "retrieved_at",
    "published_at",
    "language",
    "original_category",
    "task_label",
    "license_status",
    "split",
    "notes",
]


def main() -> int:
    corpus = list(csv.DictReader(open(PROCESSED / "corpus_manifest.csv", encoding="utf-8")))
    gold = [json.loads(line) for line in open(ANNOT / "qa_gold.jsonl", encoding="utf-8")]

    rows: list[dict] = []
    for r in corpus:
        rows.append(
            {
                "item_id": r["document_id"],
                "document_id": r["document_id"],
                "source_name": r["source_name"],
                "source_url": r["source_url"],
                "source_version": r["source_version"],
                "retrieved_at": r["retrieved_at"],
                "published_at": "",
                "language": r["language"],
                "original_category": r["original_category"],
                "task_label": r["task_label"],
                "license_status": r["license_status"],
                "split": "corpus",
                "notes": (
                    f"company={r['company_id']}; year={r['fiscal_year']}; "
                    f"version={r['report_version']}; pages={r['n_pages']}; "
                    f"sha256={r['sha256']}; local={r['local_path']}"
                ),
            }
        )

    for g in gold:
        if g.get("source") == "vifinqa":
            source_name = "AIGuruTinix/ViFinQA"
            source_url = "https://huggingface.co/datasets/AIGuruTinix/ViFinQA/blob/main/questions/questions.jsonl"
            source_version = "0450088ab22ec946f04f097586967ca405955b3b"
            original_category = "vifinqa_question"
        else:
            source_name = "synthetic-by-team"
            source_url = ""
            source_version = "annotation-guideline-v0.1"
            original_category = "synthetic_question"
        doc = g.get("report_id") or f"{g.get('company_id')}_{g.get('fiscal_year')}"
        rows.append(
            {
                "item_id": g["question_id"],
                "document_id": doc,
                "source_name": source_name,
                "source_url": source_url,
                "source_version": source_version,
                "retrieved_at": "2026-11-10",
                "published_at": "",
                "language": "vi",
                "original_category": original_category,
                "task_label": "qa_gold",
                "license_status": "unknown_verify_with_teacher",
                "split": g.get("split", ""),
                "notes": (
                    f"answer_type={g.get('answer_type')}; unit={g.get('unit')}; "
                    f"needs_more_evidence={g.get('needs_more_evidence')}; "
                    f"review={g.get('review_status')}"
                ),
            }
        )

    out = DATA / "data_manifest.csv"
    with open(out, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    SPLITS_DIR.mkdir(parents=True, exist_ok=True)
    meta = json.loads(open(SPLITS_DIR / "split_meta.json", encoding="utf-8").read())
    dev_ids = json.loads(open(SPLITS_DIR / "dev.json", encoding="utf-8").read())
    test_ids = json.loads(open(SPLITS_DIR / "test.json", encoding="utf-8").read())
    gold_ids = {g["question_id"] for g in gold}
    assert set(dev_ids) | set(test_ids) == gold_ids, "dev/test trong splits phai khop gold"
    assert len(dev_ids) == meta["n_dev"] and len(test_ids) == meta["n_test"]

    n_corpus = sum(1 for r in rows if r["split"] == "corpus")
    n_dev = sum(1 for r in rows if r["split"] == "dev")
    n_test = sum(1 for r in rows if r["split"] == "test")
    print(f"Đã ghi {len(rows)} dòng -> {out} (corpus={n_corpus}, dev={n_dev}, test={n_test})")
    missing = [n for n in ("dev.json", "test.json", "split_meta.json") if not (SPLITS_DIR / n).is_file()]
    assert not missing, f"Thiếu file splits: {missing}"
    print(f"Splits chuẩn đã đóng băng tại {SPLITS_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
