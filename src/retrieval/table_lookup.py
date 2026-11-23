"""Structured lookup, unit compatibility, refusal gating, and synthesis on table_records.

Unified module used by both E8 inference (`src/infer/e8_table_lookup.py`)
and the Streamlit/QA engine (`app/qa_engine.py`).
"""

from __future__ import annotations

import re
import unicodedata

UNIT_FACTORS: dict[str, float] = {
    "đồng": 1.0,
    "nghìn đồng": 1e3,
    "triệu đồng": 1e6,
    "tỷ đồng": 1e9,
    "trăm tỷ đồng": 1e11,
    "nghìn tỷ đồng": 1e12,
    "%": 1.0,
    "lần": 1.0,
    "": 1.0,
}

VND_UNITS: set[str] = {
    "đồng",
    "nghìn đồng",
    "triệu đồng",
    "tỷ đồng",
    "trăm tỷ đồng",
    "nghìn tỷ đồng",
}

COMPANY_ALIASES: dict[str, list[str]] = {
    "HPG": ["hpg", "hòa phát", "hoa phat"],
    "HSG": ["hsg", "hoa sen"],
    "NKG": ["nkg", "nam kim", "thép nam kim", "thep nam kim"],
    "MSR": [
        "msr",
        "masan high-tech materials",
        "masan high-tech",
        "masan high tech",
        "masan",
        "high-tech",
        "high tech",
        "hightech",
    ],
}

METRIC_KEYWORDS: dict[str, list[str]] = {
    "doanh thu thuan": ["doanh thu thuan", "doanh thu ban hang"],
    "loi nhuan sau thue": ["loi nhuan sau thue", "loi nhuan thuan"],
    "tien va tuong duong tien": ["tien", "tuong duong"],
    "lai co ban": ["lai co ban", "co phieu"],
    "bien loi nhuan gop": ["bien", "loi nhuan gop"],
    "von chu so huu": ["von chu so huu"],
    "tong tai san": ["tong tai san"],
}

REFUSAL_TEXT_DEFAULT = "Không đủ bằng chứng trong corpus để trả lời."

YEAR_ANY_RE = re.compile(r"\b((?:19|20)\d{2})\b")
CORPUS_YEARS = set(range(2020, 2025))

_OCR_REPLACEMENTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bchỉ\s+phí\b", re.IGNORECASE), "chi phí"),
    (re.compile(r"\bthuân\b", re.IGNORECASE), "thuần"),
    (re.compile(r"\blợi\s+nhuân\b", re.IGNORECASE), "lợi nhuận"),
    (re.compile(r"\bphài\s+trả\b", re.IGNORECASE), "phải trả"),
    (re.compile(r"\bphài\s+thu\b", re.IGNORECASE), "phải thu"),
    (re.compile(r"\bngăn\s+hạn\b", re.IGNORECASE), "ngắn hạn"),
    (re.compile(r"\bchứng\s+khoan\b", re.IGNORECASE), "chứng khoán"),
    (re.compile(r"\bđầu\s+tu\b", re.IGNORECASE), "đầu tư"),
    (re.compile(r"\btài\s+sàn\b", re.IGNORECASE), "tài sản"),
    (re.compile(r"\bdoanh\s+thụ\b", re.IGNORECASE), "doanh thu"),
]

_STOPWORDS_ACC: set[str] = {
    "về",
    "các",
    "của",
    "và",
    "cho",
    "năm",
    "bao",
    "nhiêu",
    "là",
    "trong",
    "tại",
    "ngày",
    "tháng",
    "từ",
    "đến",
    "với",
    "giữa",
    "cùng",
    "kỳ",
    "này",
    "đó",
    "theo",
    "hay",
    "hoặc",
    "được",
    "bị",
    "có",
    "đã",
    "đang",
    "sẽ",
    "trên",
    "dưới",
    "tính",
    "mức",
    "lại",
    "ra",
    "vào",
    "nào",
    "gì",
}

_DEGENERATE_METRICS: set[str] = {
    "khác",
    "cộng",
    "tổng",
    "tổng cộng",
    "trong đó",
    "chi tiết",
    "ghi chú",
    "thuyết minh",
    "mã số",
    "đơn vị",
    "đơn vị tính",
    "usd",
    "eur",
    "vnd",
    "vnđ",
    "đồng",
    "chỉ tiêu",
}

_CONSOLIDATED_METRIC_IDIOMS: list[str] = [
    "co dong cua cong ty me",
    "cua co dong cong ty me",
    "co dong cong ty me",
    "loi ich cua cong ty me",
    "cua cong ty me khong kiem soat",
]

_DIFF_KEYWORDS: tuple[str, ...] = (
    "tăng hay giảm",
    "tang hay giam",
    "tăng giảm",
    "tang giam",
    "chênh lệch",
    "chenh lech",
    "so với",
    "so voi",
    "biến động",
    "bien dong",
    "thay đổi",
    "thay doi",
    "cao hơn hay thấp hơn",
    "nhiều hơn hay ít hơn",
    "hơn kém",
)


def strip_accents(text: str) -> str:
    text = (text or "").replace("đ", "d").replace("Đ", "D")
    text = unicodedata.normalize("NFD", text)
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def norm_text(text: str) -> str:
    text = unicodedata.normalize("NFC", (text or "").lower())
    return re.sub(r"\s+", " ", text).strip()


def normalize_ocr_vi(text: str) -> str:
    s = norm_text(text)
    for pat, repl in _OCR_REPLACEMENTS:
        s = pat.sub(repl, s)
    return re.sub(r"\s+", " ", s).strip()


def tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-zà-ỹ0-9_%.,/+-]+", norm_text(text)))


def _tokens_list(text: str) -> list[str]:
    return re.findall(r"[a-zà-ỹ0-9_%+-]+", normalize_ocr_vi(text))


def resolve_tickers(question: str) -> list[str]:
    """Identify ticker symbols from explicit codes and Vietnamese company names."""
    up = (question or "").upper()
    found: list[str] = []
    for t in ["HPG", "HSG", "NKG", "MSR"]:
        if re.search(rf"(?<![A-Z]){t}(?![A-Z])", up):
            if t not in found:
                found.append(t)
    low_noacc = strip_accents(norm_text(question))
    for ticker, aliases in COMPANY_ALIASES.items():
        if ticker in found:
            continue
        for alias in aliases:
            a_noacc = strip_accents(norm_text(alias))
            if re.search(rf"(?<![a-z0-9]){re.escape(a_noacc)}(?![a-z0-9])", low_noacc):
                if ticker not in found:
                    found.append(ticker)
                break
    return found


def extract_years(question: str) -> list[str]:
    """Extract unique 4-digit years preserving appearance order."""
    return list(dict.fromkeys(YEAR_ANY_RE.findall(question or "")))


def detect_report_version(question: str) -> str:
    """Detect consolidated vs separate report scope without misclassifying consolidated metrics."""
    low_noacc = strip_accents(norm_text(question))
    if any(k in low_noacc for k in ("hop nhat", "consolidated")):
        return "consolidated"
    cleaned = low_noacc
    for idiom in _CONSOLIDATED_METRIC_IDIOMS:
        cleaned = cleaned.replace(idiom, " ")
    if any(
        k in cleaned
        for k in (
            "cong ty me",
            "ban rieng",
            "bao cao rieng",
            "bao cao tai chinh rieng",
            "bctc rieng",
            "rieng le",
            "separate",
        )
    ):
        return "separate"
    return ""


def detect_period_side(question: str) -> str:
    """Detect whether the question explicitly asks for beginning vs ending period balances."""
    low = norm_text(question)
    if any(k in low for k in ("đầu năm", "số đầu năm", "đầu kỳ", "01/01/", "1/1/")):
        return "start"
    if any(k in low for k in ("cuối năm", "số cuối năm", "cuối kỳ", "31/12", "30/09", "30/9", "30.9", "kết thúc ngày")):
        return "end"
    return "auto"


def parse_target_unit(question: str) -> str:
    """Parse requested output unit carefully without matching substrings inside unrelated words."""
    low = norm_text(question)
    low_noacc = strip_accents(low)

    if "%" in question or "phần trăm" in low or "phan tram" in low_noacc:
        return "%"
    if re.search(r"\b(usd|eur)\b", low_noacc) or any(k in low for k in ("đô la", "đô-la", "đôla")):
        if re.search(r"\beur\b", low_noacc):
            return "EUR"
        return "USD"
    if not is_eps_query(question):
        if re.search(r"(?:đồng|vnd|vnđ)\s*(?:một|/|trên)\s*(?:cổ\s*phiếu|cp)\b", low):
            return "đồng/cổ phiếu"
        if re.search(r"(?:đồng|vnd|vnđ)\s*(?:một|/|trên)\s*(?:tấn|kg)\b", low):
            return "đồng/tấn"

    masked = low
    for phrase in (
        "tỷ lệ",
        "tỷ giá",
        "tỷ suất",
        "tỷ trọng",
        "tỷ số",
        "hội đồng",
        "hợp đồng",
        "cộng đồng",
        "đồng thời",
        "đồng nhất",
        "đồng thuận",
        "đồng ý",
        "đồng bộ",
        "đồng nghiệp",
    ):
        masked = masked.replace(phrase, " ")

    masked_noacc = strip_accents(masked)
    for phrase in ("ty le", "ty gia", "ty suat", "ty trong", "ty so"):
        masked_noacc = masked_noacc.replace(phrase, " ")

    if "nghìn tỷ" in masked or "nghin ty" in masked_noacc:
        return "nghìn tỷ đồng"
    if "trăm tỷ" in masked or "tram ty" in masked_noacc:
        return "trăm tỷ đồng"

    # Avoid misreading "triệu cổ phiếu" / "tỷ cổ phiếu" as currency units
    no_share_scale = re.sub(
        r"\b(?:triệu|tỷ|nghìn|trieu|ty|nghin)\s+(?:cổ\s+phiếu|co\s+phieu|cổ\s+đông|co\s+dong|tấn|tan|người|nguoi)\b",
        " ",
        masked,
    )
    if re.search(r"\btriệu(?:\s+đồng)?\b", no_share_scale):
        return "triệu đồng"
    if re.search(r"\btỷ(?:\s+đồng)?\b", no_share_scale):
        return "tỷ đồng"
    if re.search(r"\bnghìn\s+đồng\b", no_share_scale):
        return "nghìn đồng"
    if re.search(r"\blần\b", masked):
        return "lần"
    if re.search(r"(?<![a-zà-ỹ])(đồng|vnd|vnđ)(?![a-zà-ỹ])", masked):
        return "đồng"
    return ""


def detect_query_meta(question: str, use_aliases: bool = True) -> dict:
    """Unified query metadata extractor for tickers, years, report version, period, and unit."""
    tickers = (
        resolve_tickers(question)
        if use_aliases
        else [t for t in ("HPG", "HSG", "NKG", "MSR") if re.search(rf"(?<![A-Z]){t}(?![A-Z])", (question or "").upper())]
    )
    return {
        "tickers": tickers,
        "years": extract_years(question),
        "version": detect_report_version(question),
        "period_side": detect_period_side(question),
        "target_unit": parse_target_unit(question),
    }


def is_eps_query(question: str) -> bool:
    low = norm_text(question)
    low_noacc = strip_accents(low)
    return any(
        k in low_noacc
        for k in ("lai co ban tren co phieu", "lai suy giam tren co phieu", "lai co ban", "eps")
    )


def check_refusal(question: str, extra_patterns: list[str] | None = None) -> tuple[bool, str]:
    """Principled out-of-corpus refusal gating for 2020-2024 annual BCTC QA (HPG/HSG/NKG/MSR)."""
    q = question or ""
    low = norm_text(q)
    low_noacc = strip_accents(low)

    # 1. Config / caller patterns (matched accurately without false-matching "quỹ" as "quý")
    for pat in extra_patterns or []:
        p_norm = norm_text(pat)
        if not p_norm:
            continue
        if p_norm == "quý":
            if re.search(r"(?<![a-zà-ỹ])quý(?![a-zà-ỹ])|\bq[1-4]\b", low):
                return True, "subannual_period"
        elif p_norm in low:
            return True, f"pattern:{p_norm}"

    # 2. Sub-annual periods (avoid "quỹ" and footnote tenure phrasing unless period framing)
    if re.search(r"(?<![a-zà-ỹ])quý(?![a-zà-ỹ])|\bq[1-4]\b", low):
        return True, "subannual_period"
    if any(k in low for k in ("bán niên", "6 tháng đầu năm", "6 tháng cuối năm", "9 tháng đầu năm", "nửa đầu năm")):
        return True, "subannual_period"
    if re.search(r"(?:giai đoạn|kết quả|doanh thu|lợi nhuận|báo cáo)\s+6\s+tháng|\b6\s+tháng\b", low):
        return True, "subannual_period"

    # 3. Out-of-range years (>=2025, or <2020 when standalone)
    yrs_int = [int(y) for y in extract_years(q)]
    if any(y >= 2025 for y in yrs_int):
        return True, "out_of_range_year_future"
    if yrs_int and all(y < 2020 for y in yrs_int):
        return True, "out_of_range_year_past"

    # 4. Forward-looking / forecasts / plans
    if any(k in low for k in ("kế hoạch", "dự báo", "dự kiến", "mục tiêu năm", "ước tính cả năm")):
        return True, "forward_looking"

    # 5. Market / share-price / credit-rating / per-unit non-statement data
    if any(
        k in low
        for k in (
            "giá đóng cửa",
            "vốn hóa thị trường",
            "thị giá",
            "xếp hạng tín nhiệm",
            "giá bán bình quân",
            "tổng số cổ đông",
            "số lượng cổ đông",
            "giá cổ phiếu",
        )
    ):
        return True, "market_or_nonstatement_metric"

    # Per-share dividend or dividend rate per share (note: Cash Flow "Tiền trả cổ tức" in VND IS in corpus)
    if "cổ tức" in low and (
        "cổ phiếu" in low or "/cp" in low_noacc or "tỷ lệ cổ tức" in low or "mức cổ tức" in low
    ):
        return True, "dividend_per_share"

    # Per-share / per-unit queries outside valid EPS ("lãi cơ bản/suy giảm trên cổ phiếu")
    if not is_eps_query(q):
        if re.search(r"(?:đồng|vnd)\s*(?:một|/)\s*(?:cổ\s*phiếu|cp|tấn|kg)\b", low):
            return True, "per_unit_non_statement"
        if re.search(r"giá\s+(?:bán|mua|trung bình|bình quân|vonfram|thép|quặng|than|nhôm)[^.?!]{0,45}(?:một\s+tấn|/tấn|/kg|usd)", low):
            return True, "commodity_unit_price"

    # Foreign currency answer expectation (e.g. "bao nhiêu USD", "USD một tấn", "USD/tấn")
    if parse_target_unit(q) in ("USD", "EUR"):
        return True, "foreign_currency_unit"
    if re.search(r"\busd\s*(?:một|/)\s*\w+", low_noacc) or (
        re.search(r"\busd\b", low_noacc) and re.search(r"\b(tấn|tan|kg|ounce|thùng|thung)\b", low)
    ):
        return True, "foreign_currency_commodity"

    return False, ""


def is_unit_compatible(record_unit: str, target_unit: str) -> bool:
    """Check whether a table record's unit can validly satisfy the question's target unit."""
    ru = (record_unit or "").strip()
    tu = (target_unit or "").strip()
    if not tu:
        return True
    if tu == "%":
        return ru == "%"
    if tu == "lần":
        return ru in ("lần", "")
    if tu in VND_UNITS:
        return ru in VND_UNITS or ru == ""
    return ru == tu


def convert_value(value: float, from_unit: str, to_unit: str) -> float | None:
    if value is None:
        return None
    fu_str = (from_unit or "").strip()
    tu_str = (to_unit or "").strip()
    if not tu_str:
        return float(value)
    if not is_unit_compatible(fu_str, tu_str):
        return None
    if tu_str == "%":
        return float(value) if fu_str == "%" else None
    if tu_str == "lần":
        return float(value) if fu_str in ("lần", "") else None
    fu = UNIT_FACTORS.get(fu_str, None)
    tu = UNIT_FACTORS.get(tu_str, None)
    if fu is None or tu is None:
        return None
    return float(value) * fu / tu


def pick_readable_vnd_unit(abs_vnd_value: float) -> str:
    val = abs(float(abs_vnd_value))
    if val >= 1e12:
        return "nghìn tỷ đồng"
    if val >= 1e9:
        return "tỷ đồng"
    if val >= 1e6:
        return "triệu đồng"
    return "đồng"


def format_number(value: float) -> str:
    if value is None:
        return ""
    if abs(value) >= 1e15 or (abs(value) < 1e-6 and value != 0):
        return f"{value:.4f}"
    rounded = round(float(value), 4)
    if rounded == int(rounded):
        return str(int(rounded))
    text = f"{rounded:.4f}".rstrip("0").rstrip(".")
    return text


def _strip_metric_decorations(record_metric: str) -> str:
    s = normalize_ocr_vi(record_metric or "")
    s = re.sub(r"\\?\([^)]*\)", " ", s)
    s = re.sub(r"\([^)]*\)", " ", s)
    s = re.sub(r"^(?:[a-d]\s*[-–.]\s*|[ivx]+\.\s*|\d+(?:\.\d+)*\.?\s*[-–.]?\s*)", "", s)
    s = re.sub(r"\btndn\b", "thu nhập doanh nghiệp", s)
    s = re.sub(r"[:;.,!?]+$", "", s)
    return re.sub(r"\s+", " ", s).strip()


def extract_metric_core(question: str) -> str:
    """Extract the metric phrase from a Vietnamese question while preserving subsidiary names."""
    s = normalize_ocr_vi(question or "")
    # Remove trailing comparison/question clauses before removing "bao nhiêu"
    s = re.sub(
        r"\b(?:tăng\s+hay\s+giảm|tăng\s+giảm|(?:tăng|giảm)\s+(?:thêm|đi|lên|xuống)?\s*(?:bao\s+nhiêu|bằng\s+bao\s+nhiêu|mấy))\b.*$",
        " ",
        s,
    )
    s = re.sub(r"\b(?:là\s+)?(?:bao\s+nhiêu|bằng\s+bao\s+nhiêu|đạt\s+bao\s+nhiêu)\b.*$", " ", s)
    # Remove framing prefixes / clauses
    for pat in (
        r"\btrong\s+giai\s+đoạn\b",
        r"\btính\s+mức\s+chênh\s+lệch\b",
        r"\bmức\s+chênh\s+lệch\b",
        r"\bchênh\s+lệch\b",
        r"\bso\s+với\b",
        r"\bnăm\s+tài\s+chính\s+kết\s+thúc\s+ngày\b",
        r"\bkết\s+thúc\s+ngày\b",
        r"\btính\s+đến\s+ngày\b",
        r"\btại\s+ngày\b",
        r"\bcho\s+biết\b",
        r"\bhãy\s+cho\s+biết\b",
        r"\bbáo\s+cáo\s+tài\s+chính\b",
        r"\bbctc\b",
        r"\bchỉ\s+tiêu\b",
        r"\bchi\s+tiêu\s+cho\b",
        r"\bgiá\s+trị\b",
        r"\bhợp\s+nhất\b",
        r"\bbáo\s+cáo\s+riêng\b",
        r"\bbản\s+riêng\b",
        r"\briêng\s+lẻ\b",
        r"\bconsolidated\b",
        r"\bseparate\b",
    ):
        s = re.sub(pat, " ", s)
    # Remove multi-year range/comparison clauses before removing standalone years
    s = re.sub(
        r"\b(?:giữa|từ)\s+(?:năm\s+)?(?:19|20)\d{2}\s+(?:và|đến|tới)\s+(?:năm\s+)?(?:19|20)\d{2}\b",
        " ",
        s,
    )
    # Remove temporal period markers ("đầu năm", "cuối năm") and dates & years
    s = re.sub(r"\b(?:đầu|cuối)\s+(?:năm|kỳ)(?:\s+(?:19|20)\d{2})?\b", " ", s)
    s = re.sub(r"\b\d{1,2}[./-]\d{1,2}[./-](?:19|20)\d{2}\b", " ", s)
    s = re.sub(r"\bnăm\s+(?:19|20)\d{2}\b", " ", s)
    s = re.sub(r"\b(?:19|20)\d{2}\b", " ", s)
    # Remove parent company ownership clauses ("của CTCP Tập đoàn Hòa Phát", tickers),
    # while keeping subsidiary targets ("tại Công ty TNHH Tôn Hòa Phát") untouched!
    s = re.sub(
        r"\b(?:của\s+)?(?:(?:ctcp|công\s+ty\s+cổ\s+phần)\s+)?(?:tập\s+đoàn\s+hòa\s+phát|tập\s+đoàn\s+hoa\s+sen|thép\s+nam\s+kim|masan\s+high[-\s]*tech(?:\s+materials)?)\b",
        " ",
        s,
    )
    s = re.sub(r"\bcủa\s+(?:hòa\s+phát|hoa\s+sen|nam\s+kim|masan)\b", " ", s)
    s = re.sub(r"\b(?:của\s+)?(?:hpg|hsg|nkg|msr)\b", " ", s)
    # Remove report-scope "công ty mẹ" only when NOT part of consolidated ownership/profit metric
    s_noacc = strip_accents(s)
    if not any(idiom in s_noacc for idiom in _CONSOLIDATED_METRIC_IDIOMS):
        s = re.sub(r"\b(?:của\s+)?công\s+ty\s+mẹ\b", " ", s)
    # Expand common VAS abbreviation and remove dangling units/prepositions
    s = re.sub(r"\btndn\b", "thu nhập doanh nghiệp", s)
    s = re.sub(r"\b(?:nghìn\s+tỷ\s+đồng|trăm\s+tỷ\s+đồng|tỷ\s+đồng|triệu\s+đồng|nghìn\s+đồng|phần\s+trăm|đồng|vnd|vnđ)\b", " ", s)
    s = re.sub(r"[,;?\"']+", " ", s)
    s = re.sub(r"(?:^|\s)(?:của|về|cho|tại|ở)\s*$", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _content_tokens(text: str) -> list[str]:
    return [t for t in _tokens_list(text) if len(t) > 1 and t not in _STOPWORDS_ACC]


_BREAKDOWN_CUES: tuple[str, ...] = (
    "bo phan",
    "linh vuc",
    "nganh",
    "khu vuc",
    "san pham",
    "noi bo",
    "ban ra ngoai",
    "ra ben ngoai",
    "ben ngoai",
    "rangoai",
    "nguyen gia",
    "hao mon",
    "luy ke",
    "thuyet minh",
    "chi tiet",
    "tam ung",
    "thu lao",
    "ty le so huu",
    "cong ty con",
    "cong ty lien ket",
    "khong kiem soat",
)


def _is_breakdown_query(question: str) -> bool:
    low_noacc = strip_accents(normalize_ocr_vi(question or ""))
    return any(cue in low_noacc for cue in _BREAKDOWN_CUES)


# (phrases_to_match, canonical_replacements, short_headline_only)
_VAS_METRIC_ALIASES: list[tuple[tuple[str, ...], tuple[str, ...], bool]] = [
    (
        (
            "thu nhập thuần từ hoạt động khác",
            "lợi nhuận thuần từ hoạt động khác",
            "lãi thuần từ hoạt động khác",
            "kết quả từ hoạt động khác",
            "lợi nhuận khác",
        ),
        ("kết quả từ hoạt động khác", "lợi nhuận khác"),
        False,
    ),
    (("tổng vốn chủ sở hữu", "tổng cộng vốn chủ sở hữu"), ("vốn chủ sở hữu",), True),
    (("tiền và tương đương tiền",), ("tiền và các khoản tương đương tiền",), True),
    (("giá vốn hàng bán",), ("giá vốn hàng bán và dịch vụ cung cấp",), True),
    (
        ("tổng lợi nhuận kế toán trước thuế", "lợi nhuận kế toán trước thuế"),
        ("lợi nhuận kế toán trước thuế", "tổng lợi nhuận kế toán trước thuế"),
        True,
    ),
    (("doanh thu thuần",), ("doanh thu thuần về bán hàng và cung cấp dịch vụ",), True),
    (("doanh thu bán hàng", "tổng doanh thu"), ("doanh thu bán hàng và cung cấp dịch vụ",), True),
    (("lợi nhuận gộp",), ("lợi nhuận gộp về bán hàng và cung cấp dịch vụ",), True),
    (("lợi nhuận thuần",), ("lợi nhuận thuần từ hoạt động kinh doanh",), True),
    (("lợi nhuận trước thuế",), ("lợi nhuận kế toán trước thuế", "tổng lợi nhuận kế toán trước thuế"), True),
    (("lợi nhuận sau thuế",), ("lợi nhuận sau thuế thu nhập doanh nghiệp",), True),
    (("tổng tài sản",), ("tổng cộng tài sản",), True),
    (("tổng nguồn vốn",), ("tổng cộng nguồn vốn",), True),
    (("tổng nợ phải trả",), ("nợ phải trả",), True),
]


def _metric_score_single(q_phrase: str, qn_full: str, mn_base: str) -> float:
    m_toks = _content_tokens(mn_base)
    if not m_toks:
        m_toks = [t for t in _tokens_list(mn_base) if len(t) > 1]
    q_toks = _content_tokens(q_phrase)
    if not q_toks:
        q_toks = _content_tokens(qn_full)
    if not m_toks or not q_toks:
        return 0.0

    m_set = set(m_toks)
    q_set = set(q_toks)
    m_noacc = {strip_accents(t) for t in m_set}
    q_noacc = {strip_accents(t) for t in q_set}

    inter_acc = q_set & m_set
    inter_noacc = q_noacc & m_noacc

    # Require at least one overlapping non-numeric domain word
    if not any(not t.isdigit() for t in inter_noacc):
        return 0.0
    if not inter_acc and len(inter_noacc) < 2:
        return 0.0

    # Reject single-token labels like "Tiền" matching multi-word metrics ("Cổ tức tiền mặt")
    if len(m_set) == 1 and len(q_set) >= 2:
        return 0.0

    recall = (0.8 * len(inter_acc) / len(m_set)) + (0.2 * len(inter_noacc) / len(m_noacc))
    precision = (0.8 * len(inter_acc) / len(q_set)) + (0.2 * len(inter_noacc) / len(q_noacc))
    if recall + precision == 0:
        return 0.0
    f1 = 2.0 * recall * precision / (recall + precision)

    q_phrase_noacc = strip_accents(q_phrase)
    mn_base_noacc = strip_accents(mn_base)
    qn_full_noacc = strip_accents(qn_full)

    is_containment = (
        len(q_set) >= 2
        and precision >= 0.75
        and (q_phrase in mn_base or q_phrase_noacc in mn_base_noacc)
    )
    if precision < 0.25 or (recall < 0.34 and not is_containment):
        return 0.0

    phrase_bonus = 0.0
    if mn_base == q_phrase or mn_base_noacc == q_phrase_noacc:
        phrase_bonus = 0.22
    elif is_containment and (mn_base.startswith(q_phrase) or mn_base_noacc.startswith(q_phrase_noacc)):
        phrase_bonus = 0.20
    elif mn_base in qn_full or mn_base in q_phrase:
        phrase_bonus = 0.16 + min(0.06, len(mn_base) / 250.0)
    elif mn_base_noacc in qn_full_noacc:
        phrase_bonus = 0.12 + min(0.04, len(mn_base_noacc) / 250.0)
    elif len(q_phrase) >= 6 and (q_phrase in mn_base or q_phrase_noacc in mn_base_noacc):
        phrase_bonus = 0.16 if is_containment else 0.10

    score = 0.56 * f1 + 0.22 * (max(recall, 0.75 * precision) if is_containment else recall) + phrase_bonus

    # Key accounting semantic distinction guards
    q_all_noacc = qn_full_noacc
    m_all_noacc = mn_base_noacc
    if ("thuan" in q_all_noacc) != ("thuan" in m_all_noacc):
        score -= 0.25
    for a, b in (
        ("ngan han", "dai han"),
        ("truoc thue", "sau thue"),
        ("phai thu", "phai tra"),
        ("lai co ban", "lai suy giam"),
        ("ban hang", "quan ly"),
        ("tai chinh", "quan ly"),
    ):
        if (a in q_all_noacc and b not in q_all_noacc and b in m_all_noacc and a not in m_all_noacc) or (
            b in q_all_noacc and a not in q_all_noacc and a in m_all_noacc and b not in m_all_noacc
        ):
            score -= 0.35

    return max(0.0, min(1.0, score))


def metric_score(question: str, record_metric: str) -> float:
    """Bidirectional Vietnamese metric similarity score clamped to [0.0, 1.0]."""
    raw_m = normalize_ocr_vi(record_metric or "")
    mn_base = _strip_metric_decorations(raw_m)
    if not mn_base or mn_base in _DEGENERATE_METRICS:
        return 0.0

    q_core = extract_metric_core(question)
    qn_full = normalize_ocr_vi(question or "")
    q_phrase = q_core if q_core else qn_full

    best = _metric_score_single(q_phrase, qn_full, mn_base)
    q_noacc = strip_accents(q_phrase)
    qn_full_noacc = strip_accents(qn_full)
    q_toks_cnt = len(_content_tokens(q_phrase))
    has_shareholder_mod = "co dong" in qn_full_noacc or "khong kiem soat" in qn_full_noacc
    is_breakdown = _is_breakdown_query(question)
    is_ratio_ask = any(k in qn_full_noacc for k in ("ty trong", "ty suat", "ty le", "chiem bao nhieu"))

    for phrases, canonicals, short_headline_only in _VAS_METRIC_ALIASES:
        if short_headline_only and (is_breakdown or has_shareholder_mod or is_ratio_ask):
            continue
        for ph in phrases:
            ph_noacc = strip_accents(ph)
            if ph in q_phrase or ph_noacc in q_noacc:
                if short_headline_only and q_toks_cnt > len(_content_tokens(ph)):
                    continue
                for canonical in canonicals:
                    if ph in q_phrase:
                        alt_phrase = q_phrase.replace(ph, canonical)
                        alt_full = qn_full.replace(ph, canonical)
                    elif ph_noacc in q_noacc:
                        if q_toks_cnt <= len(_content_tokens(ph)):
                            alt_phrase = canonical
                            alt_full = canonical
                        else:
                            alt_phrase = re.sub(re.escape(ph_noacc), canonical, q_noacc)
                            alt_full = re.sub(re.escape(ph_noacc), canonical, qn_full_noacc)
                    else:
                        continue
                    best = max(best, _metric_score_single(alt_phrase, alt_full, mn_base))
                break
    return best


def _period_rank(period_label: str, period_side: str) -> int:
    pl = (period_label or "").lower()
    is_start = bool(re.search(r"(?:^|[^0-9])0?1[./-]0?1[./-]|đầu năm|đầu kỳ", pl))
    is_end = bool(re.search(r"(?:31[./-]12|30[./-]0?9)[./-]|cuối năm|cuối kỳ", pl))
    is_col = pl.startswith("col_")
    if period_side == "start":
        if is_start:
            return 3
        if is_end:
            return 0
        return 1 if is_col else 2
    # Default ("auto" or "end"): strongly prefer ending balance & penalize 1/1 beginning balance
    if is_end:
        return 4
    if is_start:
        return 0
    if not is_col:
        return 3
    if pl == "col_2":
        return 2
    return 1


def _rank_key(
    r: dict,
    m_score: float,
    target_unit: str,
    period_side: str,
    requested_version: str,
    prefer_primary: bool = True,
) -> tuple:
    ru = (r.get("unit") or "").strip()
    tu = (target_unit or "").strip()
    if tu:
        unit_tier = 3 if ru == tu else (2 if ru in VND_UNITS else 0)
    else:
        unit_tier = 2 if ru in VND_UNITS or ru in ("%", "lần") else 0

    p_tier = _period_rank(str(r.get("period_label") or ""), period_side)
    p_side_ok = 1 if p_tier > 0 else 0
    p_explicit = 1 if p_tier >= 3 else 0
    native_yr = 1 if str(r.get("fiscal_year", "")) == str(r.get("year", "")) else 0
    ver = r.get("report_version") or ""
    ver_tier = 1 if (requested_version and ver == requested_version) or (not requested_version and ver == "consolidated") else 0
    stmt = r.get("statement") or "other"
    stmt_tier = 2 if stmt in ("income_statement", "balance_sheet", "cash_flow") else 0
    code_tier = 1 if r.get("metric_code") else 0
    stmt_pref = stmt_tier if prefer_primary else 0
    code_pref = code_tier if (prefer_primary and stmt_tier > 0) else 0
    conf = float(r.get("confidence") or 0.0)
    raw_val = float(r.get("value") or 0.0)
    non_footnote = (
        0
        if (
            ru == "đồng"
            and 0 < abs(raw_val) < 100
            and raw_val == int(raw_val)
            and "cổ phiếu" not in normalize_ocr_vi(r.get("metric", ""))
        )
        else 1
    )
    m_bucket = round(m_score, 2)
    return (
        m_bucket,
        non_footnote,
        unit_tier,
        p_side_ok,
        ver_tier,
        stmt_pref,
        code_pref,
        native_yr,
        p_explicit,
        p_tier,
        m_score,
        conf,
    )


def _is_ratio_without_currency_query(question: str, target_unit: str = "") -> bool:
    """Return True when the question asks for a ratio/proportion/percentage without a currency target."""
    tu = (target_unit or "").strip()
    if tu in VND_UNITS or tu in ("USD", "EUR"):
        return False
    low_noacc = strip_accents(norm_text(question or ""))
    return any(k in low_noacc for k in ("ty trong", "ty suat", "ty le", "chiem bao nhieu"))


def lookup_records(
    records: list[dict],
    tickers: list[str],
    years: list[str],
    version: str,
    question: str,
    min_score: float = 0.35,
    target_unit: str = "",
    period_side: str = "auto",
) -> list[tuple[float, dict]]:
    """Lookup structured table records matching metadata, unit compatibility, and tightened metric score."""
    scored: list[tuple[tuple, float, dict]] = []
    year_set = {str(y) for y in years}
    tu = (target_unit or "").strip()
    prefer_primary = not _is_breakdown_query(question)
    ratio_no_currency = _is_ratio_without_currency_query(question, tu)
    for r in records:
        if tickers and r.get("company") not in tickers:
            continue
        if year_set and str(r.get("year")) not in year_set:
            continue
        if version and r.get("report_version") != version:
            continue
        ru = (r.get("unit") or "").strip()
        if ratio_no_currency and ru in VND_UNITS:
            continue
        if tu:
            if not is_unit_compatible(ru, tu):
                continue
            # Exclude tiny footnote numbers when unit is missing on a VND question
            if ru == "" and tu in VND_UNITS and abs(float(r.get("value") or 0.0)) < 1e5:
                continue
        s = metric_score(question, r.get("metric", ""))
        if s < min_score:
            continue
        key = _rank_key(r, s, tu, period_side, version, prefer_primary=prefer_primary)
        out_score = max(0.0, min(1.0, s))
        scored.append((key, out_score, r))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [(s, r) for _, s, r in scored]


def find_pair(
    records: list[dict],
    tickers: list[str],
    years: list[str],
    version: str,
    keywords: list[str],
    target_unit: str = "",
    period_side: str = "auto",
) -> dict | None:
    cands = lookup_records(
        records,
        tickers,
        years,
        version,
        " ".join(keywords),
        min_score=0.25,
        target_unit=target_unit,
        period_side=period_side,
    )
    if not cands:
        return None
    return cands[0][1]


def find_by_code(
    records: list[dict],
    tickers: list[str],
    years: list[str],
    version: str,
    codes: list[str],
    keywords: list[str] | None = None,
    period_side: str = "auto",
) -> dict | None:
    """Find best matching standard statement line item by VAS metric_code and optional keywords."""
    year_set = {str(y) for y in years}
    kw = [normalize_ocr_vi(k) for k in (keywords or [])]
    cands: list[tuple[tuple, dict]] = []
    for r in records:
        if tickers and r.get("company") not in tickers:
            continue
        if year_set and str(r.get("year")) not in year_set:
            continue
        if version and r.get("report_version") != version:
            continue
        if str(r.get("metric_code") or "") not in codes:
            continue
        if kw:
            mn = normalize_ocr_vi(r.get("metric", ""))
            if not any(k and k in mn for k in kw):
                continue
        stmt_tier = 2 if r.get("statement") == "income_statement" else (1 if r.get("statement") != "other" else 0)
        p_tier = _period_rank(str(r.get("period_label") or ""), period_side)
        p_side_ok = 1 if p_tier > 0 else 0
        native_yr = 1 if str(r.get("fiscal_year", "")) == str(r.get("year", "")) else 0
        ver_tier = 1 if (version and r.get("report_version") == version) or (not version and r.get("report_version") == "consolidated") else 0
        unit_tier = 1 if (r.get("unit") or "").strip() in VND_UNITS else 0
        conf = float(r.get("confidence") or 0.0)
        cands.append(((stmt_tier, ver_tier, unit_tier, p_side_ok, native_yr, p_tier, conf), r))
    if not cands:
        return None
    cands.sort(key=lambda x: x[0], reverse=True)
    return cands[0][1]


def is_comparison_query(question: str, years: list[str] | None = None) -> bool:
    """Detect T2/T3 multi-year change or difference questions."""
    yrs = years if years is not None else extract_years(question)
    uniq = sorted({int(y) for y in yrs if int(y) in CORPUS_YEARS})
    if len(uniq) != 2:
        return False
    low = norm_text(question)
    low_noacc = strip_accents(low)
    return any(k in low or k in low_noacc for k in _DIFF_KEYWORDS)


def lookup_comparison_pair(
    records: list[dict],
    ticker: str,
    y1: str,
    y2: str,
    version: str,
    question: str,
    min_score: float = 0.35,
    target_unit: str = "",
    period_side: str = "auto",
) -> tuple[float, dict, dict] | None:
    """Find best consistent (r_y1, r_y2) pair for two-year T2/T3 comparison."""
    # Allow records in either currency or target unit, preferring explicit units
    tu_filter = target_unit if target_unit in ("%", "lần") else ""
    prefer_primary = not _is_breakdown_query(question)
    c1 = lookup_records(
        records,
        [ticker],
        [str(y1)],
        version,
        question,
        min_score=min_score,
        target_unit=tu_filter,
        period_side=period_side,
    )[:40]
    c2 = lookup_records(
        records,
        [ticker],
        [str(y2)],
        version,
        question,
        min_score=min_score,
        target_unit=tu_filter,
        period_side=period_side,
    )[:40]
    if not c1 or not c2:
        return None

    best_key: tuple | None = None
    best_pair: tuple[float, dict, dict] | None = None
    for s1, r1 in c1:
        u1 = (r1.get("unit") or "").strip()
        if target_unit and not is_unit_compatible(u1, target_unit):
            continue
        v1 = _period_rank(str(r1.get("period_label") or ""), period_side)
        if period_side != "start" and v1 == 0:
            continue
        m1_norm = _strip_metric_decorations(r1.get("metric", ""))
        for s2, r2 in c2:
            if (r1.get("report_version") or "") != (r2.get("report_version") or ""):
                continue
            u2 = (r2.get("unit") or "").strip()
            if target_unit and not is_unit_compatible(u2, target_unit):
                continue
            if (u1 == "%") != (u2 == "%"):
                continue
            v2 = _period_rank(str(r2.get("period_label") or ""), period_side)
            if period_side != "start" and v2 == 0:
                continue
            # Verify both convert cleanly into a common unit
            if u1 == "%" and u2 == "%":
                pass
            elif convert_value(float(r1["value"]), u1, "đồng") is None or convert_value(float(r2["value"]), u2, "đồng") is None:
                continue

            m2_norm = _strip_metric_decorations(r2.get("metric", ""))
            same_chunk = 1 if (r1.get("source_chunk_id") and r1.get("source_chunk_id") == r2.get("source_chunk_id")) else 0
            same_metric = 1 if m1_norm and m1_norm == m2_norm else 0
            code1, code2 = str(r1.get("metric_code") or ""), str(r2.get("metric_code") or "")
            same_code = 1 if (code1 and code1 == code2) else 0
            if not (same_chunk or same_metric or same_code):
                continue
            same_stmt = 1 if r1.get("statement") == r2.get("statement") else 0
            primary_stmts = ("income_statement", "balance_sheet", "cash_flow")
            stmt_tier = 2 if (r1.get("statement") in primary_stmts and r2.get("statement") in primary_stmts) else 0
            ver_tier = 1 if (version and r1.get("report_version") == version) or (not version and r1.get("report_version") == "consolidated") else 0
            avg_score = round((s1 + s2) / 2.0, 4)
            unit_explicit = 1 if (u1 in VND_UNITS or u1 == "%") and (u2 in VND_UNITS or u2 == "%") else 0
            not_start_both = 1 if (v1 > 0 and v2 > 0) else 0
            explicit_both = 1 if (v1 >= 3 and v2 >= 3) else 0
            stmt_pref = stmt_tier if prefer_primary else 0
            code_pref = same_code if (prefer_primary and stmt_tier > 0) else 0
            # Prefer strong score, matching report version & primary statement, same code/metric/chunk
            pair_key = (
                round(avg_score, 2),
                not_start_both,
                unit_explicit,
                ver_tier,
                stmt_pref,
                code_pref,
                same_metric,
                same_chunk,
                same_stmt,
                explicit_both,
                v1 + v2,
                avg_score,
            )
            if best_key is None or pair_key > best_key:
                best_key = pair_key
                best_pair = (avg_score, r1, r2)
    return best_pair


def _result_base(
    question: str,
    tickers: list[str],
    years: list[str],
    version: str,
    target_unit: str,
) -> dict:
    return {
        "refused": False,
        "refusal_reason": "",
        "answer": "",
        "computation": "",
        "answer_source": "none",
        "evidence_records": [],
        "evidence_chunk_ids": [],
        "lookup_score": 0.0,
        "predicted_year": "",
        "predicted_company": tickers[0] if len(tickers) == 1 else "",
        "predicted_report_version": version,
        "predicted_page": "",
        "tickers": tickers,
        "years": years,
        "version": version,
        "target_unit": target_unit,
    }


def _compute_margin_single(
    records: list[dict],
    tickers: list[str],
    yr_list: list[str],
    version: str,
    target_unit: str,
    period_side: str,
) -> tuple[float, dict, dict] | None:
    if target_unit and target_unit != "%":
        return None
    for v_try in ((version,) if version else ("consolidated", "")):
        gross = find_by_code(records, tickers, yr_list, v_try, ["20"], ["lợi nhuận gộp", "loi nhuan gop"], period_side=period_side)
        if not gross:
            continue
        rev_ver = gross.get("report_version") or v_try
        rev = find_by_code(records, tickers, yr_list, rev_ver, ["10"], ["doanh thu thuần", "doanh thu thuan"], period_side=period_side)
        if not rev or not rev.get("value"):
            continue
        g_vnd = convert_value(float(gross["value"]), gross.get("unit", ""), "đồng")
        r_vnd = convert_value(float(rev["value"]), rev.get("unit", ""), "đồng")
        if g_vnd is None or r_vnd is None or r_vnd == 0:
            continue
        return (g_vnd / r_vnd) * 100.0, gross, rev
    return None


def synthesize_answer(
    question: str,
    records: list[dict],
    min_score: float = 0.35,
    extra_refusal_patterns: list[str] | None = None,
    refusal_text: str = REFUSAL_TEXT_DEFAULT,
) -> dict:
    """Unified structured lookup + calculation + refusal synthesis shared by E8 and QAEngine."""
    meta = detect_query_meta(question, use_aliases=True)
    tickers = meta["tickers"]
    years = meta["years"]
    version = meta["version"]
    period_side = meta["period_side"]
    target_unit = meta["target_unit"]
    res = _result_base(question, tickers, years, version, target_unit)

    refused, reason = check_refusal(question, extra_patterns=extra_refusal_patterns)
    if refused:
        res["refused"] = True
        res["refusal_reason"] = reason
        res["answer"] = refusal_text
        res["answer_source"] = "refusal_rule"
        return res

    # Only synthesize structured single-company table answers when exactly 1 corpus company is identified
    if len(tickers) != 1:
        return res
    ticker = tickers[0]

    low = norm_text(question)
    low_noacc = strip_accents(low)
    is_numeric_ask = bool(target_unit) or any(
        k in low_noacc for k in ("bao nhieu", "may ", "so du", "so tien", "ty le", "bien ")
    )
    is_qualitative = any(
        k in low_noacc
        for k in (
            "nhu the nao",
            "the nao",
            "tai sao",
            "vi sao",
            "gom nhung",
            "bao gom nhung",
            "nhung khoan nao",
            "cac khoan nao",
            "nhung noi dung",
            "noi dung gi",
            "chi tiet gom",
            "ke ten",
            "liet ke",
            "phuong phap nao",
            "chinh sach",
            "la gi",
        )
    )
    if is_qualitative and not is_numeric_ask and not is_comparison_query(question, years):
        return res
    is_margin = ("bien" in low_noacc) and ("gop" in low_noacc)
    corpus_yrs = sorted({int(y) for y in years if int(y) in CORPUS_YEARS})

    # Case 1: T2 / T3 two-year comparison or difference
    if len(corpus_yrs) == 2 and is_comparison_query(question, [str(y) for y in corpus_yrs]):
        y1, y2 = str(corpus_yrs[0]), str(corpus_yrs[1])
        if is_margin:
            m1 = _compute_margin_single(records, [ticker], [y1], version, target_unit, period_side)
            m2 = _compute_margin_single(records, [ticker], [y2], version, target_unit, period_side)
            if m1 and m2:
                val1, g1, rev1 = m1
                val2, g2, rev2 = m2
                diff = val2 - val1
                out_unit = target_unit or "%"
                evs = [g1, rev1, g2, rev2]
                res["answer"] = f"{format_number(diff)} {out_unit}".strip()
                res["computation"] = (
                    f"{y2}: {format_number(val2)}% - {y1}: {format_number(val1)}% "
                    f"= {format_number(diff)} {out_unit}"
                )
                res["answer_source"] = "computed_diff"
                res["evidence_records"] = evs
                res["evidence_chunk_ids"] = list(dict.fromkeys(r.get("source_chunk_id", "") for r in evs if r.get("source_chunk_id")))
                best_m = max(metric_score(question, g2.get("metric", "")), metric_score(question, g1.get("metric", "")), 0.92)
                res["lookup_score"] = round(max(0.85, min(1.0, best_m)), 4)
                res["predicted_year"] = f"{y1}|{y2}"
                res["predicted_company"] = g2.get("company") or ticker
                res["predicted_report_version"] = g2.get("report_version", version)
                res["predicted_page"] = g2.get("page", "")
                return res

        pair = lookup_comparison_pair(
            records,
            ticker,
            y1,
            y2,
            version,
            question,
            min_score=min_score,
            target_unit=target_unit,
            period_side=period_side,
        )
        if pair is not None:
            pair_score, r1, r2 = pair
            u1, u2 = (r1.get("unit") or "").strip(), (r2.get("unit") or "").strip()
            if u1 == "%" and u2 == "%":
                v1, v2 = float(r1["value"]), float(r2["value"])
                diff = v2 - v1
                out_unit = target_unit or "%"
                comp = f"{y2}: {format_number(v2)}% - {y1}: {format_number(v1)}% = {format_number(diff)} {out_unit}"
            else:
                v1_vnd = convert_value(float(r1["value"]), u1, "đồng")
                v2_vnd = convert_value(float(r2["value"]), u2, "đồng")
                if v1_vnd is None or v2_vnd is None:
                    return res
                diff_vnd = v2_vnd - v1_vnd
                out_unit = target_unit if target_unit in VND_UNITS else pick_readable_vnd_unit(abs(diff_vnd))
                v1_out = convert_value(v1_vnd, "đồng", out_unit)
                v2_out = convert_value(v2_vnd, "đồng", out_unit)
                diff = convert_value(diff_vnd, "đồng", out_unit)
                if v1_out is None or v2_out is None or diff is None:
                    return res
                comp = (
                    f"{y2}: {format_number(v2_out)} {out_unit} - "
                    f"{y1}: {format_number(v1_out)} {out_unit} = "
                    f"{format_number(diff)} {out_unit}"
                )
            # Keep both evidence chunk IDs (prioritizing primary y2 or distinct y1/y2 chunks)
            ev_ids = list(
                dict.fromkeys(
                    cid for cid in (r1.get("source_chunk_id", ""), r2.get("source_chunk_id", "")) if cid
                )
            )
            res["answer"] = f"{format_number(diff)} {out_unit}".strip()
            res["computation"] = comp
            res["answer_source"] = "computed_diff"
            res["evidence_records"] = [r1, r2]
            res["evidence_chunk_ids"] = ev_ids
            res["lookup_score"] = max(0.0, min(1.0, float(pair_score)))
            res["predicted_year"] = f"{y1}|{y2}"
            res["predicted_company"] = ticker
            res["predicted_report_version"] = r2.get("report_version") or r1.get("report_version") or version
            res["predicted_page"] = r2.get("page", "")
            return res
        return res

    # Case 2: Gross profit margin calculation
    if is_margin:
        m = _compute_margin_single(records, [ticker], years, version, target_unit, period_side)
        if m is not None:
            margin, gross, rev = m
            out_unit = target_unit or "%"
            ev_ids = list(
                dict.fromkeys(
                    cid for cid in (gross.get("source_chunk_id", ""), rev.get("source_chunk_id", "")) if cid
                )
            )
            res["answer"] = f"{format_number(margin)} {out_unit}".strip()
            res["computation"] = (
                f"({format_number(float(gross['value']))} / {format_number(float(rev['value']))}) × 100% "
                f"= {format_number(margin)} {out_unit}"
            )
            res["answer_source"] = "computed_margin"
            res["evidence_records"] = [gross, rev]
            res["evidence_chunk_ids"] = ev_ids
            res["lookup_score"] = round(
                max(0.85, min(1.0, max(metric_score(question, gross.get("metric", "")), 0.92))),
                4,
            )
            res["predicted_year"] = str(gross.get("fiscal_year") or gross.get("year") or "")
            res["predicted_company"] = str(gross.get("company") or ticker)
            res["predicted_report_version"] = str(gross.get("report_version") or version)
            res["predicted_page"] = gross.get("page", "")
            return res

    # Case 3: Single-metric structured lookup with strict unit compatibility
    cands = lookup_records(
        records,
        [ticker],
        years,
        version,
        question,
        min_score=min_score,
        target_unit=target_unit,
        period_side=period_side,
    )
    if not cands:
        return res

    best_score, hit = cands[0]
    from_unit = (hit.get("unit") or "").strip()
    out_unit = target_unit or from_unit
    conv = convert_value(float(hit["value"]), from_unit, out_unit)
    if conv is None:
        return res

    res["answer"] = f"{format_number(conv)} {out_unit}".strip()
    if from_unit and out_unit and from_unit != out_unit:
        res["computation"] = f"{format_number(float(hit['value']))} {from_unit} = {format_number(conv)} {out_unit}"
    else:
        res["computation"] = f"{hit.get('metric', '')}: {format_number(conv)} {out_unit}".strip()
    res["answer_source"] = "table_lookup"
    res["evidence_records"] = [hit]
    if hit.get("source_chunk_id"):
        res["evidence_chunk_ids"] = [hit["source_chunk_id"]]
    res["lookup_score"] = max(0.0, min(1.0, float(best_score)))
    res["predicted_year"] = str(hit.get("fiscal_year") or hit.get("year") or "")
    res["predicted_company"] = str(hit.get("company") or ticker)
    res["predicted_report_version"] = str(hit.get("report_version") or version)
    res["predicted_page"] = hit.get("page", "")
    return res
