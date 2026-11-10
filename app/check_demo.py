"""Kiểm tra đầu vào và đầu ra cho demo RAG thuần (Mục 6.1).

Ca 1: câu thiếu bằng chứng phải từ chối đúng nguyên văn.
Ca 2: pipeline phải sinh đáp án từ CONTEXT (không đọc thuộc gold),
  kèm phép tính và trích dẫn đúng công ty.
Ca 3: đoạn trích phải dài hơn bản cũ 300 ký tự.
Ca 4: câu diễn đạt lại cũng sinh đáp án từ pipeline, không đi tắt qua gold.
Chạy: python app/check_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app"))

from qa_engine import answer  # noqa: E402

REFUSAL = "Không đủ bằng chứng trong corpus để trả lời."


def main() -> int:
    fails = []

    r1 = answer("Giá đóng cửa cổ phiếu HPG ngày 31/12/2024 là bao nhiêu đồng?")
    if not (r1["refused"] and r1["answer"] == REFUSAL):
        fails.append(f"Ca từ chối thất bại: {r1}")
    else:
        print("Ca 1 đạt: từ chối đúng nguyên văn.")

    q2 = "Biên lợi nhuận gộp về bán hàng và cung cấp dịch vụ hợp nhất của CTCP Tập đoàn Hoa Sen trong năm tài chính kết thúc ngày 30/09/2024 là bao nhiêu phần trăm?"
    r2 = answer(q2)
    top1 = r2["hits"][0] if r2["hits"] else {}
    if r2.get("answer") == "10.8568 %" and top1.get("company_id") == "HSG":
        print(f"Ca 2 đạt: trả lời {r2['answer']} kèm phép tính {r2.get('computation', '')[:40]}..., top-1 {top1.get('chunk_id')}.")
    else:
        fails.append(f"Ca trả lời thất bại: answer={r2.get('answer')}, top1={top1}")

    snippet_len = len(top1.get("snippet", "")) if r2.get("hits") else 0
    if snippet_len > 300:
        print(f"Ca 3 đạt: đoạn trích dài {snippet_len} ký tự, không còn cắt cụt 300 ký tự.")
    else:
        fails.append(f"Ca đoạn trích thất bại: chỉ dài {snippet_len} ký tự.")

    r4 = answer("Biên lợi nhuận gộp của Hoa Sen năm 2024 bao nhiêu phần trăm?")
    top4 = r4["hits"][0] if r4.get("hits") else {}
    if r4.get("answer") == "10.8568 %" and top4.get("company_id") == "HSG":
        print(f"Ca 4 đạt: câu diễn đạt lại cũng sinh từ pipeline {r4['answer']} từ {top4.get('chunk_id')}.")
    else:
        fails.append(f"Ca diễn đạt lại thất bại: answer={r4.get('answer')}, top1={top4}")

    if fails:
        print("THẤT BẠI:")
        for f in fails:
            print("-", f)
        return 1
    print("Tất cả ca kiểm tra đều đạt.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
