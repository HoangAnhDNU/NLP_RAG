"""Sinh 15 câu gold bổ sung để đủ định mức 50 câu (35 ViFinQA khớp + 15 tự tạo).

Gồm 7 câu trả lời được (đáp án trích trực tiếp từ chunk, script tự kiểm chứng
chuỗi bằng chứng có mặt trong chunks.jsonl) và 8 câu thiếu bằng chứng
(script kiểm chứng chủ đề vắng mặt hoàn toàn trong corpus).

Đáp án số được tính bằng script, không tính tay. Quy tắc làm tròn:
4 chữ số thập phân cho đơn vị chuyển đổi và tỷ lệ phần trăm.

Ví dụ:
    python src/build_supplement_gold.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
CHUNKS = ROOT / "data" / "processed" / "chunks.jsonl"
OUT_DIR = ROOT / "data" / "annotations"
OUT_JSONL = OUT_DIR / "qa_gold_supplement.jsonl"

REVIEWER = "member-1"
REVIEW_STATUS = "draft-needs-second-reviewer"


def load_chunks() -> dict:
    rows = [json.loads(line) for line in open(CHUNKS, encoding="utf-8")]
    return {(r["document_id"], r["page"]): r for r in rows}


def must_contain(chunk: dict, snippet: str) -> str:
    assert snippet in chunk["text"], f"Không tìm thấy bằng chứng trong {chunk['chunk_id']}: {snippet[:80]}"
    return snippet


def main() -> int:
    idx = load_chunks()
    all_text = "\n".join(r["text"] for r in idx.values())
    records: list[dict] = []

    def answerable(
        qid: str,
        question: str,
        answer_type: str,
        value,
        unit: str,
        company_id: str,
        fiscal_year: int,
        report_id: str,
        page: int,
        evidence_lines: list[str],
        computation: str = "",
    ) -> dict:
        chunk = idx[(report_id, page)]
        for line in evidence_lines:
            must_contain(chunk, line)
        if answer_type == "numeric":
            gold = f"{value} {unit}".strip()
        else:
            gold = f"{value} {unit}".strip()
        return {
            "question_id": qid,
            "question": question,
            "gold_answer": gold,
            "answer_type": answer_type,
            "value": value,
            "unit": unit,
            "company_id": company_id,
            "fiscal_year": fiscal_year,
            "report_id": report_id,
            "evidence": [
                {
                    "chunk_id": chunk["chunk_id"],
                    "source_page": page,
                    "quote": line,
                }
                for line in evidence_lines
            ],
            "computation": computation,
            "source_page": page,
            "needs_more_evidence": False,
            "reviewer_id": REVIEWER,
            "review_status": REVIEW_STATUS,
        }

    def unanswerable(
        qid: str,
        question: str,
        company_id: str,
        fiscal_year: int,
        absent_terms: list[str],
        reason: str,
    ) -> dict:
        for term in absent_terms:
            count = sum(1 for r in idx.values() if term.lower() in r["text"].lower())
            assert count == 0, f"Chủ đề '{term}' vẫn xuất hiện ở {count} chunk, không dùng làm câu thiếu bằng chứng"
        return {
            "question_id": qid,
            "question": question,
            "gold_answer": "Không đủ bằng chứng trong corpus để trả lời.",
            "answer_type": "unanswerable",
            "value": "",
            "unit": "",
            "company_id": company_id,
            "fiscal_year": fiscal_year,
            "report_id": "",
            "evidence": [],
            "computation": "",
            "source_page": "",
            "needs_more_evidence": True,
            "reviewer_id": REVIEWER,
            "review_status": REVIEW_STATUS,
            "unanswerable_reason": reason,
        }

    # ---- 7 câu trả lời được ----

    # S_NEW_01: doanh thu thuần HSG 2024, đơn vị nghìn tỷ đồng
    raw = 39271893738448
    v = round(raw / 1e12, 4)
    records.append(
        answerable(
            "S_NEW_01",
            "Doanh thu thuần về bán hàng và cung cấp dịch vụ hợp nhất của CTCP Tập đoàn Hoa Sen "
            "trong năm tài chính kết thúc ngày 30/09/2024 là bao nhiêu nghìn tỷ đồng?",
            "numeric",
            v,
            "nghìn tỷ đồng",
            "HSG",
            2024,
            "HSG_2024_consolidated",
            9,
            ["30.9.2024 VND | 30.9.2023 VND",
             "10 | Doanh thu thuần về bán hàng và cung cấp dịch vụ | 26 | 39.271.893.738.448 | 31.650.660.956.650"],
            computation=f"{raw} VND / 1e12 = {v} nghìn tỷ đồng (làm tròn 4 chữ số thập phân).",
        )
    )

    # S_NEW_02: lợi nhuận sau thuế NKG 2024, đơn vị triệu đồng
    raw = 453008144440
    v = round(raw / 1e6, 4)
    records.append(
        answerable(
            "S_NEW_02",
            "Lợi nhuận sau thuế TNDN hợp nhất của CTCP Thép Nam Kim năm 2024 là bao nhiêu triệu đồng?",
            "numeric",
            v,
            "triệu đồng",
            "NKG",
            2024,
            "NKG_2024_consolidated",
            11,
            ["2024 VND | 2023 VND",
             "60 | Lợi nhuận sau thuế TNDN | | 453.008.144.440 | 117.408.565.158"],
            computation=f"{raw} VND / 1e6 = {v} triệu đồng (làm tròn 4 chữ số thập phân).",
        )
    )

    # S_NEW_03: doanh thu thuần MSR 2024, báo cáo ghi nghìn VND, hỏi tỷ đồng
    raw_nghin = 14336328727
    v = round(raw_nghin * 1000 / 1e9, 4)
    records.append(
        answerable(
            "S_NEW_03",
            "Doanh thu thuần về bán hàng và cung cấp dịch vụ hợp nhất của CTCP Masan High-Tech Materials "
            "năm 2024 là bao nhiêu tỷ đồng?",
            "numeric",
            v,
            "tỷ đồng",
            "MSR",
            2024,
            "MSR_2024_consolidated",
            11,
            ["| Mã số | Thuyết minh | 2024Nghìn VND | 2023Nghìn VND",
             "Doanh thu thuần về bán hàng và cung cấp dịch vụ (10 = 01 - 02) | 10 | 28 | 14.336.328.727 | 14.093.253.487"],
            computation=f"{raw_nghin} nghìn VND x 1000 / 1e9 = {v} tỷ đồng (làm tròn 4 chữ số thập phân).",
        )
    )

    # S_NEW_04: tiền và tương đương tiền, bản riêng HPG 2024, hỏi tỷ đồng
    raw = 319257876941
    v = round(raw / 1e9, 4)
    records.append(
        answerable(
            "S_NEW_04",
            "Tiền và các khoản tương đương tiền của công ty mẹ CTCP Tập đoàn Hòa Phát "
            "tại ngày 31/12/2024 là bao nhiêu tỷ đồng?",
            "numeric",
            v,
            "tỷ đồng",
            "HPG",
            2024,
            "HPG_2024_separate",
            7,
            ["| Mã số | Thuyết minh | 31/12/2024 VND | 1/1/2024 VND",
             "Tiền và các khoản tương đương tiền | 110 | 4 | 319.257.876.941 | 140.727.541.395"],
            computation=f"{raw} VND / 1e9 = {v} tỷ đồng (làm tròn 4 chữ số thập phân).",
        )
    )

    # S_NEW_05: tiền và tương đương tiền HSG hợp nhất 2024, hỏi tỷ đồng
    raw = 602071799277
    v = round(raw / 1e9, 4)
    records.append(
        answerable(
            "S_NEW_05",
            "Tiền và các khoản tương đương tiền hợp nhất của CTCP Tập đoàn Hoa Sen "
            "tại ngày 30/09/2024 là bao nhiêu tỷ đồng?",
            "numeric",
            v,
            "tỷ đồng",
            "HSG",
            2024,
            "HSG_2024_consolidated",
            7,
            ["30.9.2024 VND | 30.9.2023 VND",
             "110 | Tiền và các khoản tương đương tiền | 3 | 602.071.799.277 | 596.862.912.861"],
            computation=f"{raw} VND / 1e9 = {v} tỷ đồng (làm tròn 4 chữ số thập phân).",
        )
    )

    # S_NEW_06: lãi cơ bản trên cổ phiếu NKG 2024
    records.append(
        answerable(
            "S_NEW_06",
            "Lãi cơ bản trên cổ phiếu hợp nhất của CTCP Thép Nam Kim năm 2024 là bao nhiêu đồng?",
            "numeric",
            1434,
            "đồng",
            "NKG",
            2024,
            "NKG_2024_consolidated",
            11,
            ["2024 VND | 2023 VND",
             "70 | Lãi cơ bản trên cổ phiếu | 23 | 1.434 | 357"],
            computation="Ô bảng ghi 1.434 theo quy ước dấu chấm phân cách nghìn, tức 1434 đồng.",
        )
    )

    # S_NEW_07: biên lợi nhuận gộp HSG 2024, cần phép tính
    tu = 4263666396467
    mau = 39271893738448
    v = round(tu / mau * 100, 4)
    records.append(
        answerable(
            "S_NEW_07",
            "Biên lợi nhuận gộp về bán hàng và cung cấp dịch vụ hợp nhất của CTCP Tập đoàn Hoa Sen "
            "trong năm tài chính kết thúc ngày 30/09/2024 là bao nhiêu phần trăm?",
            "computation",
            v,
            "%",
            "HSG",
            2024,
            "HSG_2024_consolidated",
            9,
            ["10 | Doanh thu thuần về bán hàng và cung cấp dịch vụ | 26 | 39.271.893.738.448 | 31.650.660.956.650",
             "20 | Lợi nhuận gộp về bán hàng và cung cấp dịch vụ | | 4.263.666.396.467 | 3.060.642.089.644"],
            computation=f"Biên gộp = {tu} / {mau} x 100 = {v}% (làm tròn 4 chữ số thập phân).",
        )
    )

    # ---- 8 câu thiếu bằng chứng ----

    records.append(
        unanswerable(
            "S_NEW_08",
            "Giá đóng cửa cổ phiếu HPG ngày 31/12/2024 là bao nhiêu đồng?",
            "HPG",
            2024,
            ["giá đóng cửa"],
            "Corpus chỉ gồm báo cáo tài chính, không có dữ liệu giá thị trường. "
            "Cụm giá đóng cửa vắng mặt hoàn toàn trong corpus.",
        )
    )
    records.append(
        unanswerable(
            "S_NEW_09",
            "Vốn hóa thị trường của CTCP Tập đoàn Hoa Sen tại ngày 30/09/2024 là bao nhiêu tỷ đồng?",
            "HSG",
            2024,
            ["vốn hóa thị trường", "thị giá"],
            "Từ vốn hóa trong corpus chỉ dùng cho chi phí đi vay được vốn hóa, "
            "không có vốn hóa thị trường hay thị giá.",
        )
    )
    records.append(
        unanswerable(
            "S_NEW_10",
            "Doanh thu thuần quý 1 năm 2024 của CTCP Tập đoàn Hòa Phát là bao nhiêu tỷ đồng?",
            "HPG",
            2024,
            ["quý 1", "quý i", "quý 1/2024", "theo quý"],
            "Corpus chỉ có báo cáo năm, không có báo cáo quý. "
            "Mọi biến thể của quý 1 đều vắng mặt.",
        )
    )
    records.append(
        unanswerable(
            "S_NEW_11",
            "Lợi nhuận sau thuế 6 tháng đầu năm 2024 của CTCP Thép Nam Kim là bao nhiêu tỷ đồng?",
            "NKG",
            2024,
            ["6 tháng đầu năm", "bán niên"],
            "Corpus chỉ có báo cáo năm, không có báo cáo bán niên. "
            "Cả hai cụm đều vắng mặt hoàn toàn.",
        )
    )
    records.append(
        unanswerable(
            "S_NEW_12",
            "Kế hoạch doanh thu năm 2025 của CTCP Tập đoàn Hoa Sen là bao nhiêu nghìn tỷ đồng?",
            "HSG",
            2025,
            ["kế hoạch doanh thu năm 2025"],
            "Báo cáo tài chính ghi nhận số đã thực hiện, không có kế hoạch năm sau. "
            "Cụm kế hoạch doanh thu năm 2025 vắng mặt hoàn toàn.",
        )
    )
    records.append(
        unanswerable(
            "S_NEW_13",
            "Dự báo lợi nhuận sau thuế năm 2025 của CTCP Masan High-Tech Materials là bao nhiêu tỷ đồng?",
            "MSR",
            2025,
            ["dự báo lợi nhuận"],
            "Báo cáo tài chính không chứa dự báo lợi nhuận tương lai. "
            "Cụm dự báo lợi nhuận vắng mặt hoàn toàn.",
        )
    )
    records.append(
        unanswerable(
            "S_NEW_14",
            "Giá bán bình quân thép HRC của CTCP Tập đoàn Hòa Phát năm 2024 là bao nhiêu đồng một tấn?",
            "HPG",
            2024,
            ["giá thép hrc", "giá quặng sắt"],
            "Báo cáo tài chính không công bố giá bán theo sản phẩm. "
            "Cả hai cụm giá đều vắng mặt hoàn toàn.",
        )
    )
    records.append(
        unanswerable(
            "S_NEW_15",
            "Tổng số cổ đông của CTCP Thép Nam Kim tại ngày 31/12/2024 là bao nhiêu người?",
            "NKG",
            2024,
            ["tổng số cổ đông"],
            "Báo cáo tài chính không công bố tổng số cổ đông. "
            "Cụm tổng số cổ đông vắng mặt hoàn toàn.",
        )
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSONL, "w", encoding="utf-8", newline="\n") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    n_ok = sum(1 for r in records if not r["needs_more_evidence"])
    n_no = sum(1 for r in records if r["needs_more_evidence"])
    print(f"Đã ghi {len(records)} câu ({n_ok} trả lời được, {n_no} thiếu bằng chứng) -> {OUT_JSONL}")
    for r in records:
        print(f"  {r['question_id']:<10} {r['answer_type']:<12} {str(r['value'])[:24]:<24} {r['unit']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
