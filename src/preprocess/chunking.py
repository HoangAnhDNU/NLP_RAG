"""Định nghĩa chunk cho truy hồi (tầng processed).

Quy ước chunk của dự án: 1 chunk = 1 trang báo cáo OCR.
Lý do: bảng tài chính nằm trọn trong một trang, trích dẫn theo trang
khớp với `report_id`, `source_page` và `chunk_id` trong gold.

Luồng thực tế nằm ở `src/build_chunks.py` (parse + làm sạch + gắn unit).
File này chỉ đóng vai trò tài liệu hóa quy ước chunk size/overlap cho E0:
- chunk_size: 1 trang (không cắt nhỏ trong trang).
- overlap: 0 (các trang không chồng lấn).
- chunk_id: `<document_id>#p<page:03d>`, ví dụ `HPG_2020_consolidated#p011`.
"""

from __future__ import annotations

CHUNK_UNIT = "page"
CHUNK_SIZE = 1
CHUNK_OVERLAP = 0


def chunk_id(document_id: str, page: int) -> str:
    """Tạo chunk_id ổn định từ document_id và số trang."""
    return f"{document_id}#p{page:03d}"
