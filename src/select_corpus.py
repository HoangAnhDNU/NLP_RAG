"""Chọn corpus báo cáo tài chính và ghi manifest.

Theo đề tài 6 của hướng dẫn BTL CSC4007: giới hạn một corpus khả thi,
khuyến nghị 10-20 báo cáo của 02-04 doanh nghiệp qua một số năm.

Script này chọn bộ báo cáo theo cấu hình, kiểm tra file tồn tại và đủ trang,
rồi ghi data/processed/corpus_manifest.csv với metadata truy vết được.

Ví dụ:
    python src/select_corpus.py --tickers HPG VCB ACB --years 2020 2021 2022 2023 2024
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ID = "AIGuruTinix/ViFinQA"
REPO_URL = f"https://huggingface.co/datasets/{REPO_ID}"
REPO_REVISION = "0450088ab22ec946f04f097586967ca405955b3b"

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "vifinqa"
OUT_DIR = ROOT / "data" / "processed"

MIN_PAGES = 10


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def find_report(ticker: str, year: int, version: str) -> Path | None:
    base = RAW / "financial_statements" / ticker / str(year)
    if not base.is_dir():
        return None
    folder = f"{ticker}_financial_statements_{year}_{version}"
    directory = base / folder
    if not directory.is_dir():
        return None
    candidates = sorted(directory.glob("*_extracted.txt"))
    return candidates[0] if candidates else None


def main() -> int:
    p = argparse.ArgumentParser(description="Chon corpus bao cao tai chinh Va ghi manifest.")
    p.add_argument("--tickers", nargs="+", required=True, help="ma co phieu, ví dụ HPG VCB ACB")
    p.add_argument("--years", nargs="+", required=True, type=int, help="cac nam, ví dụ 2020 2021 2022")
    p.add_argument(
        "--versions",
        nargs="+",
        default=["consolidated"],
        choices=["consolidated", "separate"],
        help="loai ban bao cao",
    )
    p.add_argument("--out", default=str(OUT_DIR / "corpus_manifest.csv"))
    args = p.parse_args()

    rows: list[dict] = []
    missing: list[str] = []
    for ticker in args.tickers:
        t = ticker.upper()
        for year in args.years:
            for version in args.versions:
                path = find_report(t, year, version)
                if path is None:
                    missing.append(f"{t}_{year}_{version}")
                    continue
                raw = path.read_text(encoding="utf-8")
                n_pages = raw.count("===== PAGE ")
                rel = path.relative_to(ROOT).as_posix()
                rows.append(
                    {
                        "document_id": f"{t}_{year}_{version}",
                        "company_id": t,
                        "fiscal_year": year,
                        "report_version": version,
                        "source_name": REPO_ID,
                        "source_url": f"{REPO_URL}/blob/{REPO_REVISION}/financial_statements/{t}/{year}/",
                        "source_version": REPO_REVISION,
                        "retrieved_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                        "published_at": "",  # ngày phát hành thực: chưa xác minh, để trống
                        "language": "vi",
                        "original_category": "financial_statement_ocr",
                        "task_label": "financial_report_chunk",
                        "license_status": "unknown_verify_with_teacher",
                        "split": "corpus",
                        "local_path": rel,
                        "n_pages": n_pages,
                        "n_chars": len(raw),
                        "sha256": file_sha256(path),
                        "notes": "",
                    }
                )

    if missing:
        print("Thieu file cho cac cap (ticker_nam_version):", ", ".join(missing), file=sys.stderr)

    thin = [r["document_id"] for r in rows if r["n_pages"] < MIN_PAGES]
    if thin:
        print(f"Canh bao: bao co it trang (<{MIN_PAGES}): {', '.join(thin)}", file=sys.stderr)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys()) if rows else ["document_id"]
    with open(out, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Da chon {len(rows)} bao cao -> {out}")
    for r in rows:
        print(f"  {r['document_id']:<28} trang={r['n_pages']:<4} ky tu={r['n_chars']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
