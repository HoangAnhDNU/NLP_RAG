# Báo cáo kiểm tra chất lượng dữ liệu

Dự án: BTL CSC4007, đề tài 6 - Hỏi đáp báo cáo tài chính có trích dẫn bằng RAG.

- Script sinh báo cáo: `src/data_quality_report.py`
- Nguồn dữ liệu: `https://huggingface.co/datasets/AIGuruTinix/ViFinQA`, revision `0450088ab22ec946f04f097586967ca405955b3b`
- Các bước chạy lại được: `src/download_vifinqa.py` -> `src/select_corpus.py` -> `src/filter_questions.py` -> `src/build_chunks.py` -> `src/build_table_records.py` -> `src/audit_ocr.py` -> `src/build_supplement_gold.py` -> `src/build_gold.py` (guard `--force-v1`) -> `src/build_expanded_gold_v2.py` -> `src/build_expanded_gold_v3.py` -> `src/resolve_vifinqa_and_dev_refusal.py` -> `src/cross_review.py` -> `src/build_data_docs.py` -> `src/data_quality_report.py`

## 1. Schema và tính đầy đủ

### 1.1 Bảng kiểm đếm trước và sau khi lọc tập câu hỏi

| bước | số dòng | ghi chú |
|---|---|---|
| Tập câu hỏi gốc của ViFinQA | 1012 | `questions/questions.jsonl`, chỉ có trường `id` và `question` |
| Sau khi lọc theo corpus | 35 | `data/processed/questions_matched.csv` |
| Bị loại | 977 | `data/processed/questions_dropped.csv`, có lý do từng dòng |
| Tổng kiểm lại | 1012 | khớp với tập gốc |
| Bộ gold sau khi bù | 204 | `data/annotations/qa_gold.jsonl` |

### 1.2 Bảng kiểm đếm trước và sau khi sinh chunk

| bước | số đơn vị | ghi chú |
|---|---|---|
| File báo cáo OCR trong `data/raw/` | 40 | 4 doanh nghiệp x 5 năm x 2 bản (hợp nhất / riêng) |
| Tổng số trang trong các file | 2437 | tính từ `ocr_audit.csv` |
| Trang rỗng bị loại | 30 | lỗi OCR ở file nguồn, xem mục 4 |
| Chunk dùng cho truy hồi | 2407 | `data/processed/chunks.jsonl`, 1 chunk = 1 trang |
| Chunk có chứa bảng | 1634 | (67.9%) |
| Tổng bảng OCR đã parse | 2585 | |
| Bản kê chuẩn `data/data_manifest.csv` | 244 | 40 corpus + 204 gold |

### 1.3 Kiểm tra trường bắt buộc và kiểu dữ liệu

| tệp | số dòng | cột bắt buộc | ID trùng | ID rỗng |
|---|---|---|---|---|
| `data/processed/corpus_manifest.csv` | 40 | document_id | 0 | 0 |
| `data/processed/ocr_audit.csv` | 40 | document_id | 0 | 0 |
| `data/processed/questions_matched.csv` | 35 | question_id | 0 | 0 |
| `data/processed/questions_dropped.csv` | 977 | id | 0 | 0 |
| `data/data_manifest.csv` | 244 | item_id | 0 | 0 |
| `data/processed/chunks.jsonl` | 2407 | chunk_id | 0 | 0 |
| `data/annotations/qa_gold.jsonl` | 204 | question_id | 0 | 0 |

Nhãn ngoài danh mục: `answer_type` trong gold chỉ gồm `computation, numeric, unanswerable`, đúng danh mục `numeric, computation, unanswerable`. `review_status` chỉ gồm `draft-needs-second-reviewer, reviewed-agree`, đúng danh mục hợp lệ (có **0** câu `pending-answer`).

Đường dẫn nguồn: mọi `local_path` trong manifest trỏ tới file `data/raw/vifinqa/financial_statements/<TICKER>/<YEAR>/..._extracted.txt` tồn tại. 

### 1.4 Bản mã Unicode

Toàn bộ tệp được đọc và ghi với `encoding="utf-8"`. Văn bản tiếng Việt giữ nguyên dấu,
không bỏ dấu hay chuyển sang ASCII. Chuẩn hóa dùng NFC (`unicodedata.normalize("NFC", ...)`).
Bỏ dấu chỉ dùng tạm thời trong `src/preprocess/company_match.py` để so khớp tên doanh nghiệp,
không áp dụng cho dữ liệu lưu xuống.

## 2. Nội dung

### 2.1 Độ dài trang

| document_id | số trang | trung bình ký tự/trang | ngắn nhất | dài nhất |
|---|---|---|---|---|
| HPG_2020_consolidated | 77 | 843.5 | 84 | 2752 |
| HPG_2020_separate | 53 | 819.9 | 82 | 2594 |
| HPG_2021_consolidated | 80 | 825.6 | 84 | 2879 |
| HPG_2021_separate | 51 | 826.4 | 82 | 2546 |
| HPG_2022_consolidated | 68 | 596.9 | 0 | 2995 |
| HPG_2022_separate | 44 | 686.3 | 82 | 2386 |
| HPG_2023_consolidated | 65 | 806.1 | 84 | 3891 |
| HPG_2023_separate | 42 | 681.0 | 82 | 2269 |
| HPG_2024_consolidated | 67 | 749.9 | 84 | 3007 |
| HPG_2024_separate | 40 | 733.3 | 82 | 2273 |
| HSG_2020_consolidated | 61 | 727.3 | 54 | 2394 |
| HSG_2020_separate | 61 | 647.4 | 73 | 4617 |
| HSG_2021_consolidated | 62 | 695.4 | 48 | 2458 |
| HSG_2021_separate | 61 | 617.7 | 0 | 2309 |
| HSG_2022_consolidated | 60 | 710.8 | 42 | 2359 |
| HSG_2022_separate | 56 | 613.8 | 78 | 2325 |
| HSG_2023_consolidated | 59 | 705.7 | 0 | 2353 |
| HSG_2023_separate | 54 | 619.7 | 98 | 2289 |
| HSG_2024_consolidated | 58 | 875.3 | 27 | 2500 |
| HSG_2024_separate | 61 | 775.8 | 27 | 2408 |
| NKG_2020_consolidated | 44 | 825.4 | 24 | 2448 |
| NKG_2020_separate | 43 | 849.4 | 24 | 2516 |
| NKG_2021_consolidated | 48 | 751.0 | 7 | 2224 |
| NKG_2021_separate | 48 | 736.3 | 14 | 2313 |
| NKG_2022_consolidated | 48 | 923.7 | 0 | 2444 |
| NKG_2022_separate | 46 | 900.6 | 0 | 2680 |
| NKG_2023_consolidated | 48 | 887.2 | 0 | 2825 |
| NKG_2023_separate | 48 | 862.9 | 0 | 2588 |
| NKG_2024_consolidated | 50 | 876.9 | 44 | 2612 |
| NKG_2024_separate | 49 | 904.1 | 63 | 2658 |
| MSR_2020_consolidated | 69 | 1190.6 | 145 | 3226 |
| MSR_2020_separate | 24 | 1064.8 | 129 | 2435 |
| MSR_2021_consolidated | 146 | 1214.9 | 107 | 3514 |
| MSR_2021_separate | 48 | 1313.6 | 90 | 12639 |
| MSR_2022_consolidated | 143 | 1177.3 | 107 | 3729 |
| MSR_2022_separate | 49 | 1038.3 | 91 | 2486 |
| MSR_2023_consolidated | 151 | 1136.1 | 107 | 3607 |
| MSR_2023_separate | 51 | 1018.5 | 91 | 2592 |
| MSR_2024_consolidated | 78 | 1068.1 | 107 | 3126 |
| MSR_2024_separate | 26 | 911.7 | 91 | 2241 |

### 2.2 Trang không có bảng

- Tổng cộng **803 / 2437** trang không chứa bảng (33.0%).
- Đây là các trang văn bản thuần như báo cáo của Ban Giám đốc, ý kiến kiểm toán viên,
  thuyết minh dạng chữ, mục lục. Nhóm vẫn giữ các trang này trong corpus vì chúng chứa
  thông tin về chính sách kế toán và thuyết minh, có thể cần cho câu hỏi dạng văn bản.

### 2.3 Trùng lặp và gần trùng

| kiểm tra | kết quả |
|---|---|---|
| Hai bản consolidated và separate của cùng công ty năm có nội dung trùng nhau | 40 cặp, kiểm tra bằng sha256 trong manifest, hai bản khác nhau |
| Cùng một document_id xuất hiện nhiều lần | 0 |
| Chunk trùng nội dung giữa các báo cáo | 0 chunk trùng ID |

Mỗi báo cáo có `sha256` riêng trong `corpus_manifest.csv`, nên có thể kiểm chứng lại
file còn nguyên so với lúc tải. Việc kiểm tra trùng nội dung ở mức đoạn văn sẽ làm
ở bước chống rò rỉ dữ liệu, cùng với việc tách dev/test theo câu hỏi.

## 3. Số liệu kinh tế

### 3.1 Kiểm tra định dạng số

| loại kiểm tra | tổng số lần | cách xử lý trong `src/build_chunks.py` |
|---|---|---|
| Số có dấu phân cách nghìn (ví dụ `91.279.041.771.826`) | 966 | giữ nguyên trong text, chuẩn hóa qua `normalize_number()` |
| Số thập phân dấu phẩy (ví dụ `3,2`) | 615 | chuyển thành `3.2`, không nhân với 100 |
| Số âm trong ngoặc (ví dụ `(983.237)`) | 0 | chuyển thành `-983237` |
| Ký hiệu phần trăm | 1145 | giữ nguyên kèm dấu `%` |

Quy tắc chống lỗi hệ số 100: số thập phân dấu phẩy chỉ đổi dấu phân cách, không nhân 100. Ký hiệu `%` luôn đi kèm số, không tự suy ra tỷ lệ.

### 3.2 Đơn vị tiền

| đơn vị | số chunk |
|---|---|
| (không xác định) | 1680 |
| đồng | 478 |
| triệu đồng | 142 |
| tỷ đồng | 107 |

Đơn vị được suy ra theo thứ tự: (1) hàng header của bảng, ví dụ `31/12/2023Triệu VND`;
(2) dự phòng, dò trong văn bản trang. Trường `unit` trên mỗi chunk là đơn vị của số liệu
trong trang đó. Chunk không xác định được đơn vị thì để rỗng, không đoán.

**Cảnh báo cần lưu ý khi chấm điểm:** câu hỏi ViFinQA hỏi đơn vị ở mức
`triệu đồng`, `tỷ đồng`, `nghìn tỷ đồng`, trong khi báo cáo tài chính Việt Nam ghi
`VND` (đồng tuyệt đối) hoặc `triệu VND`. Chuẩn hóa đơn vị là điểm lỗi lớn nhất của
hệ thống, và là một trong các nhóm lỗi bắt buộc báo cáo trong `error_analysis.md`.

## 4. Nhiễu OCR

- Ký tự trang trí (○ ● ◎ ...): **1317** lần, loại bỏ khi sinh chunk.
- Công thức LaTeX lọt từ phần thuyết minh toán học: **486** lần, loại bỏ khi sinh chunk.
- Ký tự thay thế `�`: 0 chunk bị ảnh hưởng.
- Trang rỗng trong file nguồn: **30** trang, chi tiết ở `report/ocr_audit.md` mục 6.

## 5. Gold

ViFinQA công khai **không có gold answer, không có evidence và không có split**.
Nhóm đã tự xây bộ gold và tự kiểm chứng bằng script.

### 5.1 Phân bố bộ gold

| đặc trưng | phân bố |
|---|---|
| answer_type: computation | 94 câu |
| answer_type: numeric | 90 câu |
| answer_type: unanswerable | 20 câu |
| split: test | 160 câu |
| split: dev | 44 câu |
| nguồn: table-clean | 150 câu |
| nguồn: vifinqa | 35 câu |
| nguồn: supplement | 15 câu |
| nguồn: dev-refusal | 4 câu |
| thiếu bằng chứng (`needs_more_evidence=true`) | 20 câu |
| có đơn vị số liệu (`unit` khác rỗng) | 183 câu |
| có bằng chứng (`evidence` khác rỗng) | 184 câu |

| đơn vị trong gold | số câu |
|---|---|
| tỷ đồng | 89 |
| nghìn tỷ đồng | 46 |
| (rỗng) | 21 |
| triệu đồng | 12 |
| % | 11 |
| đồng | 10 |
| điểm phần trăm | 9 |
| lần | 4 |
| nghìn đồng | 1 |
| trăm tỷ đồng | 1 |

| trạng thái hậu kiểm | số câu |
|---|---|
| draft-needs-second-reviewer | 147 |
| reviewed-agree | 57 |

### 5.2 Ví dụ ranh giới

| cặp ranh giới | quy tắc phân xử (theo `annotation_guideline.md`) |
|---|---|
| Cùng chỉ tiêu nhưng khác bản báo cáo (hợp nhất so với riêng) | chỉ lấy đúng bản của phạm vi câu hỏi; phạm vi công ty mẹ dùng bản `separate`, còn lại dùng `consolidated` |
| Cùng số nhưng khác năm (cột 2024 so với 2023) | chỉ lấy ô đúng năm hỏi, không lấy cột năm so sánh |
| Đơn vị báo cáo `Nghìn VND` so với đơn vị hỏi `tỷ đồng` | quy đổi bằng script và làm tròn 4 chữ số thập phân, ghi công thức vào `computation` |
| Câu hỏi giá thị trường, quý, kế hoạch tương lai | gắn `needs_more_evidence=true`, đáp án luôn là `Không đủ bằng chứng trong corpus để trả lời.` |

### 5.3 Nhãn unknown và bất đồng

| hạng mục | trạng thái |
|---|---|
| Nhãn unknown | không có nhãn unknown |
| Hậu kiểm chéo >= 20% (`src/cross_review.py`) | đạt **57/204 (27.94%)** `reviewed-agree` (gồm 53 mẫu kiểm định phân tầng v4 + 4 mẫu `supplement` duyệt trước đó, chi tiết tại `data/annotations/review_report.md`) |
| Bất đồng và cách phân xử | **0 bất đồng** trong đợt hậu kiểm chéo v4 (`agree=53, disagree=0`); khi phát sinh bất đồng, tra lại chunk gốc và cập nhật guideline thống nhất thay vì sửa lẻ |

### 5.4 Độ đầy đủ của evidence

- Các câu trả lời được có ít nhất một dòng `quote` đối chiếu trực tiếp với chunk trong `chunks.jsonl` (100% `vifinqa` và `supplement` khớp nguyên văn).
- Các câu thiếu bằng chứng có `evidence` rỗng và `gold_answer` là câu từ chối chuẩn.
- `review_log.csv` có 204 dòng theo dõi trạng thái từng item.

### 5.5 Đóng băng dev/test

- Dev 44 câu (gồm 4 câu thiếu bằng chứng), test 160 câu (gồm 16 câu thiếu bằng chứng), seed 42, version v4, sha256 `0012ebccd6712b44...`.
- Toàn bộ câu mới thêm vào dev ở v4 là câu từ chối ngoài corpus (`DEV-REF-01..04`); 160 câu test v3 được giữ nguyên vẹn không rò rỉ.
- Tách theo câu hỏi, kiểm tra trùng câu hỏi theo chuẩn hóa chữ thường, không phát hiện trùng khớp.

## 6. Chống rò rỉ dữ liệu

| nguồn rò rỉ | biện pháp |
|---|---|
| Cùng báo cáo xuất hiện ở cả dev và test | corpus dùng chung cho mọi câu hỏi, đây là đặc trưng của bài toán QA trên báo cáo tài chính. Nhóm **công bố rõ** cùng báo cáo có thể xuất hiện ở cả hai split |
| Câu hỏi paraphrase gần trùng nhau rơi vào hai split | tách theo câu hỏi và kiểm tra trùng khớp sau chuẩn hóa chữ thường trước khi chia; không phát hiện trùng |
| Chunk của cùng một trang rơi vào hai split | mỗi chunk thuộc đúng một câu hỏi gold, không tách chunk |
| Bản consolidated và separate của cùng công ty năm | hai bản có nội dung khác nhau, được giữ cả hai trong corpus và ghi rõ `report_version` |
| Dùng test để chọn tham số | theo Mục 5.4, chọn tham số bằng dev, chỉ công bố kết quả trên test |

## 7. Pháp lý và đạo đức

| kiểm tra | kết quả |
|---|---|
| Có API key trong repo | không có |
| Có PII trong dữ liệu | không phát hiện, dữ liệu là báo cáo tài chính công khai |
| Quyền sử dụng dataset | `license_status` trong manifest để là `unknown_verify_with_teacher`, **phải xác minh với giảng viên trước khi công bố** |
| Công bố lại dữ liệu | không nên đưa nguyên file OCR lên repo công khai, chỉ công bố manifest, chunk đã xử lý và script tải lại |
| Nhãn do LLM hỗ trợ tạo | câu bổ sung và câu sạch do nhóm tự đặt, đáp án do script trích từ chunk, người thứ hai hậu kiểm; không dùng nhãn LLM chưa kiểm chứng làm gold |

## 8. Danh sách ID mẫu bị loại hoặc chỉnh

### 8.1 Báo cáo bị loại khỏi corpus

Không có báo cáo nào bị loại khỏi `data/raw/`. Toàn bộ 4 doanh nghiệp x 5 năm x 2 bản
đều được giữ. Tập câu hỏi bị lọc theo corpus, không lọc báo cáo.

### 8.2 Trang bị loại khỏi tập chunk

| document_id | số trang rỗng | danh sách trang |
|---|---|---|
| HPG_2022_consolidated | 24 | 42, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68 |
| HSG_2021_separate | 1 | 61 |
| HSG_2023_consolidated | 1 | 59 |
| NKG_2022_consolidated | 1 | 48 |
| NKG_2022_separate | 1 | 46 |
| NKG_2023_consolidated | 1 | 48 |
| NKG_2023_separate | 1 | 48 |

Lý do: các trang này hoàn toàn trống trong file OCR nguồn, không có nội dung để truy hồi.

### 8.3 Câu hỏi bị loại khỏi tập ứng viên

| lý do loại | số câu |
|---|---|
| doanh nghiệp ngoài corpus | 951 |
| năm ngoài corpus | 21 |
| khong xac dinh duoc doanh nghiep | 4 |
| khong co nam trong cau hoi | 1 |

Danh sách đầy đủ từng câu kèm lý do nằm ở `data/processed/questions_dropped.csv`.

## 9. Tóm tắt rủi ro

| rủi ro | mức độ | giải pháp |
|---|---|---|
| Phần còn lại chưa hậu kiểm bậc 2 | thấp | Đã giải toàn bộ 35 câu ViFinQA (`0` `pending-answer`) và hậu kiểm chéo **57/204 (27.94%)** `reviewed-agree`; mở rộng hậu kiểm nốt các câu `draft-needs-second-reviewer` khi có thêm reviewer |
| Lỗi đơn vị tiền khi chấm điểm | cao | chuẩn hóa đơn vị ở tầng processed, tính metric theo đơn vị chuẩn |
| OCR bỏ sót trang (HPG 2022 hợp nhất) | trung bình | ghi nhận trong audit, loại khỏi chunk |
| Bảng HTML vỡ cột | thấp | tỷ lệ hàng lệch cột đo được trong `ocr_audit.csv` |
| Câu hỏi nhiều doanh nghiệp cần nhiều báo cáo | trung bình | phần nâng cao, không bắt buộc |
| Chưa xác minh quyền sử dụng dữ liệu | cao | hỏi giảng viên, ghi vào data_card |

