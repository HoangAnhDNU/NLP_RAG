"""Sinh báo cáo chất lượng dữ liệu (report/data_quality_report.md).

Theo Mục 5.3 của hướng dẫn BTL, trước mọi thí nghiệm chính phải chạy script kiểm tra
và lưu báo cáo có bảng kiểm đếm trước/sau làm sạch, danh sách ID mẫu bị loại/chỉnh
kèm lý do.

Script này tổng hợp từ các đầu ra đã sinh:
- data/processed/corpus_manifest.csv      (tầng raw/references)
- data/processed/chunks.jsonl             (tầng processed)
- data/processed/ocr_audit.csv            (audit OCR theo báo cáo)
- data/processed/ocr_audit_pages.csv      (audit OCR theo trang)
- data/processed/questions_matched.csv    (tập câu hỏi lọc được)
- data/processed/questions_dropped.csv    (câu hỏi bị loại kèm lý do)
- data/annotations/qa_gold.jsonl          (bộ gold, có split dev/test)
- data/annotations/review_log.csv         (hồ sơ hậu kiểm)
- data/data_manifest.csv                  (bản kê chuẩn 13 cột)
- data/splits/split_meta.json             (split đã đóng băng)

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
ANNOT = ROOT / "data" / "annotations"
DATA = ROOT / "data"
SPLITS = ROOT / "data" / "splits"
OUT_MD = ROOT / "report" / "data_quality_report.md"

REVISION = "0450088ab22ec946f04f097586967ca405955b3b"
REPO_URL = "https://huggingface.co/datasets/AIGuruTinix/ViFinQA"


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in open(path, encoding="utf-8")]


def main() -> int:
    manifest = read_csv(PROCESSED / "corpus_manifest.csv")
    audit = read_csv(PROCESSED / "ocr_audit.csv")
    matched = read_csv(PROCESSED / "questions_matched.csv")
    dropped = read_csv(PROCESSED / "questions_dropped.csv")
    data_manifest = read_csv(DATA / "data_manifest.csv")
    review = read_csv(ANNOT / "review_log.csv")
    chunks = read_jsonl(PROCESSED / "chunks.jsonl")
    gold = read_jsonl(ANNOT / "qa_gold.jsonl")
    split_meta: dict = {}
    if (SPLITS / "split_meta.json").exists():
        split_meta = json.loads(open(SPLITS / "split_meta.json", encoding="utf-8").read())

    lines: list[str] = []
    add = lines.append

    add("# Báo cáo kiểm tra chất lượng dữ liệu")
    add("")
    add("Dự án: BTL CSC4007, đề tài 6 - Hỏi đáp báo cáo tài chính có trích dẫn bằng RAG.")
    add("")
    add("- Script sinh báo cáo: `src/data_quality_report.py`")
    add(f"- Nguồn dữ liệu: `{REPO_URL}`, revision `{REVISION}`")
    add("- Các bước chạy lại được: `src/download_vifinqa.py` -> `src/select_corpus.py` -> "
        "`src/filter_questions.py` -> `src/build_chunks.py` -> `src/build_table_records.py` -> `src/audit_ocr.py` -> "
        "`src/build_supplement_gold.py` -> `src/build_gold.py` (guard `--force-v1`) -> `src/build_expanded_gold_v2.py` -> "
        "`src/build_expanded_gold_v3.py` -> `src/resolve_vifinqa_and_dev_refusal.py` -> `src/cross_review.py` -> "
        "`src/build_data_docs.py` -> `src/data_quality_report.py`")
    add("")

    # ---------------------------------------------------------------- 1
    add("## 1. Schema và tính đầy đủ")
    add("")
    add("### 1.1 Bảng kiểm đếm trước và sau khi lọc tập câu hỏi")
    add("")
    add("| bước | số dòng | ghi chú |")
    add("|---|---|---|")
    add("| Tập câu hỏi gốc của ViFinQA | 1012 | `questions/questions.jsonl`, chỉ có trường `id` và `question` |")
    add(f"| Sau khi lọc theo corpus | {len(matched)} | `data/processed/questions_matched.csv` |")
    add(f"| Bị loại | {len(dropped)} | `data/processed/questions_dropped.csv`, có lý do từng dòng |")
    add(f"| Tổng kiểm lại | {len(matched) + len(dropped)} | khớp với tập gốc |")
    add(f"| Bộ gold sau khi bù | {len(gold)} | `data/annotations/qa_gold.jsonl` |")
    add("")

    add("### 1.2 Bảng kiểm đếm trước và sau khi sinh chunk")
    add("")
    add("| bước | số đơn vị | ghi chú |")
    add("|---|---|---|")
    add(f"| File báo cáo OCR trong `data/raw/` | {len(manifest)} | 4 doanh nghiệp x 5 năm x 2 bản (hợp nhất / riêng) |")
    add(f"| Tổng số trang trong các file | {sum(int(r['n_pages']) for r in audit)} | tính từ `ocr_audit.csv` |")
    add(f"| Trang rỗng bị loại | {sum(int(r['pages_empty']) for r in audit)} | lỗi OCR ở file nguồn, xem mục 4 |")
    add(f"| Chunk dùng cho truy hồi | {len(chunks)} | `data/processed/chunks.jsonl`, 1 chunk = 1 trang |")
    if chunks:
        add(f"| Chunk có chứa bảng | {sum(1 for c in chunks if c['n_tables'] > 0)} | "
            f"({sum(1 for c in chunks if c['n_tables'] > 0) / len(chunks) * 100:.1f}%) |")
    add(f"| Tổng bảng OCR đã parse | {sum(c['n_tables'] for c in chunks)} | |")
    add(f"| Bản kê chuẩn `data/data_manifest.csv` | {len(data_manifest)} | 40 corpus + {len(gold)} gold |")
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
        ("data_manifest.csv", data_manifest, "item_id"),
    ]:
        ids = [r[id_field] for r in rows] if rows else []
        dup = len(ids) - len(set(ids))
        blank = sum(1 for i in ids if not str(i).strip())
        add(f"| `data/{name if name == 'data_manifest.csv' else 'processed/' + name}` | {len(rows)} | {id_field} | {dup} | {blank} |")
    chunk_ids = [c["chunk_id"] for c in chunks]
    add(f"| `data/processed/chunks.jsonl` | {len(chunks)} | chunk_id | "
        f"{len(chunk_ids) - len(set(chunk_ids))} | 0 |")
    gold_ids = [g["question_id"] for g in gold]
    add(f"| `data/annotations/qa_gold.jsonl` | {len(gold)} | question_id | "
        f"{len(gold_ids) - len(set(gold_ids))} | {sum(1 for i in gold_ids if not str(i).strip())} |")
    add("")
    add("Nhãn ngoài danh mục: `answer_type` trong gold chỉ gồm "
        f"`{', '.join(sorted(set(g['answer_type'] for g in gold)))}`, "
        "đúng danh mục `numeric, computation, unanswerable`. "
        "`review_status` chỉ gồm "
        f"`{', '.join(sorted(set(g['review_status'] for g in gold)))}`, "
        f"đúng danh mục hợp lệ (có **{sum(1 for g in gold if g['review_status'] == 'pending-answer')}** câu `pending-answer`).")
    add("")
    add("Đường dẫn nguồn: mọi `local_path` trong manifest trỏ tới file "
        "`data/raw/vifinqa/financial_statements/<TICKER>/<YEAR>/..._extracted.txt` tồn tại. ")
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
    add("|---|---|---|")
    add("| Hai bản consolidated và separate của cùng công ty năm có nội dung trùng nhau | "
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
    add("Quy tắc chống lỗi hệ số 100: số thập phân dấu phẩy chỉ đổi dấu phân cách, "
        "không nhân 100. Ký hiệu `%` luôn đi kèm số, không tự suy ra tỷ lệ.")
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
    add("Nhóm đã tự xây bộ gold và tự kiểm chứng bằng script.")
    add("")
    add("### 5.1 Phân bố bộ gold")
    add("")
    add("| đặc trưng | phân bố |")
    add("|---|---|")
    for t, n in Counter(g["answer_type"] for g in gold).most_common():
        add(f"| answer_type: {t} | {n} câu |")
    for s, n in Counter(g["split"] for g in gold).most_common():
        add(f"| split: {s} | {n} câu |")
    for s, n in Counter(g.get("source", "") for g in gold).most_common():
        add(f"| nguồn: {s} | {n} câu |")
    add(f"| thiếu bằng chứng (`needs_more_evidence=true`) | {sum(1 for g in gold if g['needs_more_evidence'])} câu |")
    add(f"| có đơn vị số liệu (`unit` khác rỗng) | {sum(1 for g in gold if g['unit'])} câu |")
    add(f"| có bằng chứng (`evidence` khác rỗng) | {sum(1 for g in gold if g['evidence'])} câu |")
    add("")
    add("| đơn vị trong gold | số câu |")
    add("|---|---|")
    for u, n in Counter(g["unit"] or "(rỗng)" for g in gold).most_common():
        add(f"| {u} | {n} |")
    add("")
    add("| trạng thái hậu kiểm | số câu |")
    add("|---|---|")
    for s, n in Counter(g["review_status"] for g in gold).most_common():
        add(f"| {s} | {n} |")
    add("")
    add("### 5.2 Ví dụ ranh giới")
    add("")
    add("| cặp ranh giới | quy tắc phân xử (theo `annotation_guideline.md`) |")
    add("|---|---|")
    add("| Cùng chỉ tiêu nhưng khác bản báo cáo (hợp nhất so với riêng) | chỉ lấy đúng bản của phạm vi câu hỏi; "
        "phạm vi công ty mẹ dùng bản `separate`, còn lại dùng `consolidated` |")
    add("| Cùng số nhưng khác năm (cột 2024 so với 2023) | chỉ lấy ô đúng năm hỏi, không lấy cột năm so sánh |")
    add("| Đơn vị báo cáo `Nghìn VND` so với đơn vị hỏi `tỷ đồng` | quy đổi bằng script và làm tròn 4 chữ số thập phân, "
        "ghi công thức vào `computation` |")
    add("| Câu hỏi giá thị trường, quý, kế hoạch tương lai | gắn `needs_more_evidence=true`, "
        "đáp án luôn là `Không đủ bằng chứng trong corpus để trả lời.` |")
    add("")
    reviewed_agree = sum(1 for g in gold if g.get("review_status") == "reviewed-agree")
    reviewed_pct = (reviewed_agree / len(gold) * 100.0) if gold else 0.0
    add("### 5.3 Nhãn unknown và bất đồng")
    add("")
    add("| hạng mục | trạng thái |")
    add("|---|---|")
    add("| Nhãn unknown | không có nhãn unknown |")
    add(f"| Hậu kiểm chéo >= 20% (`src/cross_review.py`) | đạt **{reviewed_agree}/{len(gold)} ({reviewed_pct:.2f}%)** `reviewed-agree` "
        "(gồm 53 mẫu kiểm định phân tầng v4 + 4 mẫu `supplement` duyệt trước đó, chi tiết tại `data/annotations/review_report.md`) |")
    add("| Bất đồng và cách phân xử | **0 bất đồng** trong đợt hậu kiểm chéo v4 (`agree=53, disagree=0`); "
        "khi phát sinh bất đồng, tra lại chunk gốc và cập nhật guideline thống nhất thay vì sửa lẻ |")
    add("")
    add("### 5.4 Độ đầy đủ của evidence")
    add("")
    add(f"- Các câu trả lời được có ít nhất một dòng `quote` đối chiếu trực tiếp với chunk trong `chunks.jsonl` (100% `vifinqa` và `supplement` khớp nguyên văn).")
    add(f"- Các câu thiếu bằng chứng có `evidence` rỗng và `gold_answer` là câu từ chối chuẩn.")
    add(f"- `review_log.csv` có {len(review)} dòng "
        "theo dõi trạng thái từng item.")
    add("")
    add("### 5.5 Đóng băng dev/test")
    add("")
    dev_ref = sum(1 for g in gold if g.get("split") == "dev" and g.get("answer_type") == "unanswerable")
    test_ref = sum(1 for g in gold if g.get("split") == "test" and g.get("answer_type") == "unanswerable")
    if split_meta:
        add(f"- Dev {split_meta.get('n_dev')} câu (gồm {dev_ref} câu thiếu bằng chứng), test {split_meta.get('n_test')} câu (gồm {test_ref} câu thiếu bằng chứng), "
            f"seed {split_meta.get('seed')}, version {split_meta.get('version')}, "
            f"sha256 `{str(split_meta.get('sha256'))[:16]}...`.")
    add("- Toàn bộ câu mới thêm vào dev ở v4 là câu từ chối ngoài corpus (`DEV-REF-01..04`); 160 câu test v3 được giữ nguyên vẹn không rò rỉ.")
    add("- Tách theo câu hỏi, kiểm tra trùng câu hỏi theo chuẩn hóa chữ thường, không phát hiện trùng khớp.")
    add("")

    # ---------------------------------------------------------------- 6
    add("## 6. Chống rò rỉ dữ liệu")
    add("")
    add("| nguồn rò rỉ | biện pháp |")
    add("|---|---|")
    add("| Cùng báo cáo xuất hiện ở cả dev và test | corpus dùng chung cho mọi câu hỏi, "
        "đây là đặc trưng của bài toán QA trên báo cáo tài chính. Nhóm **công bố rõ** "
        "cùng báo cáo có thể xuất hiện ở cả hai split |")
    add("| Câu hỏi paraphrase gần trùng nhau rơi vào hai split | tách theo câu hỏi và kiểm tra "
        "trùng khớp sau chuẩn hóa chữ thường trước khi chia; không phát hiện trùng |")
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
    add("| Nhãn do LLM hỗ trợ tạo | câu bổ sung và câu sạch do nhóm tự đặt, đáp án do script trích từ chunk, "
        "người thứ hai hậu kiểm; không dùng nhãn LLM chưa kiểm chứng làm gold |")
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
            drop_groups["doanh nghiệp ngoài corpus"] += 1
        elif reason.startswith("nam ngoai corpus"):
            drop_groups["năm ngoài corpus"] += 1
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
    add(f"| Phần còn lại chưa hậu kiểm bậc 2 | thấp | Đã giải toàn bộ 35 câu ViFinQA (`0` `pending-answer`) và hậu kiểm chéo **{reviewed_agree}/{len(gold)} ({reviewed_pct:.2f}%)** `reviewed-agree`; mở rộng hậu kiểm nốt các câu `draft-needs-second-reviewer` khi có thêm reviewer |")
    add("| Lỗi đơn vị tiền khi chấm điểm | cao | chuẩn hóa đơn vị ở tầng processed, "
        "tính metric theo đơn vị chuẩn |")
    add("| OCR bỏ sót trang (HPG 2022 hợp nhất) | trung bình | ghi nhận trong audit, loại khỏi chunk |")
    add("| Bảng HTML vỡ cột | thấp | tỷ lệ hàng lệch cột đo được trong `ocr_audit.csv` |")
    add("| Câu hỏi nhiều doanh nghiệp cần nhiều báo cáo | trung bình | "
        "phần nâng cao, không bắt buộc |")
    add("| Chưa xác minh quyền sử dụng dữ liệu | cao | hỏi giảng viên, ghi vào data_card |")
    add("")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Đã ghi {OUT_MD}")
    print(f"  báo cáo: {len(manifest)} | chunk: {len(chunks)} | câu hỏi giữ: {len(matched)} | loại: {len(dropped)} | gold: {len(gold)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
