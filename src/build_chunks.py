"""Chuẩn hóa corpus báo cáo tài chính và sinh tập chunk cho truy hồi.

Đây là tầng "processed" của dữ liệu (Mục 5.1). Script đọc
`data/processed/corpus_manifest.csv`, parse từng báo cáo OCR thành trang và bảng,
loại trang rỗng, gắn ID ổn định và ghi ra `data/processed/chunks.jsonl`.

Nguyên tắc:
- Giữ nguyên dấu tiếng Việt, chuẩn Unicode NFC.
- Chuẩn hóa số: bỏ dấu phân cách nghìn, dấu âm trong ngoặc thành dấu âm.
- Chuẩn hóa đơn vị tiền theo bảng header, ghi vào trường `unit`.
- Không sửa file nguồn trong `data/raw/`.

Ví dụ:
    python src/build_chunks.py
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.preprocess.vifinqa_parser import nfc, parse_document  # noqa: E402

MANIFEST = ROOT / "data" / "processed" / "corpus_manifest.csv"
OUT_CHUNKS = ROOT / "data" / "processed" / "chunks.jsonl"

THOUSAND_RE = re.compile(r"(?<=\d)\.(?=\d{3}(?!\d))")
DECIMAL_COMMA_RE = re.compile(r"(?<=\d),(?=\d{1,2}(?!\d))")

# Ký tự trang trí do OCR nhận nhầm từ đường kẻ trang trí ở tiêu đề báo cáo.
DECORATION_RE = re.compile(r"[○●◎◉◍◌◇◆□■▢▣▤▥▦▧▨▩▬▭▮▯△▲▽▼]")

# Công thức LaTeX lọt vào văn bản OCR từ phần thuyết minh toán học.
LATEX_RE = re.compile(r"\\\([^)]*\\\)|\$\$?[^$]*\$\$?")

# Ký tự điều khiển và ký tự thay thế, loại bỏ trước khi lưu.
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

UNIT_FROM_HEADER = [
    ("nghìn tỷ đồng", r"nghìn\s*tỷ\s*đồng|nghìn\s*tỷ\s*vnd"),
    ("tỷ đồng", r"tỷ\s*đồng|tỷ\s*vnd"),
    ("triệu đồng", r"triệu\s*đồng|triệu\s*vnd"),
    ("nghìn đồng", r"nghìn\s*đồng"),
    ("đồng", r"đồng"),
]


def normalize_number(raw: str) -> str:
    """Chuẩn hóa chuỗi số về dạng số có dấu, dùng dấu chấm thập phân.

    - "1.234.567" -> "1234567"
    - "(983.237)" -> "-983237"
    - "3,2" -> "3.2"
    - "-" -> ""
    """
    value = raw.strip()
    if not value:
        return ""
    negative = False
    if value.startswith("(") and value.endswith(")"):
        negative = True
        value = value[1:-1].strip()
    if value in {"-", "--", "–", "—"}:
        return ""
    if value.endswith("%"):
        return value
    value = THOUSAND_RE.sub("", value)
    value = DECIMAL_COMMA_RE.sub(".", value)
    if value.startswith("-"):
        negative = not negative
        value = value[1:].strip()
    if negative:
        value = "-" + value
    return value


def detect_unit_from_table(table: list[list[str]]) -> str:
    """Suy ra đơn vị tiền từ hàng header của bảng."""
    if not table:
        return ""
    header = " ".join(table[0])
    for name, pattern in UNIT_FROM_HEADER:
        if re.search(pattern, header, re.IGNORECASE):
            return name
    return ""


def clean_noise(text: str) -> str:
    """Loại nhiễu OCR không mang thông tin nghiệp vụ.

    Giữ nguyên dấu tiếng Việt và mọi chữ số, chỉ bỏ ký tự trang trí, công thức
    LaTeX và ký tự điều khiển.
    """
    text = DECORATION_RE.sub(" ", text)
    text = LATEX_RE.sub(" ", text)
    text = CONTROL_RE.sub("", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r" ?\n ?", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def detect_unit_from_text(text: str) -> str:
    """Suy ra đơn vị tiền từ văn bản trang, dùng khi header bảng không nêu rõ."""
    for name, pattern in UNIT_FROM_HEADER:
        if re.search(pattern, text, re.IGNORECASE):
            return name
    return ""


def build_chunk_text(page: dict) -> str:
    """Ghép văn bản và bảng của một trang thành text để truy hồi."""
    parts: list[str] = []
    if page["text"]:
        parts.append(page["text"])
    for index, table in enumerate(page["tables"], start=1):
        rows = [" | ".join(cell for cell in row) for row in table]
        parts.append(f"[Bang {index}]\n" + "\n".join(rows))
    return nfc(clean_noise("\n".join(parts)))


def main() -> int:
    p = argparse.ArgumentParser(description="Chuan hoa corpus va sinh chunk cho truy hoi.")
    p.add_argument("--manifest", default=str(MANIFEST))
    p.add_argument("--out", default=str(OUT_CHUNKS))
    p.add_argument("--drop-empty-pages", action="store_true", default=True)
    args = p.parse_args()

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"Khong tim thay manifest: {manifest_path}", file=sys.stderr)
        return 2

    with open(manifest_path, encoding="utf-8", newline="") as f:
        manifest = list(csv.DictReader(f))

    chunks: list[dict] = []
    n_empty = 0
    n_tables = 0
    n_numbers = 0

    for row in manifest:
        path = ROOT / row["local_path"]
        raw = path.read_text(encoding="utf-8")
        pages = parse_document(raw)

        for page in pages:
            if args.drop_empty_pages and not page["text"] and not page["tables"]:
                n_empty += 1
                continue

            unit = ""
            for table in page["tables"]:
                found = detect_unit_from_table(table)
                if found:
                    unit = found
                    break
            if not unit:
                # dự phòng: dò đơn vị trong toàn bộ văn bản trang
                unit = detect_unit_from_text(page["text"])

            chunk_id = f"{row['document_id']}#p{page['page']:03d}"
            text = build_chunk_text(page)
            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "document_id": row["document_id"],
                    "company_id": row["company_id"],
                    "fiscal_year": int(row["fiscal_year"]),
                    "report_version": row["report_version"],
                    "page": page["page"],
                    "n_tables": page["n_tables"],
                    "unit": unit,
                    "text": text,
                    "text_chars": len(text),
                    "local_path": row["local_path"],
                }
            )
            n_tables += page["n_tables"]
            n_numbers += sum(1 for c in text if c.isdigit())

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    print(f"Da sinh {len(chunks)} chunk tu {len(manifest)} bao cao")
    print(f"  bo qua {n_empty} trang rong")
    print(f"  tong {n_tables} bang, {n_numbers} ky tu so")
    print(f"  ghi: {out}")

    by_doc: dict[str, int] = {}
    for c in chunks:
        by_doc[c["document_id"]] = by_doc.get(c["document_id"], 0) + 1
    print("\nSo chunk theo bao cao:")
    for doc, count in sorted(by_doc.items()):
        print(f"  {doc:<28} {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
