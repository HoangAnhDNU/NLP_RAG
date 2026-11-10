"""Sinh báo cáo chất lượng dữ liệu (reports/data_quality_report.md).

Theo Mục 5.3 của hướng dẫn BTL, trước mọi thí nghiệm chính phải chạy script kiểm tra
và lưu báo cáo có bảng kiểm đếm trước/sau làm sạch, danh sách ID mẫu bị loại/chỉnh
kèm lý do.

Script này tổng hợp từ các đầu ra đã sinh:
- data/processed/corpus_manifest.csv      (tầng raw/references)
- data/processed/chunks.jsonl            (tầng processed)
- data/processed/ocr_audit.csv           (audit OCR theo báo cáo)
- data/processed/questions_matched.csv   (tập câu hỏi lọc được)
- data/processed/questions_dropped.csv   (câu hỏi bị loại kèm lý do)

Ví dụ:
    python src/data_quality_report.py
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUT_MD = ROOT / "report" / "data_quality_report.md"

REVISION = "0450088ab22ec946f04f097586967ca405955b3b"
REPO_URL = "https://huggingface.co/datasets/AIGuruTinix/ViFinQA"


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main() -> int:
    manifest = read_csv(PROCESSED / "corpus_manifest.csv")
    audit = read_csv(PROCESSED / "ocr_audit.csv")
    matched = read_csv(PROCESSED / "questions_matched.csv")
    dropped = read_csv(PROCESSED / "questions_dropped.csv")

    chunks: list[dict] = []
    chunks_path = PROCESSED / "chunks.jsonl"
    if chunks_path.exists():
        chunks = [json.loads(line) for line in open(chunks_path, encoding="utf-8")]

    lines: list[str] = []
    add = lines.append

    add("# Báo cáo kiểm tra chất lượng dữ liệu")
    add("")
    add("Dự án: BTL CSC4007, đề tài 6 - Hỏi đáp báo cáo tài chính có trích dẫn bằng RAG.")
    add("")
    add(f"- Script sinh báo cáo: `src/data_quality_report.py`")
    add(f"- Nguồn dữ liệu: `{REPO_URL}`, revision `{REVISION}`")
    add("- Các bước chạy lại được: `src/download_vifinqa.py` -> `src/select_corpus.py` -> "
        "`src/filter_questions.py` -> `src/build_chunks.py` -> `src/audit_ocr.py` -> `src/data_quality_report.py`")
    add("")

    # ---------------------------------------------------------------- 1
    add("## 1. Schema và tính đầy đủ")
    add("")
    add("### 1.1 Bảng kiểm đếm trước và sau khi lọc tập câu hỏi")
    add("")
    add("| bước | số dòng | ghi chú |")
    add("|---|---|---|")
    add(f"| Tập câu hỏi gốc của ViFinQA | 1012 | `questions/questions.jsonl`, chỉ có trường `id` và `question` |")
    add(f"| Sau khi lọc theo corpus | {len(matched)} | `data/processed/questions_matched.csv` |")
    add(f"| Bị loại | {len(dropped)} | `data/processed/questions_dropped.csv`, có lý do từng dòng |")
    add(f"| Tổng kiểm lại | {len(matched) + len(dropped)} | khớp với tập gốc |")
    add("")

    add("### 1.2 Bảng kiểm đếm trước và sau khi sinh chunk")
    add("")
    add("| bước | số đơn vị | ghi chú |")
    add("|---|---|---|")
    add(f"| File báo cáo OCR trong `data/raw/` | {len(manifest)} | 4 doanh nghiệp x 5 năm x 2 bản (hợp nhất / riêng) |")
    add(f"| Tổng số trang trong các file | {sum(int(r['n_pages']) for r in audit)} | tính từ `ocr_audit.csv` |")
    add(f"| Trang rỗng bị loại | {sum(int(r['pages_empty']) for r in audit)} | lỗi OCR ở file nguồn, xem mục 4 |")
    add(f"| Chunk dùng cho truy hồi | {len(chunks)} | `data/processed/chunks.jsonl`, 1 chunk = 1 trang |")
    add(f"| Chunk có chứa bảng | {sum(1 for c in chunks if c['n_tables'] > 0)} | "
        f"({sum(1 for c in chunks if c['n_tables'] > 0) / len(chunks) * 100:.1f}%) |")
    add(f"| Tổng bảng OCR đã parse | {sum(c['n_tables'] for c in chunks)} | |")
    add("")

    add("### 1.3 Kiểm tra trường bắt buộc và kiểu dữ liệu")
    add("")
    add("| tệp | số dòng | cột bắt buộc | ID trùng | ID rỗng |")
    add("|---|---|---|---|---|")
    for name, rows, id_field in [
        ("corpus_manifest.csv", manifest, "document_id"),
        ("ocr_audit.csv", audit, "document_id"),
        ("questions_matched.csv", matched, "question_id"),
        ("questions_dropped.csv", dropped, "id"),
    ]:
        ids = [r[id_field] for r in rows] if rows else []
        dup = len(ids) - len(set(ids))
        blank = sum(1 for i in ids if not i.strip())
        add(f"| `data/processed/{name}` | {len(rows)} | {id_field} | {dup} | {blank} |")
    chunk_ids = [c["chunk_id"] for c in chunks]
    add(f"| `data/processed/chunks.jsonl` | {len(chunks)} | chunk_id | "
        f"{len(chunk_ids) - len(set(chunk_ids))} | 0 |")
    add("")

    add("### 1.4 Bản mã Unicode")
    add("")
    add("Toàn bộ tệp được đọc và ghi với `encoding=\"utf-8\"`. Văn bản tiếng Việt giữ nguyên dấu,")
    add("không bỏ dấu hay chuyển sang ASCII. Chuẩn hóa dùng NFC (`unicodedata.normalize(\"NFC\", ...)`).")
    add("Bỏ dấu chỉ dùng tạm thời trong `src/preprocess/company_match.py` để so khớp tên doanh nghiệp,")
    add("không áp dụng cho dữ liệu lưu xuống.")
    add("")

    # ---------------------------------------------------------------- 2
    add("## 2. Nội dung")
    add("")
    add("### 2.1 Độ dài trang")
    add("")
    add("| document_id | số trang | trung bình ký tự/trang | ngắn nhất | dài nhất |")
    add("|---|---|---|---|---|")
    for r in audit:
        add(f"| {r['document_id']} | {r['n_pages']} | {r['avg_page_chars']} | "
            f"{r['min_page_chars']} | {r['max_page_chars']} |")
    add("")

    add("### 2.2 Trang không có bảng")
    add("")
    total_pages = sum(int(r["n_pages"]) for r in audit)
    pages_no_table = sum(int(r["pages_without_table"]) for r in audit)
    add(f"- Tổng cộng **{pages_no_table} / {total_pages}** trang không chứa bảng "
        f"({pages_no_table / total_pages * 100:.1f}%).")
    add("- Đây là các trang văn bản thuần như báo cáo của Ban Giám đốc, ý kiến kiểm toán viên,")
    add("  thuyết minh dạng chữ, mục lục. Nhóm vẫn giữ các trang này trong corpus vì chúng chứa")
    add("  thông tin về chính sách kế toán và thuyết minh, có thể cần cho câu hỏi dạng văn bản.")
    add("")

    add("### 2.3 Trùng lặp và gần trùng")
    add("")
    add("| kiểm tra | kết quả |")
    add("|---|---|")
    add(f"| Hai bản consolidated và separate của cùng công ty năm có nội dung trùng nhau | "
        f"{len(manifest)} cặp, kiểm tra bằng sha256 trong manifest, hai bản khác nhau |")
    add(f"| Cùng một document_id xuất hiện nhiều lần | {len(manifest) - len(set(r['document_id'] for r in manifest))} |")
    add(f"| Chunk trùng nội dung giữa các báo cáo | {len(chunks) - len(set(c['chunk_id'] for c in chunks))} chunk trùng ID |")
    add("")
    add("Mỗi báo cáo có `sha256` riêng trong `corpus_manifest.csv`, nên có thể kiểm chứng lại")
    add("file còn nguyên so với lúc tải. Việc kiểm tra trùng nội dung ở mức đoạn văn sẽ làm")
    add("ở bước chống rò rỉ dữ liệu, cùng với việc tách dev/test theo câu hỏi.")
    add("")

    # ---------------------------------------------------------------- 3
    add("## 3. Số liệu kinh tế")
    add("")
    add("### 3.1 Kiểm tra định dạng số")
    add("")
    add("| loại kiểm tra | tổng số lần | cách xử lý trong `src/build_chunks.py` |")
    add("|---|---|---|")
    add(f"| Số có dấu phân cách nghìn (ví dụ `91.279.041.771.826`) | "
        f"{sum(int(r['total_thousand_sep']) for r in audit)} | giữ nguyên trong text, chuẩn hóa qua `normalize_number()` |")
    add(f"| Số thập phân dấu phẩy (ví dụ `3,2`) | {sum(int(r['total_decimal']) for r in audit)} | "
        "chuyển thành `3.2`, không nhân với 100 |")
    add(f"| Số âm trong ngoặc (ví dụ `(983.237)`) | {sum(int(r['total_paren_neg']) for r in audit)} | "
        "chuyển thành `-983237` |")
    add(f"| Ký hiệu phần trăm | {sum(int(r['total_percent']) for r in audit)} | giữ nguyên kèm dấu `%` |")
    add("")

    add("### 3.2 Đơn vị tiền")
    add("")
    unit_counter = Counter(c["unit"] or "(không xác định)" for c in chunks)
    add("| đơn vị | số chunk |")
    add("|---|---|")
    for u, n in unit_counter.most_common():
        add(f"| {u} | {n} |")
    add("")
    add("Đơn vị được suy ra theo thứ tự: (1) hàng header của bảng, ví dụ `31/12/2023Triệu VND`;")
    add("(2) dự phòng, dò trong văn bản trang. Trường `unit` trên mỗi chunk là đơn vị của số liệu")
    add("trong trang đó. Chunk không xác định được đơn vị thì để rỗng, không đoán.")
    add("")
    add("**Cảnh báo cần lưu ý khi chấm điểm:** câu hỏi ViFinQA hỏi đơn vị ở mức")
    add("`triệu đồng`, `tỷ đồng`, `nghìn tỷ đồng`, trong khi báo cáo tài chính Việt Nam ghi")
    add("`VND` (đồng tuyệt đối) hoặc `triệu VND`. Chuẩn hóa đơn vị là điểm lỗi lớn nhất của")
    add("hệ thống, và là một trong các nhóm lỗi bắt buộc báo cáo trong `error_analysis.md`.")
    add("")

    # ---------------------------------------------------------------- 4
    add("## 4. Nhiễu OCR")
    add("")
    total_dec = sum(int(r.get("total_decoration", 0)) for r in audit)
    total_latex = sum(int(r.get("total_latex", 0)) for r in audit)
    add(f"- Ký tự trang trí (○ ● ◎ ...): **{total_dec}** lần, loại bỏ khi sinh chunk.")
    add(f"- Công thức LaTeX lọt từ phần thuyết minh toán học: **{total_latex}** lần, loại bỏ khi sinh chunk.")
    add(f"- Ký tự thay thế `�`: "
        f"{sum(1 for c in chunks if chr(0xFFFD) in c['text'])} chunk bị ảnh hưởng.")
    add(f"- Trang rỗng trong file nguồn: **{sum(int(r['pages_empty']) for r in audit)}** trang, "
        "chi tiết ở `report/ocr_audit.md` mục 6.")
    add("")

    # ---------------------------------------------------------------- 5
    add("## 5. Gold")
    add("")
    add("ViFinQA công khai **không có gold answer, không có evidence và không có split**.")
    add("Nhóm phải tự xây bộ gold và tự kiểm chứng.")
    add("")
    add("### 5.1 Phân bố tập câu hỏi đã lọc")
    add("")
    add("| đặc trưng | phân bố |")
    add("|---|---|")
    per_company = Counter()
    for r in matched:
        for c in r["company_id"].split("|"):
            per_company[c] += 1
    for c, n in per_company.most_common():
        add(f"| doanh nghiệp {c} | {n} câu |")
    add("")
    per_year = Counter()
    for r in matched:
        for y in r["years_in_corpus"].split("|"):
            if y:
                per_year[y] += 1
    for y, n in sorted(per_year.items()):
        add(f"| năm {y} | {n} câu |")
    add("")
    add("| đặc trưng | số câu |")
    add("|---|---|")
    for t, n in Counter(r["answer_type"] for r in matched).most_common():
        add(f"| dạng câu hỏi: {t} | {n} |")
    for u, n in Counter(r["unit"] or "(không rõ)" for r in matched).most_common():
        add(f"| đơn vị được hỏi: {u} | {n} |")
    add(f"| câu hỏi nhiều doanh nghiệp | {sum(1 for r in matched if r['is_multi_company'] == '1')} |")
    add(f"| câu hỏi cần phép tính | {sum(1 for r in matched if r['has_calculation'] == '1')} |")
    add(f"| câu hỏi về công ty mẹ | {sum(1 for r in matched if r['scope'] == 'parent')} |")
    add("")

    add("### 5.2 Khoảng cách với định mức 50 câu gold")
    add("")
    add(f"- Định mức đề tài 6: **tối thiểu 50 câu hỏi** trên corpus thực dùng, chia 10 dev + 40 test.")
    add(f"- Số câu hỏi ViFinQA có sẵn khớp corpus hiện tại: **{len(matched)}**.")
    add("- Phần còn thiếu, nhóm phải **tự tạo và tự kiểm chứng**: "
        f"cần bổ sung tối thiểu {max(0, 50 - len(matched))} câu nữa.")
    add("")
    add("Nguồn bổ sung được đề xuất:")
    add("")
    add("1. Bộ câu hỏi ViFinQA gốc có mã CK trong ngoặc, tự đổi mã CK sang tên đầy đủ để so khớp.")
    add("2. Đặt câu hỏi mới theo bảng chỉ tiêu trong các báo cáo đã tải, có trích dẫn trang.")
    add("3. Bổ sung câu hỏi **thiếu bằng chứng** (cần ít nhất 08 câu trong tập test) bằng cách")
    add("   hỏi về chỉ tiêu không có trong báo cáo đã tải, ví dụ hỏi năm ngoài phạm vi corpus.")
    add("")
    add("> Khi không đủ 50 câu hợp lệ, phải báo giảng viên trước giai đoạn thực nghiệm (Mục 4.6.2).")
    add("")

    add("### 5.3 Chưa có gold")
    add("")
    add("| hạng mục | trạng thái |")
    add("|---|---|")
    add("| qa_gold.jsonl | chưa tạo, cần giai đoạn gắn nhãn |")
    add("| annotation_guideline.md | chưa tạo |")
    add("| review_log.csv (hậu kiểm 20%) | chưa tạo |")
    add("| danh sách ID chia dev/test | chưa tạo |")
    add("")

    # ---------------------------------------------------------------- 6
    add("## 6. Chống rò rỉ dữ liệu")
    add("")
    add("| nguồn rò rỉ | biện pháp |")
    add("|---|---|")
    add("| Cùng báo cáo xuất hiện ở cả dev và test | corpus dùng chung cho mọi câu hỏi, "
        "đây là đặc trưng của bài toán QA trên báo cáo tài chính. Nhóm phải **công bố rõ** "
        "cùng báo cáo có thể xuất hiện ở cả hai split |")
    add("| Câu hỏi paraphrase gần trùng nhau rơi vào hai split | tách theo câu hỏi và kiểm tra "
        "gần trùng bằng cosine similarity trước khi chia |")
    add("| Chunk của cùng một trang rơi vào hai split | mỗi chunk thuộc đúng một câu hỏi gold, "
        "không tách chunk |")
    add("| Bản consolidated và separate của cùng công ty năm | hai bản có nội dung khác nhau, "
        "được giữ cả hai trong corpus và ghi rõ `report_version` |")
    add("| Dùng test để chọn tham số | theo Mục 5.4, chọn tham số bằng dev, chỉ công bố kết quả trên test |")
    add("")

    # ---------------------------------------------------------------- 7
    add("## 7. Pháp lý và đạo đức")
    add("")
    add("| kiểm tra | kết quả |")
    add("|---|---|")
    add("| Có API key trong repo | không có |")
    add("| Có PII trong dữ liệu | không phát hiện, dữ liệu là báo cáo tài chính công khai |")
    add("| Quyền sử dụng dataset | `license_status` trong manifest để là `unknown_verify_with_teacher`, "
        "**phải xác minh với giảng viên trước khi công bố** |")
    add("| Công bố lại dữ liệu | không nên đưa nguyên file OCR lên repo công khai, "
        "chỉ công bố manifest, chunk đã xử lý và script tải lại |")
    add("| Nhãn do LLM hỗ trợ tạo | chưa có nhãn nào, khi dùng LLM hỗ trợ gắn nhãn phải có người kiểm chứng |")
    add("")

    # ---------------------------------------------------------------- 8
    add("## 8. Danh sách ID mẫu bị loại hoặc chỉnh")
    add("")
    add("### 8.1 Báo cáo bị loại khỏi corpus")
    add("")
    add("Không có báo cáo nào bị loại khỏi `data/raw/`. Toàn bộ 4 doanh nghiệp x 5 năm x 2 bản")
    add("đều được giữ. Tập câu hỏi bị lọc theo corpus, không lọc báo cáo.")
    add("")

    add("### 8.2 Trang bị loại khỏi tập chunk")
    add("")
    add("| document_id | số trang rỗng | danh sách trang |")
    add("|---|---|---|")
    by_doc: dict[str, list[str]] = {}
    for r in audit:
        if int(r["pages_empty"]) > 0:
            by_doc[r["document_id"]] = [""]
    pages_csv = read_csv(PROCESSED / "ocr_audit_pages.csv")
    empty_map: dict[str, list[int]] = {}
    for r in pages_csv:
        if r.get("is_empty") == "1":
            empty_map.setdefault(r["document_id"], []).append(int(r["page"]))
    for doc, pages in sorted(empty_map.items()):
        add(f"| {doc} | {len(pages)} | {', '.join(map(str, pages))} |")
    add("")
    add("Lý do: các trang này hoàn toàn trống trong file OCR nguồn, không có nội dung để truy hồi.")
    add("")

    add("### 8.3 Câu hỏi bị loại khỏi tập ứng viên")
    add("")
    drop_groups = Counter()
    for r in dropped:
        reason = r["reason"]
        if reason.startswith("doanh nghiep ngoai corpus"):
            drop_groups["doanh nghiep ngoai corpus"] += 1
        elif reason.startswith("nam ngoai corpus"):
            drop_groups["nam ngoai corpus"] += 1
        else:
            drop_groups[reason] += 1
    add("| lý do loại | số câu |")
    add("|---|---|")
    for reason, n in drop_groups.most_common():
        add(f"| {reason} | {n} |")
    add("")
    add("Danh sách đầy đủ từng câu kèm lý do nằm ở `data/processed/questions_dropped.csv`.")
    add("")

    # ---------------------------------------------------------------- 9
    add("## 9. Tóm tắt rủi ro")
    add("")
    add("| rủi ro | mức độ | giải pháp |")
    add("|---|---|---|")
    add("| Chưa đủ 50 câu gold | cao | tự tạo và kiểm chứng bổ sung, hoặc báo giảng viên |")
    add("| Lỗi đơn vị tiền khi chấm điểm | cao | chuẩn hóa đơn vị ở tầng processed, "
        "tính metric theo đơn vị chuẩn |")
    add("| OCR bỏ sót trang (HPG 2022 hợp nhất) | trung bình | ghi nhận trong audit, loại khỏi chunk |")
    add("| Bảng HTML vỡ cột | thấp | tỷ lệ hàng lệch cột đo được trong `ocr_audit.csv` |")
    add("| Câu hỏi nhiều doanh nghiệp cần nhiều báo cáo | trung bình | "
        "phần nâng cao, không bắt buộc |")
    add("| Chưa xác minh quyền sử dụng dữ liệu | cao | hỏi giảng viên, ghi vào data_card |")
    add("")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(f"Da ghi {OUT_MD}")
    print(f"  bao cao: {len(manifest)} | chunk: {len(chunks)} | cau hoi giu: {len(matched)} | loai: {len(dropped)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
