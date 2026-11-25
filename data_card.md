# Hồ sơ dữ liệu (Data Card): Corpus RAG và Bộ chuẩn Gold QA ViFinQA-Steel-4Co (v4)

## 1. Tóm tắt tập dữ liệu và Mục đích sử dụng

`ViFinQA-Steel-4Co (v4)` là bộ dữ liệu chuẩn cho bài toán hỏi đáp báo cáo tài chính tiếng Việt và sinh câu trả lời tăng cường truy hồi (RAG), được xây dựng cho đề tài CSC4007 (Hỏi đáp Báo cáo tài chính tiếng Việt có trích dẫn và từ chối dựa trên bằng chứng).

Với một câu hỏi tài chính tiếng Việt và một kho báo cáo tài chính kiểm toán năm cố định, mô hình cần truy hồi các đoạn nguồn ở cấp trang (`company_id`, `fiscal_year`, `report_version`, `page`, `chunk_id`), tính toán hoặc trích xuất đáp án số đã chuẩn hóa kèm quy đổi đơn vị, đính kèm trích dẫn bằng chứng có thể kiểm chứng, hoặc trả về đúng nguyên văn câu từ chối `"Không đủ bằng chứng trong corpus để trả lời."` khi corpus không có dữ liệu.

Toàn bộ các `chunk`, bản ghi bảng (`table_records`) và mẫu chuẩn (`qa_gold`) đều bảo toàn tiếng Việt (`vi`) theo chuẩn Unicode NFC trên 4 doanh nghiệp niêm yết giai đoạn `2020-2024`, bao gồm cả hai phiên bản báo cáo `consolidated` (hợp nhất) và `separate` (riêng công ty mẹ):

| Mã CK | Tên doanh nghiệp | Kết thúc năm tài chính | Đơn vị báo cáo gốc | Phiên bản |
|---|---|---|---|---|
| `HPG` | CTCP Tập đoàn Hòa Phát | `31/12` | `VND` | `consolidated`, `separate` |
| `HSG` | CTCP Tập đoàn Hoa Sen | `30/09` | `VND` | `consolidated`, `separate` |
| `NKG` | CTCP Thép Nam Kim | `31/12` | `VND` | `consolidated`, `separate` |
| `MSR` | CTCP Masan High-Tech Materials | `31/12` | `Nghìn VND` (nhân 1.000 để ra VND) | `consolidated`, `separate` |

Mục đích sử dụng của bộ dữ liệu là đánh giá chuẩn học thuật, chạy thực nghiệm RAG ngoại tuyến có khả năng tái lập (`E0-E8`), kiểm định truy hồi, trích dẫn, từ chối và minh họa ứng dụng tương tác (`app/streamlit_app.py`) trong phạm vi 4 doanh nghiệp giai đoạn `2020-2024`. Phiên bản dữ liệu và phân chia tập là `v4` (`data/splits/split_meta.json` và `evaluation/split_freeze.json`).

## 2. Nguồn dữ liệu và Phiên bản

Nguồn gốc chính được lấy từ Hugging Face [`AIGuruTinix/ViFinQA`](https://huggingface.co/datasets/AIGuruTinix/ViFinQA/blob/0450088ab22ec946f04f097586967ca405955b3b/), cố định tại revision `0450088ab22ec946f04f097586967ca405955b3b` và tải cục bộ bằng `src/download_vifinqa.py` vào `data/raw/vifinqa/`. Kho `ViFinQA` gốc trích xuất 1.973 báo cáo OCR từ [`tinixai/ocr_annual_financials`](https://huggingface.co/datasets/tinixai/ocr_annual_financials) (`TiniX Vietnam OCR Annual Financial Statements`), lưu dưới dạng tệp văn bản UTF-8 có dấu phân cách trang `===== PAGE n =====` và các thẻ bảng HTML `<table>`.

Quá trình chọn corpus và tạo manifest ban đầu diễn ra vào ngày `2026-11-10`, sau đó manifest của corpus được cập nhật lại khi dựng pipeline bản `v4` vào ngày `2026-11-15` (`retrieved_at` trong `data/processed/corpus_manifest.csv` là `2026-11-15`; các dòng câu hỏi gold trong `data/data_manifest.csv` ghi ngày `2026-11-10`; trường `published_at` để trống `""` do nguồn gốc không công bố ngày phát hành từng báo cáo).

Bộ `204` câu Gold QA đến từ bốn nguồn:

- `vifinqa` (`35` câu): tập câu hỏi lọc từ `data/raw/vifinqa/questions/questions.jsonl` (`1.012` dòng chỉ có câu hỏi -> giữ `35` câu khớp phạm vi 4 công ty `2020-2024`; loại `977` câu). Do `ViFinQA` công khai chỉ có `id` và `question`, chưa có đáp án, bằng chứng hay phân chia tập, toàn bộ 35 đáp án, giá trị chuẩn hóa, phép tính từng bước và trích dẫn nguyên văn từ chunk đều được biên soạn và đối chiếu trực tiếp trên corpus 40 báo cáo (`src/resolve_vifinqa_and_dev_refusal.py`).
- `table-clean` (`150` câu): bộ câu hỏi sinh theo mẫu chuẩn từ các bản ghi bảng `consolidated` sạch thuộc báo cáo kết quả kinh doanh và bảng cân đối kế toán, gồm tra cứu một kỳ (`T1`, 55 câu), so sánh biến động hai năm (`T2`, 44 câu), tính chênh lệch hai năm (`T3`, 43 câu) và từ chối ngoài corpus (`T5`, 8 câu) (`src/build_expanded_gold_v2.py`, `src/build_expanded_gold_v3.py`).
- `supplement` (`15` câu): các câu hỏi chuyên ngành tự biên soạn có trích dẫn trang (`S_NEW_01..07`) và các câu kiểm tra từ chối ngoài corpus (`S_NEW_08..15`) (`src/build_supplement_gold.py`).
- `dev-refusal` (`4` câu): bốn câu kiểm tra từ chối ngoài corpus (`DEV-REF-01..04`) bổ sung riêng vào tập `dev` ở bản `v4` (`src/resolve_vifinqa_and_dev_refusal.py`) để mẫu số đánh giá từ chối trên `dev` khác 0 (`refusal_den = 4`) mà không làm thay đổi tập `test` đã đóng băng.

Bản chụp lịch sử `v1` (`50` câu) vẫn được lưu tại `data/annotations/qa_gold_v1_50.jsonl` để đối chiếu.

## 3. Giấy phép và Quyền truy cập

Toàn bộ `40` dòng trong `data/processed/corpus_manifest.csv` và `244` dòng trong `data/data_manifest.csv` đều ghi nhận trường `license_status` là `unknown_verify_with_teacher`. Tài liệu `data/raw/vifinqa/README.md` từ nguồn nêu rõ các báo cáo OCR của `tinixai/ocr_annual_financials` mang giấy phép Creative Commons Attribution-NonCommercial 4.0 International (`CC BY-NC 4.0`), trong khi phần câu hỏi `ViFinQA` không đính kèm tệp giấy phép riêng. Cần xác minh quyền tái phân phối với giảng viên học phần trước khi công bố rộng rãi.

Các tệp nguồn thô trong `data/raw/` được loại trừ khỏi Git qua `.gitignore` và không phân phối lại trong kho mã nguồn. Các dữ liệu đã qua xử lý (`chunks.jsonl`, `table_records.jsonl`), manifest, bộ nhãn, kết quả đánh giá và script tái lập được lưu phiên bản phục vụ kiểm chứng học thuật.

## 4. Cấu trúc dữ liệu

Mọi tệp dữ liệu có cấu trúc đều sử dụng bảng mã UTF-8 (`encoding="utf-8"`). Định nghĩa đầy đủ từng cột được trình bày trong `data/data_schema.md`.

### Các tệp dữ liệu cốt lõi

| Thành phần | Đường dẫn | Số bản ghi | Các trường chính |
|---|---|---:|---|
| Bản kê tổng hợp | `data/data_manifest.csv` | 244 | `item_id`, `document_id`, `source_name`, `source_url`, `source_version`, `retrieved_at`, `published_at`, `language`, `original_category`, `task_label`, `license_status`, `split`, `notes` |
| Bản kê corpus | `data/processed/corpus_manifest.csv` | 40 | `document_id`, `company_id`, `fiscal_year`, `report_version`, `n_pages`, `n_chars`, `sha256`, `local_path`, `license_status` |
| Chunk cấp trang | `data/processed/chunks.jsonl` | 2.407 | `chunk_id`, `document_id`, `company_id`, `fiscal_year`, `report_version`, `page`, `n_tables`, `unit`, `text`, `text_chars`, `local_path` |
| Bản ghi bảng số | `data/processed/table_records.jsonl` | 29.615 | `company`, `year`, `period_label`, `statement`, `metric`, `metric_code`, `value`, `unit`, `value_raw`, `page`, `table_index`, `source_chunk_id`, `document_id`, `report_version`, `fiscal_year`, `confidence` |
| Bộ Gold QA (`v4`) | `data/annotations/qa_gold.jsonl` | 204 | `question_id`, `question`, `gold_answer`, `answer_type`, `value`, `unit`, `company_id`, `fiscal_year`, `report_id`, `evidence`, `computation`, `source_page`, `needs_more_evidence`, `reviewer_id`, `review_status`, `source`, `split`, `unanswerable_reason` |
| Nhật ký hậu kiểm | `data/annotations/review_log.csv` | 204 | `item_id`, `gold`, `reviewer`, `status`, `guideline_version`, `disagreement_note` |

### Ví dụ cấu trúc dữ liệu (đã rút gọn)

Ví dụ một bản ghi chunk (`data/processed/chunks.jsonl`, trường `text` dài được rút gọn):

```json
{
  "chunk_id": "HPG_2020_consolidated#p001",
  "document_id": "HPG_2020_consolidated",
  "company_id": "HPG",
  "fiscal_year": 2020,
  "report_version": "consolidated",
  "page": 1,
  "n_tables": 0,
  "unit": "",
  "text": "KPMG\n\nCông ty Cổ phần Tập đoàn Hòa Phát\n\nBáo cáo tài chính hợp nhất cho năm kết thúc ngày 31 tháng 12 năm 2020...",
  "text_chars": 110,
  "local_path": "data/raw/vifinqa/financial_statements/HPG/2020/HPG_financial_statements_2020_consolidated/HPG_financial_statements_2020_consolidated_extracted.txt"
}
```

Ví dụ một bản ghi bảng (`data/processed/table_records.jsonl`):

```json
{
  "company": "HPG",
  "year": 2020,
  "period_label": "31/12/2020 VND",
  "statement": "balance_sheet",
  "metric": "Tài sản ngắn hạn(\\( 100 = 110 + 120 + 130 + 140 + 150 \\))",
  "metric_code": "100",
  "value": 56747258197010.0,
  "unit": "đồng",
  "value_raw": "56.747.258.197.010",
  "page": 7,
  "table_index": 1,
  "source_chunk_id": "HPG_2020_consolidated#p007",
  "document_id": "HPG_2020_consolidated",
  "report_version": "consolidated",
  "fiscal_year": 2020,
  "confidence": 0.93
}
```

Ví dụ một bản ghi Gold QA (`data/annotations/qa_gold.jsonl`):

```json
{
  "question_id": "S_NEW_01",
  "question": "Doanh thu thuần về bán hàng và cung cấp dịch vụ hợp nhất của CTCP Tập đoàn Hoa Sen trong năm tài chính kết thúc ngày 30/09/2024 là bao nhiêu nghìn tỷ đồng?",
  "gold_answer": "39.2719 nghìn tỷ đồng",
  "answer_type": "numeric",
  "value": 39.2719,
  "unit": "nghìn tỷ đồng",
  "company_id": "HSG",
  "fiscal_year": 2024,
  "report_id": "HSG_2024_consolidated",
  "evidence": [{"chunk_id": "HSG_2024_consolidated#p009", "source_page": 9, "quote": "10 | Doanh thu thuần về bán hàng và cung cấp dịch vụ | 26 | 39.271.893.738.448 | 31.650.660.956.650"}],
  "computation": "39271893738448 VND / 1e12 = 39.2719 nghìn tỷ đồng (làm tròn 4 chữ số thập phân).",
  "source_page": 9,
  "needs_more_evidence": false,
  "reviewer_id": "member-1/member-2",
  "review_status": "reviewed-agree",
  "source": "supplement",
  "split": "test"
}
```

Không có thông tin định danh cá nhân riêng tư (PII) hay khóa API nào xuất hiện trong dữ liệu hoặc manifest; tên các cá nhân xuất hiện trong văn bản OCR gốc đều là lãnh đạo doanh nghiệp và kiểm toán viên ký báo cáo tài chính công khai theo quy định pháp luật.

## 5. Thành phần và Phân bố dữ liệu

### Tổng hợp Corpus

| Chỉ tiêu | Số lượng đã kiểm chứng | Đường dẫn / Ghi chú |
|---|---:|---|
| Báo cáo kiểm toán | 40 | 4 công ty x 5 năm (2020-2024) x 2 bản (`consolidated`, `separate`) |
| Trang OCR thô | 2.437 | Tổng `5.422.578` ký tự trên 40 tệp `.txt` (`report/ocr_audit.md`) |
| Trang OCR rỗng bị loại | 30 | `1,23%` tổng số trang thô (`data/processed/ocr_audit_pages.csv`) |
| Chunk dùng truy hồi | 2.407 | `data/processed/chunks.jsonl` (1 chunk = 1 trang khác rỗng; `1.634` chunk có bảng) |
| Bảng HTML OCR đã phân tích | 2.585 | Trích xuất từ các chunk khác rỗng |
| Bản ghi bảng có cấu trúc | 29.615 | `data/processed/table_records.jsonl` |
| Dòng bản kê tổng hợp | 244 | `40` corpus + `44` dev + `160` test trong `data/data_manifest.csv` |

Phân bố `29.615` bản ghi bảng theo loại báo cáo `statement` gồm `other` (19.904), `balance_sheet` (5.391), `cash_flow` (2.263) và `income_statement` (2.057). Theo đơn vị `unit` phân tích được gồm `đồng` (22.634), `nghìn đồng` (4.912), `%` (1.530), rỗng `""` (292), `triệu đồng` (234) và `tỷ đồng` (13).

Ở cấp chunk trang (`n = 2.407`), trường `unit` có giá trị `""` trên `1.680` chunk (các trang không có dòng tiêu đề đơn vị bảng), `đồng` trên `478` chunk, `triệu đồng` trên `142` chunk và `tỷ đồng` trên `107` chunk. Khi tra cứu phía sau, hệ thống phân giải đơn vị từ tiêu đề cột bảng hoặc văn bản trên trang chứ không đoán mò khi thiếu tiêu đề.

### Phân bố bộ Gold QA (`n = 204`)

- Theo nguồn (`source`): `table-clean` **150** (`T1`: 55, `T2`: 44, `T3`: 43, `T5`: 8), `vifinqa` **35**, `supplement` **15** (7 câu có đáp án, 8 câu từ chối), `dev-refusal` **4** (`DEV-REF-01..04`).
- Theo loại đáp án và tập (`answer_type`, `split`): `computation` **94** (`dev`: 21, `test`: 73), `numeric` **90** (`dev`: 19, `test`: 71), và `unanswerable` **20** (`dev`: 4, `test`: 16).
- Theo trạng thái bằng chứng: `needs_more_evidence=false` **184** (trường `evidence` khác rỗng), `needs_more_evidence=true` **20** (`evidence` rỗng và mang câu từ chối chuẩn).
- Theo trạng thái hậu kiểm (`review_status`): `reviewed-agree` **57** (`27,94%`), `draft-needs-second-reviewer` **147** (`72,06%`), `pending-answer` **0**.
- Theo `company_id`: đơn công ty gồm `HSG` (**57**), `NKG` (**52**), `MSR` (**36**), `HPG` (**34**); đa công ty gồm `HPG|HSG|MSR|NKG` (**22**), `HPG|HSG|NKG` (**2**), `HPG|MSR|HSG` (**1**).
- Theo đơn vị chuẩn hóa (`unit`): `tỷ đồng` (89), `nghìn tỷ đồng` (46), `""` cho câu đếm/từ chối (21), `triệu đồng` (12), `%` (11), `đồng` (10), `điểm phần trăm` (9), `lần` (4), `nghìn đồng` (1), `trăm tỷ đồng` (1).

### Tóm tắt dữ liệu khuyết thiếu

Trong `data/data_manifest.csv` và `data/processed/corpus_manifest.csv`, cột `published_at` là `""` ở mọi dòng do nguồn `ViFinQA` gốc không cung cấp ngày phát hành báo cáo gốc. Trong `qa_gold.jsonl`, các trường `report_id` và `source_page` mang giá trị `""` ở `20` câu từ chối và các câu tổng hợp đa công ty/đa kỳ không nằm gọn trong một báo cáo hoặc một trang duy nhất (toàn bộ bằng chứng thành phần của câu trả lời được vẫn ghi đầy đủ trong `evidence[]`). Riêng báo cáo `HPG_2022_consolidated` bị khuyết `24` trang thuyết minh cuối (`42`, `44-54`, `57-68`) do trang trống trong bản chụp OCR gốc.

## 6. Thu thập và Lấy mẫu

Các mã chứng khoán ứng viên trong `ViFinQA` được xếp hạng qua `src/select_corpus.py` theo mật độ câu hỏi khớp, sự đồng nhất mẫu báo cáo kế toán (các doanh nghiệp phi tài chính theo Thông tư `202/2014/TT-BTC`) và khả năng phân tích bảng HTML OCR. Việc chọn 4 doanh nghiệp `HPG`, `HSG`, `NKG`, `MSR` giai đoạn `2020-2024` (loại trừ khối ngân hàng như `VCB`, `ACB` do hệ thống chỉ tiêu khác biệt hoàn toàn) thu được **20** cặp công ty theo năm và **40** tệp báo cáo OCR (`consolidated` và `separate`). Cả hai phiên bản đều được giữ lại vì trong nhóm câu `ViFinQA` khớp có 4 câu hỏi trực tiếp số liệu công ty mẹ (`separate`), trong khi các câu khác hỏi số hợp nhất.

Qua `src/filter_questions.py` và `src/preprocess/company_match.py`, toàn bộ `1.012` câu hỏi thô trong `data/raw/vifinqa/questions/questions.jsonl` được đối chiếu bằng mã chứng khoán trong ngoặc, mã đứng độc lập và chuỗi tên tiếng Việt liên tiếp. Kết quả giữ lại đúng **35** câu thuộc phạm vi `{HPG, HSG, NKG, MSR} x {2020..2024}` (`data/processed/questions_matched.csv`: `10` câu đơn công ty, `25` câu đa công ty; `29` câu `numeric`, `6` câu `computation`). **977** câu còn lại được ghi lý do loại bỏ vào `data/processed/questions_dropped.csv` (`951` câu doanh nghiệp ngoài corpus, `21` câu năm ngoài corpus, `4` câu không xác định được công ty, `1` câu thiếu năm).

Quá trình mở rộng bộ chuẩn có kiểm soát trải qua bốn phiên bản:
- `v1` (`50` câu): `35` câu `vifinqa` + `15` câu `supplement` (`S_NEW_01..15`, biên soạn qua `src/build_supplement_gold.py`).
- `v2` (`127` câu): bổ sung `77` câu sạch trên bảng `consolidated` (`T1`, `T2`, `T3`, `T5`) qua `src/build_expanded_gold_v2.py` (lọc `confidence >= 0.9`, có `metric_code` hợp lệ, năm `2020-2024`, khử trùng theo bộ `(company, norm_name, year, source_chunk_id)`).
- `v3` (`200` câu): bổ sung thêm `73` câu `table-clean` (`T1 +26`, `T2 +22`, `T3 +21`, `T5 +4`) qua `src/build_expanded_gold_v3.py`.
- `v4` (`204` câu): hoàn thiện lời giải và trích dẫn cho toàn bộ `35` câu `vifinqa` đối chiếu trên corpus 40 báo cáo, đồng thời bổ sung `4` câu `dev-refusal` (`DEV-REF-01..04`) riêng vào `dev` qua `src/resolve_vifinqa_and_dev_refusal.py`.

## 7. Tiền xử lý

Mọi script tiền xử lý chỉ đọc từ `data/raw/` mà không sửa tệp gốc, và ghi kết quả tái lập chuẩn UTF-8 vào `data/processed/`.

Thứ nhất, `src/preprocess/vifinqa_parser.py` và `src/build_chunks.py` tách từng báo cáo theo mốc `===== PAGE n =====`, phân tích thẻ HTML `<table>`, chuẩn hóa văn bản về Unicode `NFC` giữ nguyên toàn bộ dấu tiếng Việt, lọc bỏ `1.317` ký tự trang trí (`○ ● ◎ ...`) trên `116` trang, `486` biểu thức LaTeX trên `295` trang cùng ký tự điều khiển (`CONTROL_RE`), và loại **30** trang rỗng (`1,23%` trên `2.437` trang). Mỗi trang còn lại tạo thành một chunk truy hồi (`2.407` chunk trong `chunks.jsonl`) định danh bằng `<document_id>#p<NNN>`.

Thứ hai, `corpus_manifest.csv` lưu mã băm `sha256` từng tệp nguồn, xác nhận 40 báo cáo riêng biệt (hai bản `consolidated` và `separate` khác nhau cả về nội dung lẫn mã băm) với `0` mã `document_id` hoặc `chunk_id` bị trùng. Các script mở rộng bộ câu hỏi chuẩn hóa câu chữ bằng viết thường và thu gọn khoảng trắng (`norm_question`) để loại trừ câu hỏi trùng hoặc lặp lại nguyên ý.

Thứ ba, `normalize_number()`, `src/build_table_records.py` và `src/preprocess/table_extract.py` giữ nguyên chuỗi số gốc trong `value_raw` và văn bản chunk để bảo toàn trích dẫn, đồng thời chuẩn hóa dấu chấm phân cách hàng nghìn của tiếng Việt (`91.279.041.771.826` -> `91279041771826`), đổi dấu phẩy thập phân thành dấu chấm (`3,2` -> `3.2`, tuyệt đối không nhân 100) và đổi số âm trong ngoặc đơn thành số âm (`(983.237)` -> `-983237`). Đơn vị được suy ra từ tiêu đề cột (`Nghìn VND`, `Triệu VND`, `Tỷ VND`, `VND`, `%`) hoặc văn bản trên trang, tạo thành `29.615` bản ghi bảng có cấu trúc với `confidence` bằng `0.93` (khi có `metric_code`) hoặc `0.85` (trừ `0.1` nếu thiếu đơn vị).

## 8. Quy trình gắn nhãn

Công tác gắn nhãn tuân thủ tài liệu `data/annotations/annotation_guideline.md` (`v0.2`), được thực hiện bởi các thành viên gắn nhãn (`member-1`, `member-2`, `annotator-1`, `reviewer-2`) kết hợp các script dựng tự động có kiểm chứng (`auto-builder`). Phân bố theo `reviewer_id` trên `204` câu: `auto-builder` (120), `auto-builder/reviewer-2` (30), `annotator-1` (23), `annotator-1/reviewer-2` (16), `member-1/reviewer-2` (6), `member-1/member-2` (5) và `member-1` (4).

Bốn quy tắc chi phối toàn bộ bộ nhãn chuẩn `v0.2`:

1. Câu hỏi nêu `"công ty mẹ"` hoặc `"riêng"` sử dụng bản `separate`; câu hỏi cấp tập đoàn hoặc không ghi rõ sử dụng bản `consolidated`.
2. Đáp án số lấy từ đúng cột năm tài chính mục tiêu (`2020-2024`, hoặc cột so sánh `"Số đầu năm"`/`"1/1/2020"` trên báo cáo `2020` khi câu hỏi hỏi gốc năm `2019`), không lấy nhầm từ cột lân cận hay trang thuyết minh trừ khi câu hỏi hỏi chi tiết thuyết minh (`ViFinQA-97`, `ViFinQA-186`, `ViFinQA-311`, `ViFinQA-612`).
3. Hệ số đơn vị báo cáo (`VND` so với `Nghìn VND`) được quy đổi về đúng đơn vị mà câu hỏi yêu cầu (`đồng`, `nghìn đồng`, `triệu đồng`, `tỷ đồng`, `trăm tỷ đồng`, `nghìn tỷ đồng`, `%`, `điểm phần trăm`, `lần`) và làm tròn tối đa `4` chữ số thập phân (`round(x, 4)`).
4. Các câu hỏi có chủ đề hoặc kỳ báo cáo không xuất hiện trên bất kỳ chunk nào trong `2.407` chunk được gắn `needs_more_evidence: true`, `answer_type: "unanswerable"`, `evidence: []`, chuỗi chuẩn `"Không đủ bằng chứng trong corpus để trả lời."` kèm `unanswerable_reason` ghi rõ các cụm từ đã tra cho kết quả `0` hit. Các ca ranh giới kế toán (`ViFinQA-97`, `ViFinQA-186`, `ViFinQA-709`) được ghi chú rõ trong `computation` và phân xử dựa trên báo cáo chính thức hoặc thuyết minh chỉ định theo Mục 7 của guideline.

## 9. Kiểm định chất lượng

Trên toàn bộ `40` báo cáo, `2.437` trang và `2.585` bảng HTML, `src/audit_ocr.py` (`report/ocr_audit.md`) đo được `avg_ragged_row_ratio` bằng `0.0000` ở mọi báo cáo (không có hàng bảng HTML lệch cột) và `0` lần xuất hiện ký tự lỗi mã hóa Unicode (`U+FFFD`). Cả `30` trang OCR rỗng đều được ghi nhận trong `data/processed/ocr_audit_pages.csv` và loại khỏi tập chunk truy hồi.

Kết quả chạy `src/data_quality_report.py` (`report/data_quality_report.md`) xác nhận `0` mã ID bị trùng hoặc rỗng trên `corpus_manifest.csv` (40), `ocr_audit.csv` (40), `questions_matched.csv` (35), `questions_dropped.csv` (977), `data_manifest.csv` (244), `chunks.jsonl` (2.407) và `qa_gold.jsonl` (204); đồng thời `0` nhãn `answer_type` hoặc `review_status` nằm ngoài danh mục hợp lệ và `0` câu ở trạng thái `pending-answer`.

Script `src/cross_review.py` thực thi hai lớp kiểm định:

1. Toàn vẹn trích dẫn trên toàn corpus (`204/204`): mọi chuỗi `evidence[].quote` của nhóm `vifinqa` (`35/35`) và `supplement` có đáp án (`7/7`) đều khớp nguyên văn bên trong `chunks.jsonl[chunk_id]["text"]` với `source_page == chunk["page"]`. Với toàn bộ `142` câu `table-clean` có đáp án, cả hai token `metric` và `raw_value` trong tóm tắt `"metric | raw_value"` đều đồng thời xuất hiện trên cùng một dòng phân tách bằng dấu gạch đứng của chunk được trích.
2. Kiểm toán độc lập phân tầng (`53/204 = 25,98%`, `seed = 42`, `data/annotations/review_report.md`): bao phủ `table-clean` (`30`: T1=10, T2=9, T3=9, T5=2), `vifinqa` (`12`), `supplement` (`7`) và `dev-refusal` (`4`) trên cả `dev` (`14`) và `test` (`39`), gồm `25` câu `numeric`, `19` câu `computation` và `9` câu `unanswerable`. Khi trích xuất lại số thô trực tiếp từ `chunks.jsonl` (không đọc `row['computation']`) và dò toàn văn trên toàn bộ `2.407` chunk cho các câu từ chối, kết quả thu được **0 bất đồng** (`agree: 53`, `disagree: 0`), nâng tổng tích lũy `reviewed-agree` trong `qa_gold.jsonl` và `review_log.csv` lên **57 / 204 (27,94%)** (tính cả 4 mẫu `supplement` do `member-1/member-2` duyệt trước đó ngoài mẫu ngẫu nhiên).

## 10. Phân chia tập dữ liệu và Chống rò rỉ

Phân chia tập được lưu tại `data/splits/dev.json`, `data/splits/test.json` và `data/splits/split_meta.json`, kèm bản sao giống hệt tại `evaluation/split_freeze.json`.

| Thuộc tính | Giá trị |
|---|---|
| `version` | `v4` |
| `seed` | `42` |
| `n_dev` | `44` (`table-clean`: 30, `vifinqa`: 9, `dev-refusal`: 4, `supplement`: 1; gồm `40` câu có đáp án + `4` câu từ chối; `refusal_den = 4`) |
| `n_test` | `160` (`table-clean`: 120, `vifinqa`: 26, `supplement`: 14; gồm `144` câu có đáp án + `16` câu từ chối; `refusal_den = 16`) |
| `sha256` | `0012ebccd6712b44cdd1faf18f020c547c82973db09d37ab2b9e96b0a94a34b4` |

Danh sách đầy đủ mã ID đã sắp xếp nằm trong `data/splits/dev.json` (`44` ID, từ `CLEAN-T1-HPG-2020-08` đến `CLEAN-T3-NKG-2023-2024-B18`, `DEV-REF-01..04`, `S_NEW_03`, `ViFinQA-99`, và `ViFinQA-373`..`ViFinQA-973`) và `data/splits/test.json` (`160` ID, từ `CLEAN-T1-HPG-2020-01` đến `CLEAN-T5-NKG-2024-07`, `S_NEW_01..02`, `S_NEW_04..15`, và `ViFinQA-97`..`ViFinQA-709`).

Bốn lớp bảo vệ chống rò rỉ đánh giá được áp dụng:

1. Toàn bộ `160` ID tập `test` và nhãn đáp án từ `v3` được giữ nguyên vẹn ở `v4`; các dòng `vifinqa` từng ở trạng thái `pending-answer` chỉ được điền đầy đủ đáp án và bằng chứng từ corpus mà không đổi thành phần split, còn `DEV-REF-01..04` chỉ thêm riêng vào `dev`.
2. Cả `204` câu hỏi đều là duy nhất sau khi viết thường và chuẩn hóa khoảng trắng, loại trừ nguy cơ câu `test` trùng hoặc diễn đạt lại lọt vào `dev`.
3. Cả `dev` và `test` cùng truy vấn trên kho 40 báo cáo cố định (`2.407` chunk), đúng thông lệ QA trên corpus tài chính cố định và được công bố minh bạch trong `evaluation/evaluation_protocol.md`. Kết quả không dùng để suy rộng sang các doanh nghiệp hay năm ngoài corpus nếu chưa có thực nghiệm tách riêng công ty mới.
4. Mọi luật nhắc (prompt), trọng số truy hồi và từ điển đồng nghĩa chỉ được tinh chỉnh trên `dev`, còn `test` chỉ dùng để báo cáo kết quả cuối. Script `src/build_gold.py` sẽ dừng với mã thoát `1` nếu `qa_gold.jsonl` đã có hơn `50` dòng khác rỗng mà thiếu cờ `--force-v1`.

## 11. Nhãn chuẩn Gold và Giao thức đánh giá

Mỗi câu gold có đáp án đều lưu `gold_answer`, `value` (quy đổi đúng `unit`, làm tròn 4 chữ số thập phân), `unit`, `evidence[]` (`chunk_id`, `source_page`, `quote`), và `computation` (dấu vết phép tính cho `94` câu tính toán và các bước quy đổi đơn vị). Mỗi câu ngoài phạm vi đều lưu `"Không đủ bằng chứng trong corpus để trả lời."`, `needs_more_evidence: true` và `unanswerable_reason`.

Script `src/evaluate/evaluate.py` (`evaluation/evaluation_protocol.md` v9) tính ngoại tuyến bốn nhóm thước đo trên top-10 `predicted_chunk_ids` đã lưu:

- Truy hồi (`evidence_den`: 144 test, 40 dev): `recall_at_3`, `recall_at_5`, `recall_at_10`, `mrr_at_3`, `mrr_at_5`, `mrr_at_10`, `context_precision_at_5`, `context_recall_at_5`.
- Trích dẫn: `citation_precision_top1`, `citation_recall_at_5`, `citation_complete_rate` (yêu cầu đủ `chunk_id`, `page`, `company_id`, `fiscal_year` theo `config/answer_policy.yaml`), `page_accuracy`.
- Đáp án số và kỳ tài chính: `numeric_match` (sai số `max(1e-4, |gv| * 1e-6)`), `exact_match`, `company_accuracy`, `year_accuracy`, `version_accuracy`, `period_accuracy` (so khớp tập đa thực thể phân cách bởi `|` qua `parse_pipe_set()`), `unsupported_claim_rate` (cô lập từng chunk bằng `CHUNK_SEP`, quy đổi đơn vị trong dải `1e3..1e12` với dung sai tương đối `1e-3`, loại bỏ số năm tiêu đề `2020-2025`), `faithfulness_heuristic` (`1 - unsupported_claim_rate`) và `answer_relevancy_heuristic`.
- Từ chối và trạng thái (`refusal_den`: 16 test, 4 dev): `decide_status()` gán nhãn `answered`, `partial_answer`, `refused` hoặc `ambiguous`; các chỉ số `refusal_precision`, `refusal_recall`, `false_answer_rate` và nhãn từng câu (`true_refusal`, `missed_refusal`, `false_refusal`, `true_answer`) được xuất ra `evaluation/refusal_labels/refusal_labels_E*.csv`.

Hai phần còn để mở theo thiết kế hoặc chờ hậu kiểm tiếp: `147 / 204` (`72,06%`) mẫu vẫn đang giữ trạng thái `draft-needs-second-reviewer` chờ người kiểm định thứ hai rà soát thủ công (dù đã qua 100% bước đối chiếu tự động câu trích trên chunk với `0` mẫu `pending-answer`), và các câu `ViFinQA` đa bước (như `ViFinQA-368`, trải rộng 4 công ty và 10 chunk) đã có đáp án cuối cùng và chứng cứ chuẩn nhưng chưa gắn nhãn từng bước trung gian (`needs_decomposition` ghi trong `evaluation/pilot_advanced.md`).

## 12. Thiên lệch, Đạo đức và Rủi ro

Bộ `40` báo cáo chỉ bao phủ 4 doanh nghiệp ngành công nghiệp, thép và vật liệu (`HPG`, `HSG`, `NKG`, `MSR`) trong giai đoạn `2020-2024`, giai đoạn biên lợi nhuận ngành thép thu hẹp sau năm 2021 và `MSR` ghi nhận lỗ ròng giai đoạn `2023-2024`. Các mô hình hoặc bộ luật tinh chỉnh trên khoản mục Thông tư `202/2014/TT-BTC` này không thể áp dụng trực tiếp cho ngân hàng, bảo hiểm hoặc chuẩn mực kế toán khác.

Văn bản OCR gốc giữ nguyên sự khác biệt trình bày của đơn vị kiểm toán, bao gồm việc PwC trên `HSG` năm 2024 ghi chi phí giá vốn trong ngoặc âm `(35.008.227.341.981)` trái ngược với KPMG giai đoạn `2020-2023` ghi số dương, hay `MSR` hạch toán bằng `Nghìn VND` trong khi `HPG`, `HSG` và `NKG` ghi theo `VND`. Một số lỗi mất dấu tiếng Việt cục bộ từ OCR (`"doanh thu thuân"`, `"NỢ PHÀI TRẢ"`) vẫn tồn tại nguyên văn trong văn bản chunk.

Corpus chỉ chứa công bố thông tin doanh nghiệp bắt buộc theo luật định (bao gồm họ tên ban điều hành, chủ tịch HĐQT và kiểm toán viên đã công bố công khai). Quét tự động xác nhận `0` dữ liệu PII cá nhân người tiêu dùng và `0` khóa API hay thông tin mật trong `src/`, `app/`, `config/`, `tests/`. Vì `license_status` là `unknown_verify_with_teacher`, các tệp OCR thô trong `data/raw/` tiếp tục bị loại trừ khỏi các commit công khai cho đến khi giảng viên xác nhận.

## 13. Giới hạn và Các trường hợp sử dụng không phù hợp

1. Báo cáo `HPG_2022_consolidated` bị trống `24` trang thuyết minh cuối (`42`, `44-54`, `57-68`) trong bản chụp OCR gốc, nên các câu hỏi chi tiết nằm ngoài trang `1-41` sẽ không tìm được lời giải từ các trang thiếu này (các báo cáo tài chính chính ở các trang đầu vẫn nguyên vẹn).
2. Nhóm `150` câu `table-clean` kế thừa từ `v2/v3` lưu `evidence[].quote` ở dạng tóm tắt hai cột `"metric | raw_value"` thay vì chuỗi con liên tục; `src/cross_review.py` kiểm chứng cả hai token này cùng nằm trên một dòng gạch đứng thực tế trong chunk được trích, trong khi `35` câu `vifinqa` và `7` câu `supplement` có đáp án lưu đúng chuỗi trích nguyên văn liên tiếp.
3. Các phép so sánh nhiều năm có thể chịu ảnh hưởng từ việc phân loại lại số liệu thuyết minh giữa các năm (đã ghi chú rõ trong trường `computation` và `data/annotations/review_report.md` cho `ViFinQA-97`, `ViFinQA-186` và `ViFinQA-709`).
4. Trên tập `dev`, mẫu số từ chối chỉ là `refusal_den = 4` (tập `test` có `16`), nên mỗi dự đoán sai/đúng đơn lẻ sẽ làm thay đổi `refusal_precision` hoặc `refusal_recall` trên `dev` tới `25` điểm phần trăm.
5. Không sử dụng bộ dữ liệu hoặc bản demo này để ra quyết định đầu tư hay tài chính thực tế, không suy diễn kết quả vượt ngoài giai đoạn `2020-2024` hoặc ngoài nhóm `{HPG, HSG, NKG, MSR}`, và không khẳng định khả năng tổng quát hóa sang doanh nghiệp lạ hay báo cáo ngân hàng nếu chưa kiểm thử trên một tập chia tách riêng theo công ty.

## 14. Hướng dẫn tái lập và Truy cập

Pipeline chạy hoàn toàn ngoại tuyến trên CPU trong môi trường **Anaconda** (Python `3.10`, đã kiểm chứng trên phiên bản `3.10.22`) cùng các thư viện được khóa phiên bản trong `requirements.txt` (`scikit-learn==1.7.2`, `pandas==2.3.3`, `numpy==2.2.6`, `scipy==1.15.3`, `PyYAML==6.0.3`, `streamlit==1.65.0`, `huggingface_hub==1.30.0`, `matplotlib==3.10.9`, `Pillow==12.3.0`).

Tạo môi trường Anaconda và cài đặt phụ thuộc (chạy trong **Anaconda Prompt** hoặc PowerShell đã cấu hình `conda`):

```powershell
conda create -n nlp_rag python=3.10 -y
conda activate nlp_rag
pip install -r requirements.txt
```

Tải dữ liệu nguồn về cục bộ (`data/raw/` bị loại trừ khỏi Git):

```powershell
python src\download_vifinqa.py --mode questions --revision 0450088ab22ec946f04f097586967ca405955b3b
python src\download_vifinqa.py --mode corpus --tickers HPG HSG NKG MSR --years 2020 2021 2022 2023 2024 --revision 0450088ab22ec946f04f097586967ca405955b3b
```

Dựng lại các chunk đã xử lý, bản ghi bảng, bộ Gold `v4` (`seed = 42`), hậu kiểm phân tầng và tài liệu dữ liệu:

```powershell
python src\select_corpus.py --tickers HPG HSG NKG MSR --years 2020 2021 2022 2023 2024 --versions consolidated separate
python src\filter_questions.py --tickers HPG HSG NKG MSR --years 2020 2021 2022 2023 2024
python src\audit_ocr.py
python src\build_chunks.py
python src\build_table_records.py
python src\build_supplement_gold.py
python src\build_gold.py --force-v1
python src\build_expanded_gold_v2.py
python src\build_expanded_gold_v3.py
python src\resolve_vifinqa_and_dev_refusal.py
python src\cross_review.py
python src\build_data_docs.py
python src\data_quality_report.py
```

Chạy đánh giá (`E0-E8`), bộ `35` unit test và `4` kiểm thử ứng dụng demo:

```powershell
foreach ($r in "E0","E1","E2","E3","E4","E5","E6","E7","E8") { python src\evaluate\evaluate.py --run $r }
python -m unittest discover -s tests -v
python app\check_demo.py
```
