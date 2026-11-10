# Báo cáo kiểm tra chất lượng dữ liệu

Dự án: BTL CSC4007, đề tài 6 - Hỏi đáp báo cáo tài chính có trích dẫn bằng RAG.

- Script sinh báo cáo: `src/data_quality_report.py`
- Nguồn dữ liệu: `https://huggingface.co/datasets/AIGuruTinix/ViFinQA`, revision `0450088ab22ec946f04f097586967ca405955b3b`
- Các bước chạy lại được: `src/download_vifinqa.py` -> `src/select_corpus.py` -> `src/filter_questions.py` -> `src/build_chunks.py` -> `src/audit_ocr.py` -> `src/data_quality_report.py`

## 1. Schema và tính đầy đủ

### 1.1 Bảng kiểm đếm trước và sau khi lọc tập câu hỏi

| bước | số dòng | ghi chú |
|---|---|---|
| Tập câu hỏi gốc của ViFinQA | 1012 | `questions/questions.jsonl`, chỉ có trường `id` và `question` |
| Sau khi lọc theo corpus | 35 | `data/processed/questions_matched.csv` |
| Bị loại | 977 | `data/processed/questions_dropped.csv`, có lý do từng dòng |
| Tổng kiểm lại | 1012 | khớp với tập gốc |

### 1.2 Bảng kiểm đếm trước và sau khi sinh chunk

| bước | số đơn vị | ghi chú |
|---|---|---|
| File báo cáo OCR trong `data/raw/` | 40 | 4 doanh nghiệp x 5 năm x 2 bản (hợp nhất / riêng) |
| Tổng số trang trong các file | 2437 | tính từ `ocr_audit.csv` |
| Trang rỗng bị loại | 30 | lỗi OCR ở file nguồn, xem mục 4 |
| Chunk dùng cho truy hồi | 2407 | `data/processed/chunks.jsonl`, 1 chunk = 1 trang |
| Chunk có chứa bảng | 1634 | (67.9%) |
| Tổng bảng OCR đã parse | 2585 | |

### 1.3 Kiểm tra trường bắt buộc và kiểu dữ liệu

| tệp | số dòng | cột bắt buộc | ID trùng | ID rỗng |
|---|---|---|---|---|
| `data/processed/corpus_manifest.csv` | 40 | document_id | 0 | 0 |
| `data/processed/ocr_audit.csv` | 40 | document_id | 0 | 0 |
| `data/processed/questions_matched.csv` | 35 | question_id | 0 | 0 |
| `data/processed/questions_dropped.csv` | 977 | id | 0 | 0 |
| `data/processed/chunks.jsonl` | 2407 | chunk_id | 0 | 0 |

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
|---|---|
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
Nhóm phải tự xây bộ gold và tự kiểm chứng.

### 5.1 Phân bố tập câu hỏi đã lọc

| đặc trưng | phân bố |
|---|---|
| doanh nghiệp HPG | 28 câu |
| doanh nghiệp NKG | 27 câu |
| doanh nghiệp HSG | 27 câu |
| doanh nghiệp MSR | 25 câu |

| năm 2020 | 5 câu |
| năm 2021 | 14 câu |
| năm 2022 | 21 câu |
| năm 2023 | 14 câu |
| năm 2024 | 10 câu |

| đặc trưng | số câu |
|---|---|
| dạng câu hỏi: numeric | 29 |
| dạng câu hỏi: computation | 6 |
| đơn vị được hỏi: (không rõ) | 16 |
| đơn vị được hỏi: lần | 7 |
| đơn vị được hỏi: nghìn tỷ đồng | 6 |
| đơn vị được hỏi: % | 2 |
| đơn vị được hỏi: triệu đồng | 2 |
| đơn vị được hỏi: tỷ đồng | 1 |
| đơn vị được hỏi: trăm tỷ đồng | 1 |
| câu hỏi nhiều doanh nghiệp | 25 |
| câu hỏi cần phép tính | 20 |
| câu hỏi về công ty mẹ | 4 |

### 5.2 Khoảng cách với định mức 50 câu gold

- Định mức đề tài 6: **tối thiểu 50 câu hỏi** trên corpus thực dùng, chia 10 dev + 40 test.
- Số câu hỏi ViFinQA có sẵn khớp corpus hiện tại: **35**.
- Phần còn thiếu, nhóm phải **tự tạo và tự kiểm chứng**: cần bổ sung tối thiểu 15 câu nữa.

Nguồn bổ sung được đề xuất:

1. Bộ câu hỏi ViFinQA gốc có mã CK trong ngoặc, tự đổi mã CK sang tên đầy đủ để so khớp.
2. Đặt câu hỏi mới theo bảng chỉ tiêu trong các báo cáo đã tải, có trích dẫn trang.
3. Bổ sung câu hỏi **thiếu bằng chứng** (cần ít nhất 08 câu trong tập test) bằng cách
   hỏi về chỉ tiêu không có trong báo cáo đã tải, ví dụ hỏi năm ngoài phạm vi corpus.

> Khi không đủ 50 câu hợp lệ, phải báo giảng viên trước giai đoạn thực nghiệm (Mục 4.6.2).

### 5.3 Chưa có gold

| hạng mục | trạng thái |
|---|---|
| qa_gold.jsonl | chưa tạo, cần giai đoạn gắn nhãn |
| annotation_guideline.md | chưa tạo |
| review_log.csv (hậu kiểm 20%) | chưa tạo |
| danh sách ID chia dev/test | chưa tạo |

## 6. Chống rò rỉ dữ liệu

| nguồn rò rỉ | biện pháp |
|---|---|
| Cùng báo cáo xuất hiện ở cả dev và test | corpus dùng chung cho mọi câu hỏi, đây là đặc trưng của bài toán QA trên báo cáo tài chính. Nhóm phải **công bố rõ** cùng báo cáo có thể xuất hiện ở cả hai split |
| Câu hỏi paraphrase gần trùng nhau rơi vào hai split | tách theo câu hỏi và kiểm tra gần trùng bằng cosine similarity trước khi chia |
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
| Nhãn do LLM hỗ trợ tạo | chưa có nhãn nào, khi dùng LLM hỗ trợ gắn nhãn phải có người kiểm chứng |

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
| doanh nghiep ngoai corpus | 951 |
| nam ngoai corpus | 21 |
| khong xac dinh duoc doanh nghiep | 4 |
| khong co nam trong cau hoi | 1 |

Danh sách đầy đủ từng câu kèm lý do nằm ở `data/processed/questions_dropped.csv`.

## 9. Tóm tắt rủi ro

| rủi ro | mức độ | giải pháp |
|---|---|---|
| Chưa đủ 50 câu gold | cao | tự tạo và kiểm chứng bổ sung, hoặc báo giảng viên |
| Lỗi đơn vị tiền khi chấm điểm | cao | chuẩn hóa đơn vị ở tầng processed, tính metric theo đơn vị chuẩn |
| OCR bỏ sót trang (HPG 2022 hợp nhất) | trung bình | ghi nhận trong audit, loại khỏi chunk |
| Bảng HTML vỡ cột | thấp | tỷ lệ hàng lệch cột đo được trong `ocr_audit.csv` |
| Câu hỏi nhiều doanh nghiệp cần nhiều báo cáo | trung bình | phần nâng cao, không bắt buộc |
| Chưa xác minh quyền sử dụng dữ liệu | cao | hỏi giảng viên, ghi vào data_card |
