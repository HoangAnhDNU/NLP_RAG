"""Nhận diện doanh nghiệp và năm được nhắc tới trong câu hỏi ViFinQA.

Bộ khớp dùng ba tín hiệu, theo thứ tự ưu tiên:

1. Mã CK trong ngoặc, ví dụ "CTCP Tập đoàn Hòa Phát (HPG)".
2. Mã CK viết tắt đứng riêng, ví dụ "công ty mẹ SCR năm 2017".
3. Tên công ty trong câu hỏi: so khớp chuỗi từ liên tiếp của tên đầy đủ.
   Nếu tên đầy đủ không khớp (câu hỏi dùng tên rút gọn), mới thử so khớp
   theo "chữ ký" là các từ còn lại sau khi loại từ chỉ định danh, và chỉ
   chấp nhận khi chữ ký không gồm từ quá phổ biến.

Cách so khớp theo chuỗi liên tiếp tránh nhầm "Ngân hàng TMCP Sài Gòn Tài Lộc"
với "Ngân hàng TMCP Sài Gòn - Hà Nội".

Dấu tiếng Việt được giữ nguyên trong dữ liệu, chỉ bỏ dấu tạm thời để so khớp.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "vifinqa"

YEAR_RE = re.compile(r"\b(20[0-2]\d)\b")
PAREN_TICKER_RE = re.compile(r"\(([A-Z]{2,5})\)")
BARE_TICKER_RE = re.compile(r"(?<![A-Za-zÀ-ỹ])([A-Z]{2,5})(?![A-Za-zÀ-ỹ])")

# Từ chỉ định danh loại bỏ khi tạo chữ ký tên công ty.
GENERIC_TOKENS = {
    "ctcp", "cong", "ty", "tong", "ngan", "hang", "tmcp", "tap", "doan",
    "chung", "nhom", "thuong", "dich", "vu", "xuat", "khau", "nha", "may",
    "thuc", "pham", "san", "phat", "trien", "mua", "ban", "gia", "thanh",
    "minh", "hoa", "bao", "quoc", "the", "gioi", "dien", "luc", "khi", "dau",
    "sach", "ruou", "nuoc", "giai", "khat", "chuc", "nang", "luyen", "kim",
    "quang", "ninh", "phuoc", "vinh", "hai", "duong", "bac", "trung", "doanh",
    "nghiep",
}

# Viết tắt không phải mã cổ phiếu, xuất hiện trong câu hỏi tài chính.
NON_TICKER = {
    "CTCP", "TMCP", "TCTD", "TNHH", "CFO", "ROE", "ROA", "EPS", "TNDN", "LNST",
    "LNTT", "BCTC", "USD", "VND", "BIDV", "CHKQT", "VAMC", "PTN", "SG", "MTV",
    "WWW", "VAT", "OCI", "AMC", "GELEX", "TKV", "PC", "CP", "HT", "NPO",
    "FPS", "TNC", "QTS",
}

# Từ cần giữ riêng vì bỏ dấu sẽ trùng với từ khác.
# "năm" bỏ dấu thành "nam", trùng với "Đông Nam Á" và "Nam Long".
_PLACEHOLDER_WORDS = [
    "năm", "công", "tổng", "sản", "tập", "đoàn", "ngân", "hàng", "chứng",
    "khoán", "thị", "trường", "đầu", "phát", "triển", "thương", "mại", "dịch",
    "vụ", "nhà", "máy", "thực", "phẩm", "xuất", "khẩu", "giá", "đức", "lâm",
    "nghiệp", "đông", "điện", "lực", "hóa", "chất", "phân", "bón", "màu",
    "đường", "quảng", "ngãi", "phú", "nhuận", "hợp", "phát",
]
_PLACEHOLDER_RE = re.compile(
    r"\b(" + "|".join(sorted(set(_PLACEHOLDER_WORDS), key=len, reverse=True)) + r")\b"
)
_PLACEHOLDER_MAP = {word: f"z{index}" for index, word in enumerate(sorted(set(_PLACEHOLDER_WORDS)))}
_PLACEHOLDER_MAP.update({word: f"z{index}" for index, word in enumerate(_PLACEHOLDER_WORDS)})

# Bảng tra dấu tiếng Việt, dựng sẵn để tránh gọi unicodedata nhiều lần.
_ACCENT_MAP = {ord(c): c for c in "aàáảãạăằắẳẵặâầấẩẫậ"}
_ACCENT_MAP.update({ord(c): "a" for c in "àáảãạăằắẳẵặâầấẩẫậ"})
_ACCENT_MAP.update({ord(c): "e" for c in "èéẻẽẹêềếểễệ"})
_ACCENT_MAP.update({ord(c): "i" for c in "ìíỉĩị"})
_ACCENT_MAP.update({ord(c): "o" for c in "òóỏõọôồốổỗộơờớởỡợ"})
_ACCENT_MAP.update({ord(c): "u" for c in "ùúủũụưừứửữự"})
_ACCENT_MAP.update({ord(c): "y" for c in "ỳýỷỹỵ"})
_ACCENT_MAP[ord("đ")] = "d"
_ACCENT_MAP[ord("Đ")] = "D"

# Ngưỡng xuất hiện để coi là từ phổ biến, không dùng làm chữ ký.
COMMON_TOKEN_RATIO = 0.02

_WORD_RE = re.compile(r"[a-z0-9]+")


def deaccent(text: str) -> str:
    """Bỏ dấu tiếng Việt để so khớp. Chỉ dùng nội bộ, không để ghi ra dữ liệu."""
    text = text.lower()
    text = _PLACEHOLDER_RE.sub(lambda m: _PLACEHOLDER_MAP.get(m.group(1), m.group(1)), text)
    return text.translate(_ACCENT_MAP)


def tokenize(text: str) -> list[str]:
    """Chuẩn hóa thành danh sách từ không dấu."""
    return _WORD_RE.findall(deaccent(text))


def content_tokens(text: str) -> list[str]:
    """Danh sách từ đã loại từ chỉ định danh.

    Token placeholder (tiền tố "z") sinh ra khi bỏ dấu cũng bị loại, vì các từ
    đó vốn đã là từ chỉ định danh ("năm", "công ty", "tập đoàn", ...).
    """
    return [
        t
        for t in tokenize(text)
        if t not in GENERIC_TOKENS and not t.startswith("z")
    ]


def load_companies() -> dict[str, str]:
    """Đọc code_stock.csv, trả về {mã CK: tên công ty}."""
    path = RAW / "code_stock.csv"
    companies: dict[str, str] = {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            code = row["Mã CK"].strip().upper()
            name = row["Tên công ty"].strip()
            if code:
                companies[code] = name
    return companies


def build_signatures(companies: dict[str, str], common_tokens: set[str] | None = None) -> dict[str, list[str]]:
    """Chữ ký của mỗi doanh nghiệp: các từ còn lại sau khi loại từ chỉ định danh.

    Nếu biết danh sách từ phổ biến, chữ ký chỉ giữ lại những từ không phổ biến.
    """
    signatures: dict[str, list[str]] = {}
    for code, name in companies.items():
        toks = [t for t in content_tokens(name) if len(t) >= 3]
        if common_tokens is not None:
            distinctive = [t for t in toks if t not in common_tokens]
            if distinctive:
                toks = distinctive
        if toks:
            signatures[code] = toks
    return signatures


def _contains_sequence(haystack: list[str], needle: list[str]) -> bool:
    """Kiểm tra needle xuất hiện liên tiếp trong haystack."""
    n = len(needle)
    if n == 0 or n > len(haystack):
        return False
    for i in range(len(haystack) - n + 1):
        if haystack[i : i + n] == needle:
            return True
    return False


def detect_companies(
    question: str,
    companies: dict[str, str],
    signatures: dict[str, list[str]] | None = None,
) -> list[str]:
    """Trả về danh sách mã CK được nhắc tới trong câu hỏi."""
    if signatures is None:
        signatures = build_signatures(companies)

    found: list[str] = []

    # 1. mã CK trong ngoặc
    for code in PAREN_TICKER_RE.findall(question):
        if code in companies and code not in found:
            found.append(code)

    # 2. mã CK viết tắt đứng riêng
    for code in BARE_TICKER_RE.findall(question):
        if code in NON_TICKER or code in found:
            continue
        if code in companies:
            found.append(code)

    if found:
        return found

    # 3a. tên đầy đủ xuất hiện liên tiếp trong câu hỏi
    q_tokens = tokenize(question)
    for code, name in companies.items():
        name_tokens = tokenize(name)
        if name_tokens and _contains_sequence(q_tokens, name_tokens):
            found.append(code)

    if found:
        return found

    # 3b. chữ ký tên rút gọn
    q_content = content_tokens(question)
    for code, sig in signatures.items():
        if _contains_sequence(q_content, sig):
            found.append(code)

    return found


def detect_years(question: str) -> list[int]:
    """Các năm dạng 4 chữ số xuất hiện trong câu hỏi, đã sắp xếp."""
    return sorted({int(y) for y in YEAR_RE.findall(question)})


def common_tokens_in_questions(questions: list[str], ratio: float = COMMON_TOKEN_RATIO) -> set[str]:
    """Từ xuất hiện trong tỷ lệ lớn câu hỏi, coi là từ phổ biến."""
    if not questions:
        return set()
    counter: Counter = Counter()
    for q in questions:
        counter.update(set(tokenize(q)))
    threshold = max(2, int(len(questions) * ratio))
    return {token for token, count in counter.items() if count >= threshold}
