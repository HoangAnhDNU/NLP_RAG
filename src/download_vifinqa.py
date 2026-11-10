"""Tải dataset ViFinQA từ Hugging Face.

Repo: https://huggingface.co/datasets/AIGuruTinix/ViFinQA

Ví dụ:
    # chỉ câu hỏi + danh sách mã CK (rất nhẹ, vài trăm KB)
    python tools/download_vifinqa.py --mode questions

    # thêm báo cáo tài chính của 3 doanh nghiệp, các năm 2020-2024
    python tools/download_vifinqa.py --mode corpus --tickers HPG VCB ACB --years 2020 2021 2022 2023 2024

    # tải toàn bộ (~380 MB)
    python tools/download_vifinqa.py --mode full
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ID = "AIGuruTinix/ViFinQA"
REPO_TYPE = "dataset"
ROOT = Path(__file__).resolve().parents[1] / "data" / "raw" / "vifinqa"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Download ViFinQA from Hugging Face.")
    p.add_argument(
        "--mode",
        choices=["questions", "corpus", "full"],
        default="questions",
        help="questions: chỉ questions.jsonl + code_stock.csv; corpus: thêm báo cáo tài chính theo ticker/năm; full: tất cả",
    )
    p.add_argument("--tickers", nargs="*", default=[], help="mã cổ phiếu, ví dụ HPG VCB")
    p.add_argument("--years", nargs="*", default=[], help="năm, ví dụ 2020 2021")
    p.add_argument(
        "--revision",
        default="main",
        help="revision của dataset repo (mặc định main). Nên ghi lại sha trong data_card.md",
    )
    p.add_argument("--out", default=str(ROOT), help="thư mục đích")
    return p.parse_args()


def main() -> int:
    from huggingface_hub import snapshot_download

    args = parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    allow: list[str] | None = None
    if args.mode == "questions":
        allow = ["questions/questions.jsonl", "code_stock.csv", "README.md"]
    elif args.mode == "corpus":
        if not args.tickers:
            print("Thiếu --tickers cho mode corpus.", file=sys.stderr)
            return 2
        allow = ["questions/questions.jsonl", "code_stock.csv", "README.md"]
        for ticker in args.tickers:
            t = ticker.upper()
            if args.years:
                for year in args.years:
                    allow.append(f"financial_statements/{t}/{year}/*")
            else:
                allow.append(f"financial_statements/{t}/*")

    print(f"Đang tải {REPO_ID} (revision={args.revision}) vào {out}")
    path = snapshot_download(
        repo_id=REPO_ID,
        repo_type=REPO_TYPE,
        revision=args.revision,
        local_dir=str(out),
        allow_patterns=allow,
        max_workers=4,
    )
    print(f"Xong. Snapshot tại: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
