"""Sinh data/processed/table_records.jsonl tu bang OCR bao cao tai chinh.

Moi hang bang thanh mot ban ghi co cau truc: cong ty, nam, ky, statement,
chi tieu, ma so, gia tri so da chuan hoa, don vi, trang, chunk nguon.
Giu dau tieng Viet (NFC), doc ma UTF-8, khong sua file goc trong data/raw.

Vi du:
    python src/build_table_records.py
    python src/build_table_records.py --out data/processed/table_records.jsonl
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.preprocess.table_extract import extract_records  # noqa: E402
from src.preprocess.vifinqa_parser import parse_document  # noqa: E402

MANIFEST = ROOT / "data" / "processed" / "corpus_manifest.csv"
OUT_DEFAULT = ROOT / "data" / "processed" / "table_records.jsonl"


def main() -> int:
    p = argparse.ArgumentParser(description="Trich ban ghi so co cau truc tu bang OCR.")
    p.add_argument("--manifest", default=str(MANIFEST))
    p.add_argument("--out", default=str(OUT_DEFAULT))
    args = p.parse_args()

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"Khong tim thay manifest: {manifest_path}", file=sys.stderr)
        return 2

    with open(manifest_path, encoding="utf-8", newline="") as f:
        manifest = list(csv.DictReader(f))

    records: list[dict] = []
    n_tables = 0
    for row in manifest:
        document_id = row["document_id"]
        company = row["company_id"]
        fiscal_year = int(row["fiscal_year"])
        report_version = row["report_version"]
        path = ROOT / row["local_path"]
        raw = path.read_text(encoding="utf-8")
        pages = parse_document(raw)
        for page in pages:
            if not page["tables"]:
                continue
            chunk_id = f"{document_id}#p{page['page']:03d}"
            for ti, table in enumerate(page["tables"], start=1):
                n_tables += 1
                recs = extract_records(
                    table,
                    page.get("text", ""),
                    company,
                    fiscal_year,
                    report_version,
                    document_id,
                    chunk_id,
                    page["page"],
                    ti,
                )
                records.extend(recs)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    by_doc: dict[str, int] = {}
    for r in records:
        by_doc[r["document_id"]] = by_doc.get(r["document_id"], 0) + 1
    print(f"Da trich {len(records)} ban ghi so tu {n_tables} bang cua {len(manifest)} bao cao")
    print(f"  ghi: {out}")
    for doc in sorted(by_doc)[:10]:
        print(f"  {doc:<28} {by_doc[doc]}")
    if len(by_doc) > 10:
        print(f"  ... va {len(by_doc) - 10} bao cao khac")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
