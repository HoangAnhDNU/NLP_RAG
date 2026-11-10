# Lược đồ dữ liệu (data_schema.md)

Tài liệu này mô tả tên trường, kiểu dữ liệu, tập giá trị hợp lệ và quy ước nhãn
cho toàn bộ dữ liệu Đề tài 6. Mọi file đọc và ghi bằng `encoding="utf-8"`.

## 1. `data/data_manifest.csv` (bản kê chuẩn, 240 dòng: 40 corpus + 200 gold)

| Trường | Kiểu | Giá trị hợp lệ | Quy ước |
|---|---|---|---|
| `item_id` | string, bắt buộc, duy nhất | `document_id` của báo cáo hoặc `question_id` của câu gold | ID ổn định, không đổi sau khi đóng băng |
| `document_id` | string, bắt buộc | `<TICKER>_<YEAR>_<consolidated\|separate>` cho báo cáo; với câu gold chưa gắn báo cáo dùng `<COMPANY>_<YEAR>` | Ví dụ `HPG_2024_consolidated` |
| `source_name` | string | `AIGuruTinix/ViFinQA`, `synthetic-by-team` | Nguồn gốc item |
| `source_url` | string | URL Hugging Face hoặc rỗng với câu tự tạo | Trỏ đúng đường dẫn file nguồn |
| `source_version` | string | revision `0450088...` hoặc `annotation-guideline-v0.1` | Ghi revision thực dùng |
| `retrieved_at` | date `YYYY-MM-DD` | ngày tải | Ngày nhóm tải snapshot |
| `published_at` | string, luôn trống | `""` | Chỉ ghi ngày phát hành thực từ nguồn. Nguồn không công bố nên để trống, không suy ra từ ID hay ngày crawl |
| `language` | string | `vi` | Toàn bộ corpus là tiếng Việt |
| `original_category` | string | `financial_statement_ocr`, `vifinqa_question`, `synthetic_question` | Nhãn gốc của nguồn, không đánh đồng với `task_label` |
| `task_label` | string | `financial_report_chunk`, `qa_gold` | Nhãn nhiệm vụ nhóm dùng cho RAG |
| `license_status` | string | `unknown_verify_with_teacher` | Chưa xác minh quyền tái phân phối, phải hỏi giảng viên |
| `split` | string | `corpus`, `dev`, `test` | `corpus` cho 40 báo cáo; `dev` 40 câu; `test` 160 câu |
| `notes` | string | tự do | Với báo cáo ghi `company/year/version/pages/sha256/local`; với câu gold ghi `answer_type/unit/needs_more_evidence/review` |

Quy tắc: `original_category` và `task_label` ghi riêng hai cột, không gộp.

## 2. `data/processed/corpus_manifest.csv` (40 báo cáo)

Bản kê kỹ thuật của corpus: `document_id, company_id, fiscal_year, report_version,`
`source_name, source_url, source_version, retrieved_at, published_at, language,`
`original_category, task_label, license_status, split, local_path, n_pages, n_chars, sha256, notes`.

- `company_id` thuộc `HPG, HSG, NKG, MSR`.
- `fiscal_year` thuộc `2020-2024` (số nguyên).
- `report_version` thuộc `consolidated, separate`.
- `n_pages >= 10`, `sha256` là SHA-256 của file OCR gốc.

## 3. `data/processed/chunks.jsonl` (2407 dòng)

Mỗi dòng là một trang báo cáo đã chuẩn hóa.

| Trường | Kiểu | Ghi chú |
|---|---|---|
| `chunk_id` | string | `<document_id>#p<NNN>`, ví dụ `HPG_2020_consolidated#p011` |
| `document_id` | string | khóa nối với manifest |
| `company_id` | string | `HPG, HSG, NKG, MSR` |
| `fiscal_year` | int | 2020-2024 |
| `report_version` | string | `consolidated` hoặc `separate` |
| `page` | int | số trang trong file OCR gốc |
| `n_tables` | int | số bảng HTML parse được trên trang |
| `unit` | string | đơn vị phát hiện (`đồng`, `Nghìn VND`, hoặc rỗng) |
| `text` | string | văn bản NFC, giữ dấu tiếng Việt |
| `text_chars` | int | độ dài `text` |
| `local_path` | string | đường dẫn file OCR gốc |

## 3b. `data/processed/table_records.jsonl` (29834 dòng)

Mỗi dòng là một ô số trong bảng HTML đã chuẩn hóa, song song với chunk văn bản.

| Trường | Kiểu | Ghi chú |
|---|---|---|
| `company` | string | `HPG, HSG, NKG, MSR` |
| `year` | int | năm của cột kỳ báo cáo, suy từ `period_label`, dự phòng bằng `fiscal_year` |
| `period_label` | string | nhãn cột gốc (`30.9.2024 VND`, `2024Nghìn VND`, `31/12/2024 VND`) |
| `statement` | string | `balance_sheet`, `income_statement`, `cash_flow`, `other` |
| `metric` | string | tên chỉ tiêu, giữ dấu tiếng Việt |
| `metric_code` | string | mã số dòng (`10`, `20`, `60`, `110`), rỗng nếu bảng không có mã |
| `value` | number | giá trị sau chuẩn hóa (`1.234,56` → `1234.56`, `(983)` → `-983`) |
| `unit` | string | đơn vị phát hiện (`đồng`, `nghìn đồng`, `triệu đồng`, `tỷ đồng`, `nghìn tỷ đồng`, `%`) |
| `value_raw` | string | chuỗi số gốc trong ô bảng |
| `page` | int | trang chứa bảng |
| `table_index` | int | thứ tự bảng trên trang, bắt đầu từ 1 |
| `source_chunk_id` | string | khóa nối về `chunks.jsonl` |
| `document_id` | string | khóa nối với manifest |
| `report_version` | string | `consolidated` hoặc `separate` |
| `fiscal_year` | int | năm báo cáo |
| `confidence` | number | `0.93` nếu có mã số, `0.85` nếu tên dài, trừ `0.1` khi thiếu đơn vị |

Tái lập: `python src/build_table_records.py`. E8 lookup trên file này trước rồi mới hybrid RAG.

## 4. Câu hỏi ViFinQA đã lọc

`questions_matched.csv` (35 dòng): `question_id, question, company_id, company_name,`
`n_companies, years_in_question, years_in_corpus, unit, answer_type, scope,`
`has_calculation, is_multi_company, evidence_required, source_question_id`.

- `unit` thuộc `"", %, tỷ đồng, triệu đồng, nghìn tỷ đồng, trăm tỷ đồng, nghìn đồng, lần, điểm phần trăm`.
- `answer_type` thuộc `numeric, computation`.
- `scope` thuộc `unspecified, parent`.

`questions_dropped.csv` (977 dòng): `id, question, reason, codes, years`.
`reason` thuộc `out_of_corpus_company, out_of_corpus_year, unknown_company, missing_year`.

## 5. Kiểm toán OCR

`ocr_audit.csv`: một dòng một báo cáo, gồm `document_id, company_id, fiscal_year,`
`report_version, local_path, n_pages, n_tables, pages_empty, pages_without_table,`
`pages_with_unit_header, avg_page_chars, min_page_chars, max_page_chars,`
`avg_viet_ratio, avg_suspect_ratio, avg_no_diacritic_ratio, avg_empty_cell_ratio,`
`avg_ragged_row_ratio, avg_number_cell_ratio, total_numbers, total_thousand_sep,`
`total_decimal, total_paren_neg, total_percent, total_decoration, total_latex, unit_coverage`.

`ocr_audit_pages.csv`: một dòng một trang, gồm `document_id, page, n_chars, n_tables,`
`n_table_rows, avg_table_cols, max_table_cols, empty_cell_ratio, ragged_row_ratio,`
`number_cell_ratio, header_with_unit, viet_ratio, suspect_ratio, no_diacritic_ratio,`
`n_numbers, n_thousand_sep, n_decimal, n_paren_neg, n_percent, n_decoration, n_latex,`
`units, is_empty`.

## 6. Gold và gắn nhãn (`data/annotations/`)

`qa_gold.jsonl` (200 dòng). Mỗi bản ghi:

| Trường | Kiểu | Quy ước |
|---|---|---|
| `question_id` | string | `ViFinQA-<n>`, `S_NEW_<nn>` hoặc `CLEAN-T<tầng>-<mã>-<năm>-<số>` |
| `question` | string | nguyên văn câu hỏi, giữ dấu |
| `gold_answer` | string | đáp án hiển thị kèm đơn vị; câu thiếu bằng chứng luôn là `Không đủ bằng chứng trong corpus để trả lời.`; 35 câu ViFinQA để trống chờ gắn nhãn |
| `answer_type` | string | `numeric, computation, unanswerable` |
| `value` | number hoặc `""` | giá trị số sau quy đổi, làm tròn 4 chữ số thập phân |
| `unit` | string | `nghìn tỷ đồng, tỷ đồng, triệu đồng, đồng, %, lần` hoặc rỗng |
| `company_id` | string | `HPG, HSG, NKG, MSR` hoặc tổ hợp `HPG\|HSG...` |
| `fiscal_year` | int hoặc string | năm của câu hỏi |
| `report_id` | string | `document_id` dùng làm bằng chứng, trống nếu chưa gắn |
| `evidence` | list | mỗi phần tử `chunk_id, source_page, quote` (quote nguyên văn trong chunk) |
| `computation` | string | công thức và số đầu vào nếu có phép tính |
| `source_page` | int hoặc `""` | trang chứa đáp án |
| `needs_more_evidence` | bool | `true` với 16 câu thiếu bằng chứng |
| `reviewer_id` | string | mã người gắn nhãn |
| `review_status` | string | `pending-answer, draft-needs-second-reviewer` |
| `source` | string | `vifinqa, supplement, table-clean` |
| `split` | string | `dev, test` |

`gold_labels.csv`: bản gọn `question_id, question, company_id, fiscal_year, unit, answer_type, source`.

`review_log.csv`: `item_id, gold, reviewer, status, guideline_version, disagreement_note`.
`status` thuộc `pending-answer, needs-second-reviewer`.

## 7. Splits (`data/splits/`)

- `dev.json`: danh sách 40 ID dev.
- `test.json`: danh sách 160 ID test.
- `split_meta.json`: `version` (`v2`), `seed` (42), `n_dev`, `n_test`, `dev_ids`, `test_ids`, `rule`, `sha256` (hash của meta để đóng băng).
- Quy tắc: toàn bộ 16 câu thiếu bằng chứng nằm ở test; dev chỉ gồm câu trả lời được; chống rò rỉ bằng kiểm tra trùng câu hỏi theo chuẩn hóa chữ thường.
