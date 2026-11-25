"""Trích bản ghi số có cấu trúc từ bảng OCR báo cáo tài chính.

Mỗi hàng bảng được gán: tên chỉ tiêu, đơn vị, kỳ báo cáo, công ty, năm,
loại báo cáo, statement, giá trị số đã chuẩn hóa. Giữ dấu tiếng Việt (NFC).

Đầu vào: file OCR gốc có thẻ <table> (qua src/preprocess/vifinqa_parser).
Đầu ra: data/processed/table_records.jsonl, mỗi dòng một bản ghi:
  company, year, period_label, statement, metric, metric_code,
  value, unit, value_raw, page, source_chunk_id, document_id,
  report_version, confidence.
"""

from __future__ import annotations

import re
import unicodedata

YEAR_RE = re.compile(r"\b(20[0-2]\d)\b")
YEAR_LOOSE_RE = re.compile(r"(20[0-2]\d)")
DATE_RE = re.compile(r"\b(\d{1,2})[/.](\d{1,2})[/.](20[0-2]\d)\b")
CODE_RE = re.compile(r"^\d{2,3}[a-z]?$", re.IGNORECASE)
NUM_CORE_RE = re.compile(r"^\(?-?[\d.\s,]+-?\)?%?$")

UNIT_PATTERNS: list[tuple[str, str]] = [
    ("nghìn tỷ đồng", r"nghìn\s*tỷ\s*(đồng|vnd)"),
    ("trăm tỷ đồng", r"trăm\s*tỷ\s*(đồng|vnd)"),
    ("tỷ đồng", r"tỷ\s*(đồng|vnd)"),
    ("triệu đồng", r"triệu\s*(đồng|vnd)"),
    ("nghìn đồng", r"nghìn\s*(đồng|vnd)"),
    ("nghìn VND", r"nghìn\s*vnd"),
    ("VND", r"vnd"),
    ("đồng", r"đồng"),
    ("%", r"%"),
]

STATEMENT_PATTERNS: list[tuple[str, str]] = [
    ("balance_sheet", r"cân\s*đối\s*kế\s*toán|bảng\s*cân\s*đối|mẫu\s*số\s*b\s*01"),
    ("income_statement", r"kết\s*quả.*kinh\s*doanh|kết\s*quả\s*hoạt\s*động|mẫu\s*số\s*b\s*02"),
    ("cash_flow", r"lưu\s*chuyển\s*tiền|lưu\s*chuyen.*tien|mẫu\s*số\s*b\s*03"),
]


def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text or "")


def clean_metric(text: str) -> str:
    text = nfc(text or "")
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"^[\-:;.\u2013\u2014]+\s*", "", text)
    return text


def detect_unit(text: str) -> str:
    low = (text or "").lower()
    # Ưu tiên dòng "đơn vị tính: ..." vì trang có thể nhắc tỷ đồng trong lời văn.
    m = re.search(r"đơn vị[^:\n]{0,30}[:：]\s*([^\n,;|]+)", low)
    if not m:
        m = re.search(r"đơn vị tính\s+([^\n,;|]+)", low)
    if m:
        frag = m.group(1)
        for name, pat in UNIT_PATTERNS:
            if re.search(pat, frag):
                if name == "nghìn VND":
                    return "nghìn đồng"
                if name == "VND":
                    return "đồng"
                return name
    for name, pat in UNIT_PATTERNS:
        if re.search(pat, low):
            if name == "nghìn VND":
                return "nghìn đồng"
            if name == "VND":
                return "đồng"
            return name
    return ""


def detect_statement(page_text: str) -> str:
    low = (page_text or "").lower()
    for name, pat in STATEMENT_PATTERNS:
        if re.search(pat, low):
            return name
    return "other"


def normalize_table_number(raw: str) -> float | None:
    """Chuẩn hóa số bảng: 1.234.567 -> 1234567, (983) -> -983, 3,2 -> 3.2."""
    if raw is None:
        return None
    value = str(raw).strip().replace(" ", " ").replace("\xa0", " ")
    value = re.sub(r"\s+", "", value)
    if not value or value in {"-", "--", "x", "X", "\u2013", "\u2014"}:
        return None
    negative = False
    if value.startswith("(") and value.endswith(")"):
        negative = True
        value = value[1:-1]
    is_pct = value.endswith("%")
    if is_pct:
        value = value[:-1]
    # Phần trăm trong báo cáo VN dùng dấu phẩy thập phân: 99,988% là 99.988%.
    if is_pct and "," in value and "." not in value:
        value = value.replace(",", ".")
        value = re.sub(r"\s+", "", value)
        if not re.search(r"\d", value):
            return None
        try:
            num = float(value)
        except ValueError:
            return None
        if negative:
            num = -num
        return num
    if not re.search(r"\d", value):
        return None
    has_dot = "." in value
    has_comma = "," in value
    if has_dot and has_comma:
        if value.rfind(",") > value.rfind("."):
            value = value.replace(".", "").replace(",", ".")
        else:
            value = value.replace(",", "")
    elif has_comma:
        parts = value.split(",")
        if len(parts) > 1 and all(len(p) == 3 for p in parts[1:]) and len(parts[0]) <= 3:
            value = "".join(parts)
        elif len(parts) == 2 and 1 <= len(parts[1]) <= 2:
            value = parts[0].replace(",", "") + "." + parts[1]
        else:
            joined = "".join(parts)
            if len(parts) == 2 and len(parts[1]) == 3 and len(parts[0]) <= 4:
                value = joined
            else:
                value = parts[0] + ("." + parts[1] if len(parts) == 2 else "".join(parts[1:]))
    elif has_dot:
        if re.fullmatch(r"\d{1,3}(\.\d{3})+", value):
            value = value.replace(".", "")
        elif value.count(".") > 1:
            head, tail = value.rsplit(".", 1)
            head = head.replace(".", "")
            value = head + "." + tail
    if value.startswith("-"):
        negative = not negative
        value = value[1:]
    value = re.sub(r"[^0-9.]", "", value)
    if not value or value == ".":
        return None
    try:
        num = float(value)
    except ValueError:
        return None
    if negative:
        num = -num
    if is_pct:
        return num
    return num


def is_number_like(cell: str) -> bool:
    value = (cell or "").strip()
    if not value:
        return False
    core = value.replace(" ", "")
    return bool(NUM_CORE_RE.match(core)) and bool(re.search(r"\d", core))


def is_code_cell(cell: str) -> bool:
    return bool(CODE_RE.match((cell or "").strip()))


def clean_period_label(text: str) -> str:
    """Tách đơn vị tiền tệ dính kèm khỏi nhãn kỳ header OCR.

    Ví dụ: "31/12/2023VND" -> "31/12/2023", "2023Nghìn VND" -> "2023",
    "2021VND'000" -> "2021". Đơn vị nằm ở cột "Đơn vị" riêng, không
    được lẫn vào cột "Kỳ" trên demo.
    """
    t = nfc(text or "").strip()
    t = re.sub(
        r"\s*(nghìn|nghin|trăm|tram|triệu|trieu|tỷ|ty)?\s*(vnd|vnđ|đồng|dong)\s*('000|’000)?\s*$",
        "",
        t,
        flags=re.IGNORECASE,
    )
    t = re.sub(r"\s*('000|’000)\s*$", "", t)
    return t.strip(" ,;|")


def header_years(header: list[str]) -> list[tuple[int, str]]:
    """Tìm cột kỳ báo cáo từ header: trả về list (col_index, period_label)."""
    out: list[tuple[int, str]] = []
    for idx, cell in enumerate(header):
        text = clean_period_label(cell or "")
        if not text:
            continue
        m = DATE_RE.search(text)
        if m:
            out.append((idx, m.group(0).strip()))
            continue
        m2 = YEAR_RE.search(text)
        if m2:
            out.append((idx, m2.group(1)))
            continue
        low = text.lower()
        if "vnd" in low or "đồng" in low or text.strip().isdigit():
            continue
    return out


def detect_header_count(norm: list[list[str]]) -> int:
    """Đếm số dòng header đầu bảng (1-3 dòng, không chứa số liệu lớn)."""
    if not norm:
        return 0
    max_h = min(3, len(norm))
    count = 1
    for i in range(1, max_h):
        text = " ".join(c or "" for c in norm[i])
        low = text.lower()
        has_period = bool(YEAR_RE.search(text) or DATE_RE.search(text))
        has_kw = any(
            k in low
            for k in [
                "mã số", "ma so", "thuyết minh", "thuyet minh", "vnd",
                "đồng", "dong", "năm", "nam", "ngày", "ngay",
                "tháng", "thang", "tuyệt đối", "tuyet doi", "tương đối",
                "tuong doi", "chênh lệch", "chenh lech", "chỉ tiêu",
                "chi tieu", "stt",
            ]
        )
        # Dòng kiểu (1) | (2) | (5)=(3)-(4): chỉ mục cột, không phải số liệu.
        idx_cells = [
            c for c in norm[i]
            if re.match(r"^\(?\d+\)?(\s*=\s*\(?\d+.*\)?)?$", (c or "").strip())
        ]
        has_col_index = len(idx_cells) >= 2
        large = 0
        for cell in norm[i]:
            if not is_number_like(cell):
                continue
            num = normalize_table_number(cell)
            if num is not None and abs(num) >= 1000:
                large += 1
        if (has_period or has_kw or has_col_index) and large == 0:
            count = i + 1
        else:
            break
    return max(1, count)


def collect_periods(norm: list[list[str]], header_count: int) -> list[str]:
    """Gom nhãn kỳ (chứa năm/ngày) từ các dòng header theo thứ tự trái-phải."""
    periods: list[str] = []
    for r in range(min(header_count, len(norm))):
        for cell in norm[r]:
            text = clean_period_label((cell or "").strip())
            if not text:
                continue
            if YEAR_LOOSE_RE.search(text) or DATE_RE.search(text):
                if text not in periods:
                    periods.append(text)
    return periods


def column_unit(norm: list[list[str]], header_count: int, col: int) -> str:
    """Đơn vị riêng từng cột: ưu tiên dấu % trong dữ liệu, rồi mới đoán header."""
    for r in range(header_count, min(header_count + 5, len(norm))):
        cell = (norm[r][col] or "").strip() if col < len(norm[r]) else ""
        if cell.endswith("%"):
            return "%"
    frag = " | ".join((norm[r][col] or "") for r in range(min(header_count, len(norm))))
    u = detect_unit(frag)
    if u:
        return u
    return ""


def find_value_columns(table: list[list[str]]) -> tuple[list[tuple[int, str, str]], str, int]:
    """Xác định cột giá trị, đơn vị chung và số dòng header của bảng.

    Trả về cols là list (col_index, period_label, col_unit) để tách
    cột phần trăm và cột VND trong cùng bảng.
    """
    if not table:
        return [], "", 1
    width = max(len(r) for r in table)
    norm = [r + [""] * (width - len(r)) for r in table]
    header_count = detect_header_count(norm)
    header_text = " | ".join(" ".join(norm[r][c] or "" for r in range(header_count)) for c in range(width))
    unit = detect_unit(header_text)
    if not unit:
        for row in norm[: max(header_count, 3)]:
            found = detect_unit(" | ".join(row))
            if found:
                unit = found
                break
    periods = collect_periods(norm, header_count)
    # Nhãn kỳ theo từng cột: ưu tiên cột có header chứa năm/ngày.
    col_labels: list[str] = []
    for c in range(width):
        label = ""
        for r in range(header_count):
            cell = clean_period_label((norm[r][c] or "").strip())
            if cell and (YEAR_LOOSE_RE.search(cell) or DATE_RE.search(cell)):
                label = cell
                break
        col_labels.append(label)
    num_counts = [0] * width
    large_counts = [0] * width
    pct_counts = [0] * width
    for row in norm[header_count:]:
        for c, cell in enumerate(row):
            if is_number_like(cell):
                num_counts[c] += 1
                if (cell or "").strip().endswith("%"):
                    pct_counts[c] += 1
                num = normalize_table_number(cell)
                if num is not None and abs(num) >= 1000:
                    large_counts[c] += 1
    data_rows = max(1, len(norm) - header_count)
    threshold = max(1, data_rows // 3)
    # Loại cột mã số (01, 10, 20...): nhiều số nhưng hầu hết < 1000.
    # Giữ cột phần trăm dù giá trị nhỏ (99,988%).
    value_cands = [
        c for c, n in enumerate(num_counts)
        if n >= threshold and (
            large_counts[c] >= max(1, threshold // 2)
            or pct_counts[c] >= max(1, threshold // 2)
        )
    ]
    numeric_cols = value_cands if value_cands else [
        c for c, n in enumerate(num_counts) if n >= threshold
    ]
    def _col_unit(c: int) -> str:
        return column_unit(norm, header_count, c) or unit
    # Trước hết giữ cột số có nhãn kỳ năm/ngày (loại cột chênh lệch tuyệt đối/tương đối).
    period_cols = [c for c in numeric_cols if col_labels[c]]
    cols: list[tuple[int, str, str]] = []
    if period_cols:
        # Giữ tất cả cột có nhãn kỳ riêng (VD bảng HPG có 6 cột số:
        # 2 cột % và 1 cột VND cho mỗi kỳ). Không cắt theo len(periods).
        cols = [(c, col_labels[c], _col_unit(c)) for c in sorted(period_cols)]
    elif numeric_cols and periods:
        # Header bị lệch cột (kỳ năm ở cột khác cột giá trị): gán theo thứ tự
        # trái-phải, cột giá trị thứ i nhận kỳ thứ i.
        ordered = sorted(numeric_cols)
        if len(ordered) == len(periods):
            cols = [(c, p, _col_unit(c)) for c, p in zip(ordered, periods)]
        elif len(ordered) > len(periods):
            cols = [(c, p, _col_unit(c)) for c, p in zip(ordered[: len(periods)], periods)]
        else:
            cols = [(c, col_labels[c] or p, _col_unit(c)) for c, p in zip(ordered, periods)]
    else:
        cols_idx = numeric_cols[:2] if len(numeric_cols) > 2 else numeric_cols
        if cols_idx and periods and len(periods) == len(cols_idx):
            cols = [(c, p, _col_unit(c)) for c, p in zip(cols_idx, periods)]
        elif cols_idx and periods and len(periods) >= len(cols_idx):
            cols = [(c, p, _col_unit(c)) for c, p in zip(cols_idx, periods[: len(cols_idx)])]
        else:
            for c in cols_idx:
                label = ""
                for r in range(header_count):
                    cell = clean_period_label((norm[r][c] or "").strip())
                    if cell and (YEAR_LOOSE_RE.search(cell) or DATE_RE.search(cell)):
                        label = cell
                        break
                cols.append((c, label or f"col_{c}", _col_unit(c)))
    return cols, unit, header_count


def metric_and_code(row: list[str], value_cols: set[int]) -> tuple[str, str]:
    """Chọn ô chỉ tiêu (text dài nhất) và mã số trong hàng."""
    code = ""
    best = ""
    for idx, cell in enumerate(row):
        if idx in value_cols:
            continue
        text = (cell or "").strip()
        if not text:
            continue
        if is_code_cell(text) and not code:
            code = text
            continue
        if is_number_like(text):
            continue
        if len(text) > len(best):
            best = text
    return clean_metric(best), code


def extract_records(
    table: list[list[str]],
    page_text: str,
    company: str,
    fiscal_year: int,
    report_version: str,
    document_id: str,
    chunk_id: str,
    page: int,
    table_index: int,
) -> list[dict]:
    if not table or len(table) < 2:
        return []
    width = max(len(r) for r in table)
    norm = [list(r) + [""] * (width - len(r)) for r in table]
    value_cols, unit, header_count = find_value_columns(norm)
    if not value_cols:
        return []
    if not unit:
        unit = detect_unit(page_text or "")
    statement = detect_statement(page_text or "")
    val_set = {c for c, _, _ in value_cols}
    records: list[dict] = []
    start = max(1, int(header_count))
    for row in norm[start:]:
        metric, code = metric_and_code(row, val_set)
        if not metric or len(metric) < 2:
            continue
        if metric.isdigit():
            continue
        for col, period_label, col_unit in value_cols:
            raw = (row[col] if col < len(row) else "").strip()
            if not raw or not is_number_like(raw):
                continue
            value = normalize_table_number(raw)
            if value is None:
                continue
            year_m = YEAR_LOOSE_RE.findall(period_label or "")
            if year_m:
                # Nhãn kỳ dạng NĐTC 2019-2020: lấy năm cuối (năm tài chính).
                year = int(year_m[-1])
            elif DATE_RE.search(period_label or ""):
                year = int(DATE_RE.findall(period_label)[-1][2])
            else:
                year = int(fiscal_year)
            conf = 0.7
            if code:
                conf = 0.93
            elif len(metric) >= 6:
                conf = 0.85
            cell_unit = (col_unit or unit or "").strip()
            if not cell_unit:
                cell_unit = detect_unit(page_text or "")
                conf -= 0.1
            records.append(
                {
                    "company": company,
                    "year": year,
                    "period_label": period_label,
                    "statement": statement,
                    "metric": metric,
                    "metric_code": code,
                    "value": value,
                    "unit": cell_unit,
                    "value_raw": raw,
                    "page": page,
                    "table_index": table_index,
                    "source_chunk_id": chunk_id,
                    "document_id": document_id,
                    "report_version": report_version,
                    "fiscal_year": int(fiscal_year),
                    "confidence": round(max(0.0, min(0.99, conf)), 2),
                }
            )
    return records
