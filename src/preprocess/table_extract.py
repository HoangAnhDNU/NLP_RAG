"""Trich ban ghi so co cau truc tu bang OCR bao cao tai chinh.

Moi hang bang duoc gan: ten chi tieu, don vi, ky bao cao, cong ty, nam,
loai bao cao, statement, gia tri so da chuan hoa. Giu dau tieng Viet (NFC).

Dau vao: file OCR goc co the <table> (qua src/preprocess/vifinqa_parser).
Dau ra: data/processed/table_records.jsonl, moi dong mot ban ghi:
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
    # Uu tien dong "don vi tinh: ..." vi trang co the nhac ty dong trong loi van.
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
    """Chuan hoa so bang: 1.234.567 -> 1234567, (983) -> -983, 3,2 -> 3.2."""
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
    # Percent trong bao cao VN dung dau phay thap phan: 99,988% la 99.988%.
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


def header_years(header: list[str]) -> list[tuple[int, str]]:
    """Tim cot ky bao cao tu header: tra ve list (col_index, period_label)."""
    out: list[tuple[int, str]] = []
    for idx, cell in enumerate(header):
        text = cell or ""
        m = DATE_RE.search(text)
        if m:
            year = int(m.group(3))
            out.append((idx, text.strip()))
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
    """Dem so dong header dau bang (1-3 dong, khong chua so lieu lon)."""
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
        # Dong kieu (1) | (2) | (5)=(3)-(4): chi muc cot, khong phai so lieu.
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
    """Gom nhan ky (chua nam/ngay) tu cac dong header theo thu tu trai-phai."""
    periods: list[str] = []
    for r in range(min(header_count, len(norm))):
        for cell in norm[r]:
            text = (cell or "").strip()
            if not text:
                continue
            if YEAR_LOOSE_RE.search(text) or DATE_RE.search(text):
                if text not in periods:
                    periods.append(text)
    return periods


def column_unit(norm: list[list[str]], header_count: int, col: int) -> str:
    """Don vi rieng tung cot: uu tien dau % trong du lieu, roi moi doan header."""
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
    """Xac dinh cot gia tri, don vi chung va so dong header cua bang.

    Tra ve cols la list (col_index, period_label, col_unit) de tach
    cot phan tram va cot VND trong cung bang.
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
    # Nhan ky theo tung cot: uu tien cot co header chua nam/ngay.
    col_labels: list[str] = []
    for c in range(width):
        label = ""
        for r in range(header_count):
            cell = (norm[r][c] or "").strip()
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
    # Loai cot ma so (01, 10, 20...): nhieu so nhung hau het < 1000.
    # Giu cot phan tram du gia tri nho (99,988%).
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
    # Truoc het giu cot so co nhan ky nam/ngay (loai cot chenh lech tuyet doi/tuong doi).
    period_cols = [c for c in numeric_cols if col_labels[c]]
    cols: list[tuple[int, str, str]] = []
    if period_cols:
        # Giu tat ca cot co nhan ky rieng (VD bang HPG co 6 cot so:
        # 2 cot % va 1 cot VND cho moi ky). Khong cat theo len(periods).
        cols = [(c, col_labels[c], _col_unit(c)) for c in sorted(period_cols)]
    elif numeric_cols and periods:
        # Header bi lech cot (ky nam o cot khac cot gia tri): gan theo thu tu
        # trai-phai, cot gia tri thu i nhan ky thu i.
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
                    cell = (norm[r][c] or "").strip()
                    if cell and (YEAR_LOOSE_RE.search(cell) or DATE_RE.search(cell)):
                        label = cell
                        break
                cols.append((c, label or f"col_{c}", _col_unit(c)))
    return cols, unit, header_count


def metric_and_code(row: list[str], value_cols: set[int]) -> tuple[str, str]:
    """Chon o chi tieu (text dai nhat) va ma so trong hang."""
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
                # Nhan ky dang NDTC 2019-2020: lay nam cuoi (nam tai chinh).
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
