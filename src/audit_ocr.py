"""Audit chất lượng OCR cho corpus báo cáo tài chính ViFinQA.

Đây là minh chứng riêng của đề tài 6 (Mục 4.6.6: audit OCR). Script đo trên mỗi
báo cáo và trên mỗi trang:

- Cấu trúc: số trang, số bảng, bảng có parse được không.
- Bảng: số cột, ô trống, ô có số, tỷ lệ cột bị lệch (lỗi OCR làm dịch cột).
- Chữ: tỷ lệ ký tự tiếng Việt có dấu, ký tự lạ, chữ bị mất dấu.
- Số liệu: số có dấu phân cách nghìn, dấu âm trong ngoặc, tỷ lệ %, đơn vị
  tiền được nhận diện trong phần header của bảng.
- Văn bản: trang rỗng, trang không có bảng, độ dài bất thường.

Kết quả ghi:
- data/processed/ocr_audit.csv      (mỗi báo cáo một dòng)
- data/processed/ocr_audit_pages.csv (mỗi trang một dòng)
- report/ocr_audit.md               (bảng tổng hợp đọc được)

Ví dụ:
    python src/audit_ocr.py
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.preprocess.vifinqa_parser import is_number_like, parse_document  # noqa: E402

MANIFEST = ROOT / "data" / "processed" / "corpus_manifest.csv"
OUT_CSV = ROOT / "data" / "processed" / "ocr_audit.csv"
OUT_PAGES = ROOT / "data" / "processed" / "ocr_audit_pages.csv"
OUT_MD = ROOT / "report" / "ocr_audit.md"

VIETNAMESE_BASE = "aàáảãạăằắẳẵặâầấẩẫậbçdđeèéẻẽẹêềếểễệghiìíỉĩịjklmnoòóỏõọôồốổỗộơờớởỡợpqrstuùúủũụưừứửữựvxyỳýỷỹỵ"
VIETNAMESE_CHARS = set(VIETNAMESE_BASE) | set(VIETNAMESE_BASE.upper())

# Ký tự thường gặp do OCR sinh ra, không phải chữ tiếng Việt hợp lệ.
SUSPECT_CHARS = set("|~`^_¬°¥€£¤§¶†‡•…«»‹›×÷±≥≤≠√∞∫∑∏µαβγδεζηθλπσφωΩ")

# Ký tự trang trí, ví dụ dòng "○ ○ ○ ○" ở tiêu đề báo cáo do OCR sinh ra.
DECORATION_CHARS = set("○●◎◉◍◌◇◆□■▢▣▤▥▦▧▨▩▬▭▮▯△▲▽▼▽")

# Công thức LaTeX lọt vào văn bản OCR, không mang thông tin nghiệp vụ.
LATEX_RE = re.compile(r"\\\([^)]*\\\)|\$\$?[^$]*\$\$?")

# Đơn vị tiền và tỷ lệ thường xuất hiện trong header bảng.
UNIT_PATTERNS = [
    ("triệu đồng", r"triệu\s*vnd|triệu\s*đồng"),
    ("tỷ đồng", r"tỷ\s*vnd|tỷ\s*đồng"),
    ("nghìn tỷ đồng", r"nghìn\s*tỷ\s*đồng"),
    ("nghìn đồng", r"nghìn\s*đồng"),
    ("đồng", r"(?<!nghìn\s)(?<!tỷ\s)đồng"),
    ("%", r"%"),
    ("lần", r"\blần\b"),
]

NUMBER_RE = re.compile(r"-?\d[\d.,]*")
THOUSAND_SEP_RE = re.compile(r"\d\.\d{3}")
DECIMAL_RE = re.compile(r"\d,\d{1,2}$")
PAREN_NEG_RE = re.compile(r"^\(\d[\d.,]*\)$")


def ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def audit_text(text: str) -> dict:
    """Thống kê chất lượng văn bản thô của một trang."""
    chars = [c for c in text if not c.isspace()]
    total = len(chars)
    if total == 0:
        return {
            "n_chars": 0,
            "viet_ratio": 0.0,
            "suspect_ratio": 0.0,
            "no_diacritic_ratio": 0.0,
            "n_numbers": 0,
            "n_thousand_sep": 0,
            "n_decimal": 0,
            "n_paren_neg": 0,
            "n_percent": 0,
            "n_decoration": 0,
            "n_latex": 0,
            "units": "",
        }

    viet = sum(1 for c in chars if c in VIETNAMESE_CHARS)
    suspect = sum(1 for c in chars if c in SUSPECT_CHARS)
    # chữ cái không thuộc bảng chữ cái tiếng Việt, ví dụ do OCR đọc sai
    letters = [c for c in chars if c.isalpha()]
    no_diacritic = sum(
        1
        for c in letters
        if c.lower() in "aeiouy"
        and unicodedata.normalize("NFC", c) == c
    )
    # ký tự trang trí và ký hiệu toán học thừa, OCR hay sinh ra ở tiêu đề bảng
    n_decoration = sum(1 for c in chars if c in DECORATION_CHARS)
    n_latex = len(LATEX_RE.findall(text))

    numbers = NUMBER_RE.findall(text)
    n_thousand = sum(1 for n in numbers if THOUSAND_SEP_RE.search(n))
    n_decimal = sum(1 for n in numbers if DECIMAL_RE.search(n))
    n_paren_neg = sum(1 for n in numbers if PAREN_NEG_RE.match(n))
    n_percent = text.count("%")

    units = ",".join(name for name, pattern in UNIT_PATTERNS if re.search(pattern, text, re.IGNORECASE))

    return {
        "n_chars": total,
        "viet_ratio": ratio(viet, total),
        "suspect_ratio": ratio(suspect, total),
        "no_diacritic_ratio": ratio(no_diacritic, len(letters)),
        "n_numbers": len(numbers),
        "n_thousand_sep": n_thousand,
        "n_decimal": n_decimal,
        "n_paren_neg": n_paren_neg,
            "n_percent": n_percent,
            "n_decoration": n_decoration,
            "n_latex": n_latex,
            "units": units,
        }


def audit_table(table: list[list[str]]) -> dict:
    """Thống kê chất lượng một bảng đã parse."""
    n_rows = len(table)
    if n_rows == 0:
        return {"n_rows": 0, "n_cols": 0, "empty_ratio": 0.0, "number_ratio": 0.0, "ragged_ratio": 0.0, "has_header": 0}

    n_cols = max(len(r) for r in table)
    cells = [c for r in table for c in r]
    empty = sum(1 for c in cells if not c.strip())
    numeric = sum(1 for c in cells if is_number_like(c))
    # hàng có số ô khác số cột chuẩn, dấu hiệu bảng bị lệch cột khi OCR
    ragged = sum(1 for r in table if len(r) != n_cols)
    header = table[0] if table else []

    return {
        "n_rows": n_rows,
        "n_cols": n_cols,
        "empty_ratio": ratio(empty, len(cells)),
        "number_ratio": ratio(numeric, len(cells)),
        "ragged_ratio": ratio(ragged, n_rows),
        "has_header": int(any(re.search(r"\d{4}", c) for c in header) or any("đồng" in c.lower() or "vnd" in c.lower() for c in header)),
    }


def audit_document(path: Path) -> tuple[dict, list[dict]]:
    """Audit một báo cáo. Trả về (tổng hợp theo báo cáo, các dòng theo trang)."""
    raw = path.read_text(encoding="utf-8")
    pages = parse_document(raw)

    page_rows: list[dict] = []
    doc_tables: list[dict] = []
    for page in pages:
        tstats = audit_text(page["text"])
        table_stats = [audit_table(t) for t in page["tables"]]
        doc_tables.extend(table_stats)

        n_tables = len(table_stats)
        empty_cells = sum(1 for t in table_stats for c in t["n_rows"] * [0])  # giữ chỗ, tính bên dưới
        page_rows.append(
            {
                "page": page["page"],
                "n_chars": tstats["n_chars"],
                "n_tables": n_tables,
                "n_table_rows": sum(t["n_rows"] for t in table_stats),
                "avg_table_cols": round(sum(t["n_cols"] for t in table_stats) / n_tables, 2) if n_tables else 0,
                "max_table_cols": max((t["n_cols"] for t in table_stats), default=0),
                "empty_cell_ratio": round(sum(t["empty_ratio"] * t["n_rows"] * t["n_cols"] for t in table_stats) / max(1, sum(t["n_rows"] * t["n_cols"] for t in table_stats)), 4),
                "ragged_row_ratio": round(sum(t["ragged_ratio"] * t["n_rows"] for t in table_stats) / max(1, sum(t["n_rows"] for t in table_stats)), 4),
                "number_cell_ratio": round(sum(t["number_ratio"] * t["n_rows"] * t["n_cols"] for t in table_stats) / max(1, sum(t["n_rows"] * t["n_cols"] for t in table_stats)), 4),
                "header_with_unit": sum(t["has_header"] for t in table_stats),
                "viet_ratio": tstats["viet_ratio"],
                "suspect_ratio": tstats["suspect_ratio"],
                "no_diacritic_ratio": tstats["no_diacritic_ratio"],
                "n_numbers": tstats["n_numbers"],
                "n_thousand_sep": tstats["n_thousand_sep"],
                "n_decimal": tstats["n_decimal"],
                "n_paren_neg": tstats["n_paren_neg"],
                "n_percent": tstats["n_percent"],
                "n_decoration": tstats["n_decoration"],
                "n_latex": tstats["n_latex"],
                "units": tstats["units"],
                "is_empty": int(tstats["n_chars"] == 0),
            }
        )

    n_pages = len(page_rows)
    empty_pages = sum(r["is_empty"] for r in page_rows)
    no_table_pages = sum(1 for r in page_rows if r["n_tables"] == 0)
    tables_total = sum(r["n_tables"] for r in page_rows)
    header_ok = sum(r["header_with_unit"] for r in page_rows)

    summary = {
        "n_pages": n_pages,
        "n_tables": tables_total,
        "pages_empty": empty_pages,
        "pages_without_table": no_table_pages,
        "pages_with_unit_header": header_ok,
        "avg_page_chars": round(sum(r["n_chars"] for r in page_rows) / n_pages, 1) if n_pages else 0,
        "min_page_chars": min((r["n_chars"] for r in page_rows), default=0),
        "max_page_chars": max((r["n_chars"] for r in page_rows), default=0),
        "avg_viet_ratio": round(sum(r["viet_ratio"] for r in page_rows) / n_pages, 4) if n_pages else 0,
        "avg_suspect_ratio": round(sum(r["suspect_ratio"] for r in page_rows) / n_pages, 4) if n_pages else 0,
        "avg_no_diacritic_ratio": round(sum(r["no_diacritic_ratio"] for r in page_rows) / n_pages, 4) if n_pages else 0,
        "avg_empty_cell_ratio": round(sum(r["empty_cell_ratio"] for r in page_rows) / n_pages, 4) if n_pages else 0,
        "avg_ragged_row_ratio": round(sum(r["ragged_row_ratio"] for r in page_rows) / n_pages, 4) if n_pages else 0,
        "avg_number_cell_ratio": round(sum(r["number_cell_ratio"] for r in page_rows) / n_pages, 4) if n_pages else 0,
        "total_numbers": sum(r["n_numbers"] for r in page_rows),
        "total_thousand_sep": sum(r["n_thousand_sep"] for r in page_rows),
        "total_decimal": sum(r["n_decimal"] for r in page_rows),
        "total_paren_neg": sum(r["n_paren_neg"] for r in page_rows),
        "total_percent": sum(r["n_percent"] for r in page_rows),
        "total_decoration": sum(r["n_decoration"] for r in page_rows),
        "total_latex": sum(r["n_latex"] for r in page_rows),
        "unit_coverage": round(header_ok / tables_total, 4) if tables_total else 0.0,
    }
    return summary, page_rows


def main() -> int:
    p = argparse.ArgumentParser(description="Audit chat luong OCR cua corpus bao cao tai chinh.")
    p.add_argument("--manifest", default=str(MANIFEST))
    p.add_argument("--out-csv", default=str(OUT_CSV))
    p.add_argument("--out-pages", default=str(OUT_PAGES))
    p.add_argument("--out-md", default=str(OUT_MD))
    args = p.parse_args()

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"Khong tim thay manifest: {manifest_path}", file=sys.stderr)
        print("Hay chay: python src/select_corpus.py ... truoc", file=sys.stderr)
        return 2

    with open(manifest_path, encoding="utf-8", newline="") as f:
        manifest = list(csv.DictReader(f))

    summaries: list[dict] = []
    page_rows: list[dict] = []

    for row in manifest:
        path = ROOT / row["local_path"]
        summary, pages = audit_document(path)
        summary["document_id"] = row["document_id"]
        summary["company_id"] = row["company_id"]
        summary["fiscal_year"] = row["fiscal_year"]
        summary["report_version"] = row["report_version"]
        summary["local_path"] = row["local_path"]
        summaries.append(summary)
        for pr in pages:
            page_rows.append({"document_id": row["document_id"], **pr})

    out_csv = Path(args.out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(summaries[0].keys()))
        writer.writeheader()
        writer.writerows(summaries)

    out_pages = Path(args.out_pages)
    with open(out_pages, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(page_rows[0].keys()))
        writer.writeheader()
        writer.writerows(page_rows)

    write_markdown(Path(args.out_md), summaries, page_rows)

    print(f"Audit xong {len(summaries)} bao cao, {len(page_rows)} trang")
    print(f"  {out_csv}")
    print(f"  {out_pages}")
    print(f"  {OUT_MD}")
    return 0


def write_markdown(path: Path, summaries: list[dict], page_rows: list[dict]) -> None:
    """Ghi báo cáo audit OCR dạng markdown."""
    path.parent.mkdir(parents=True, exist_ok=True)

    total_pages = sum(s["n_pages"] for s in summaries)
    total_tables = sum(s["n_tables"] for s in summaries)

    lines: list[str] = []
    lines.append("# Audit chất lượng OCR - corpus báo cáo tài chính ViFinQA")
    lines.append("")
    lines.append(f"- Số báo cáo: **{len(summaries)}**")
    lines.append(f"- Tổng số trang: **{total_pages}**")
    lines.append(f"- Tổng số bảng OCR: **{total_tables}**")
    lines.append("- Script sinh báo cáo: `src/audit_ocr.py` (chạy lại được, đọc `data/processed/corpus_manifest.csv`)")
    lines.append("")

    lines.append("## 1. Chỉ số tổng hợp theo báo cáo")
    lines.append("")
    lines.append("| document_id | trang | bảng | trang rỗng | trang không bảng | bảng có header đơn vị | tỷ lệ ô số | tỷ lệ hàng lệch cột | tỷ lệ ký tự tiếng Việt |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for s in summaries:
        lines.append(
            f"| {s['document_id']} | {s['n_pages']} | {s['n_tables']} | {s['pages_empty']} | "
            f"{s['pages_without_table']} | {s['pages_with_unit_header']} | {s['avg_number_cell_ratio']:.4f} | "
            f"{s['avg_ragged_row_ratio']:.4f} | {s['avg_viet_ratio']:.4f} |"
        )
    lines.append("")

    lines.append("## 2. Độ dài trang")
    lines.append("")
    lines.append("| document_id | trung bình ký tự/trang | ngắn nhất | dài nhất |")
    lines.append("|---|---|---|---|")
    for s in summaries:
        lines.append(
            f"| {s['document_id']} | {s['avg_page_chars']} | {s['min_page_chars']} | {s['max_page_chars']} |"
        )
    lines.append("")

    lines.append("## 3. Chất lượng số liệu")
    lines.append("")
    lines.append("| document_id | tổng số | có dấu phân cách nghìn | số thập phân | số âm trong ngoặc | ký hiệu % |")
    lines.append("|---|---|---|---|---|---|")
    for s in summaries:
        lines.append(
            f"| {s['document_id']} | {s['total_numbers']} | {s['total_thousand_sep']} | "
            f"{s['total_decimal']} | {s['total_paren_neg']} | {s['total_percent']} |"
        )
    lines.append("")

    lines.append("## 4. Đơn vị tiền nhận diện được trong trang")
    lines.append("")
    unit_counter: Counter = Counter()
    for r in page_rows:
        for u in filter(None, r["units"].split(",")):
            unit_counter[u] += 1
    lines.append("| đơn vị | số trang chứa đơn vị |")
    lines.append("|---|---|")
    for u, c in unit_counter.most_common():
        lines.append(f"| {u} | {c} |")
    lines.append("")

    # các trang có vấn đề nổi bật
    problems = [
        r
        for r in page_rows
        if r["is_empty"] or r["ragged_row_ratio"] > 0.2 or r["suspect_ratio"] > 0.01
    ]
    lines.append("## 5. Trang có dấu hiệu lỗi OCR")
    lines.append("")
    if problems:
        lines.append("| document_id | trang | ký tự | bảng | ô rỗng | hàng lệch cột | ký tự lạ | đơn vị |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for r in problems[:80]:
            lines.append(
                f"| {r['document_id']} | {r['page']} | {r['n_chars']} | {r['n_tables']} | "
                f"{r['empty_cell_ratio']:.3f} | {r['ragged_row_ratio']:.3f} | {r['suspect_ratio']:.4f} | {r['units'] or '-'} |"
            )
        if len(problems) > 80:
            lines.append(f"\nCòn {len(problems) - 80} trang có dấu hiệu lỗi, xem `data/processed/ocr_audit_pages.csv`.")
    else:
        lines.append("Không phát hiện trang nào vượt ngưỡng lỗi đã đặt.")
    lines.append("")

    # báo cáo riêng cho trang rỗng, vì đây là lỗi ở file OCR nguồn
    empty_pages = [r for r in page_rows if r["is_empty"]]
    lines.append("## 6. Trang rỗng trong file OCR nguồn")
    lines.append("")
    if empty_pages:
        by_doc: dict[str, list[int]] = {}
        for r in empty_pages:
            by_doc.setdefault(r["document_id"], []).append(r["page"])
        lines.append("Các trang trống hoàn toàn, nằm liền nhau, là dấu hiệu OCR bỏ sót trang trong file nguồn.")
        lines.append("Đây là lỗi ở dữ liệu nguồn, không phải lỗi do script parse.")
        lines.append("")
        lines.append("| document_id | số trang rỗng | danh sách trang |")
        lines.append("|---|---|---|")
        for doc, pages in by_doc.items():
            lines.append(f"| {doc} | {len(pages)} | {', '.join(map(str, pages))} |")
        lines.append("")
        total_empty = len(empty_pages)
        lines.append(
            f"Tổng cộng **{total_empty} trang rỗng** trên tổng {len(page_rows)} trang "
            f"({total_empty / len(page_rows) * 100:.2f}%)."
        )
        lines.append("")
        lines.append("Bước xử lý đã áp dụng: giữ nguyên trong corpus để phản ánh đúng dữ liệu thực tế, "
                     "nhưng loại các trang này khỏi tập chunk dùng cho truy hồi và ghi nhận trong "
                     "`data/processed/ocr_audit_pages.csv` để nhóm có thể đối chiếu.")
    else:
        lines.append("Không có trang rỗng trong corpus.")
    lines.append("")

    lines.append("## 7. Nhiễu OCR không mang thông tin nghiệp vụ")
    lines.append("")
    total_dec = sum(r["n_decoration"] for r in page_rows)
    total_latex = sum(r["n_latex"] for r in page_rows)
    pages_dec = sum(1 for r in page_rows if r["n_decoration"] > 0)
    pages_latex = sum(1 for r in page_rows if r["n_latex"] > 0)
    lines.append("| loại nhiễu | tổng số lần xuất hiện | số trang bị ảnh hưởng |")
    lines.append("|---|---|---|")
    lines.append(f"| ký tự trang trí (○ ● ◎ ...) | {total_dec} | {pages_dec} |")
    lines.append(f"| công thức LaTeX | {total_latex} | {pages_latex} |")
    lines.append("")
    lines.append("Ký tự trang trí xuất hiện ở tiêu đề báo cáo, ví dụ dòng `○ ○ ○ ○ ◎ ○ ○ ○` "
                 "là đường kẻ trang trí bị OCR nhận thành ký tự. Công thức LaTeX lọt vào từ "
                 "bản thuyết minh toán học. Cả hai loại này không mang thông tin nghiệp vụ "
                 "và được loại bỏ khi sinh chunk.")
    lines.append("")

    lines.append("## 8. Cách đọc các chỉ số")
    lines.append("")
    lines.append("- `tỷ lệ ô số`: tỷ lệ ô trong bảng chứa giá trị số (bao gồm số âm trong ngoặc và số kèm %).")
    lines.append("- `tỷ lệ hàng lệch cột`: tỷ lệ hàng có số ô khác số cột chuẩn của bảng, dấu hiệu bảng bị vỡ khi OCR.")
    lines.append("- `tỷ lệ ký tự tiếng Việt`: tỷ lệ ký tự thuộc bảng chữ cái tiếng Việt, đánh giá việc giữ dấu.")
    lines.append("- `ký tự lạ`: ký tự không hợp lệ trong văn bản tài chính, thường do OCR nhập nhầm.")
    lines.append("- `bảng có header đơn vị`: bảng có hàng đầu chứa năm và đơn vị (triệu VND, tỷ đồng, ...), cần thiết cho việc chuẩn hóa đơn vị.")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
