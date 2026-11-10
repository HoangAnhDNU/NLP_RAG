"""Chuẩn hóa văn bản tiếng Việt: NFC, giữ dấu.

Mọi văn bản trong pipeline đều qua `nfc()` trước khi tokenize, index hay so khớp.
Bỏ dấu chỉ dùng tạm thời trong `company_match.py`, không dùng ở đây.
"""

from __future__ import annotations

import re
import unicodedata

_WS_RE = re.compile(r"\s+")
_TOKEN_RE = re.compile(r"[a-zà-ỹ0-9_%.,/+-]+", re.IGNORECASE)


def nfc(text: str) -> str:
    """Chuẩn hóa Unicode NFC, giữ nguyên dấu tiếng Việt."""
    return unicodedata.normalize("NFC", text)


def normalize_query(text: str) -> str:
    """Chuẩn hóa query: NFC, chữ thường, gọn khoảng trắng, giữ số và dấu %."""
    text = nfc(text).lower().strip()
    return _WS_RE.sub(" ", text)


def tokenize_vi(text: str) -> list[str]:
    """Tách từ tiếng Việt đơn giản: chữ thường, giữ dấu, giữ số."""
    return _TOKEN_RE.findall(nfc(text).lower())
