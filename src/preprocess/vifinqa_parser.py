"""Tiện ích đọc và chuẩn hóa báo cáo tài chính OCR của ViFinQA.

Báo cáo trong dataset là file text, mỗi trang ngăn cách bằng "===== PAGE n =====",
bên trong có văn bản thô xen kẽ bảng ở dạng HTML (<table><tr><td>...).

Hàm ở đây giữ nguyên dấu tiếng Việt và chuẩn Unicode NFC.
"""

from __future__ import annotations

import html
import re
import unicodedata

PAGE_RE = re.compile(r"^===== PAGE (\d+) =====$")
TABLE_RE = re.compile(r"<table\b.*?</table>", re.DOTALL | re.IGNORECASE)
ROW_RE = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.DOTALL | re.IGNORECASE)
CELL_RE = re.compile(r"<t[dh]\b([^>]*)>(.*?)</t[dh]>", re.DOTALL | re.IGNORECASE)
ROWSPAN_RE = re.compile(r"rowspan\s*=\s*[\"']?(\d+)", re.IGNORECASE)
COLSPAN_RE = re.compile(r"colspan\s*=\s*[\"']?(\d+)", re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]+>")


def nfc(text: str) -> str:
    """Chuẩn hóa Unicode NFC, giữ nguyên dấu tiếng Việt."""
    return unicodedata.normalize("NFC", text)


def strip_tags(fragment: str) -> str:
    """Bỏ thẻ HTML và giải mã entity, giữ nguyên dấu tiếng Việt."""
    text = TAG_RE.sub(" ", fragment)
    text = html.unescape(text)
    text = text.replace(" ", " ").replace("&nbsp;", " ")
    return re.sub(r"[ \t]+", " ", text).strip()


def parse_table(table_html: str) -> list[list[str]]:
    """Parse một bảng HTML thành ma trận ô (text).

    Xử lý rowspan bằng cách điền lại giá trị của ô gốc vào các dòng kế tiếp
    của cùng cột, và colspan bằng cách lặp giá trị sang các cột kế tiếp.
    """
    rows: list[list[str]] = []
    # pending[(row_index, col_index)] = (value, số dòng còn lại)
    pending: dict[tuple[int, int], tuple[str, int]] = {}

    for raw_row in ROW_RE.findall(table_html):
        cells = CELL_RE.findall(raw_row)
        if not cells:
            continue
        values: list[str] = []
        spans: list[tuple[str, int, int]] = []
        col = 0
        for attrs, inner in cells:
            rowspan = int(ROWSPAN_RE.search(attrs).group(1)) if ROWSPAN_RE.search(attrs) else 1
            colspan = int(COLSPAN_RE.search(attrs).group(1)) if COLSPAN_RE.search(attrs) else 1
            value = nfc(strip_tags(inner))
            for _ in range(colspan):
                values.append(value)
                if rowspan > 1:
                    spans.append((value, rowspan, col))
                col += 1
        row_index = len(rows)
        # điền ô có rowspan từ dòng trước
        for (r, c), (val, left) in list(pending.items()):
            if r == row_index and left > 0:
                while len(values) <= c:
                    values.append("")
                values[c] = val
                if left - 1 <= 0:
                    del pending[(r, c)]
                else:
                    pending[(r, c)] = (val, left - 1)
        for value, rowspan, c in spans:
            if rowspan > 1:
                pending[(row_index, c)] = (value, rowspan - 1)
        rows.append(values)

    # đồng nhất số cột
    width = max((len(r) for r in rows), default=0)
    return [r + [""] * (width - len(r)) for r in rows]


def split_pages(raw_text: str) -> list[tuple[int, str]]:
    """Chia nội dung file thành danh sách (page_number, page_content)."""
    pages: list[tuple[int, str]] = []
    current_no: int | None = None
    buffer: list[str] = []

    for line in raw_text.splitlines():
        match = PAGE_RE.match(line.strip())
        if match:
            if current_no is not None:
                pages.append((current_no, "\n".join(buffer).strip()))
            current_no = int(match.group(1))
            buffer = []
        else:
            buffer.append(line)

    if current_no is not None:
        pages.append((current_no, "\n".join(buffer).strip()))
    elif buffer:
        pages.append((1, "\n".join(buffer).strip()))
    return pages


def parse_document(raw_text: str) -> list[dict]:
    """Tách tài liệu thành các trang, mỗi trang có text thô và các bảng đã parse.

    Mỗi trang trả về dict: page, text, tables (list of ma trận ô), n_tables.
    """
    documents: list[dict] = []
    for page_no, content in split_pages(raw_text):
        tables = [parse_table(t) for t in TABLE_RE.findall(content)]
        text = nfc(TABLE_RE.sub(" ", content))
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        documents.append(
            {
                "page": page_no,
                "text": text,
                "tables": tables,
                "n_tables": len(tables),
            }
        )
    return documents


NUM_RE = re.compile(r"^\(?-?[\d.,]+\)?%?$")


def is_number_like(cell: str) -> bool:
    """Kiểm tra ô có giống số hay không (số có dấu phân cách nghìn, dấu âm, %)."""
    value = cell.strip()
    if not value:
        return False
    return bool(NUM_RE.match(value))
