# Giao thức đánh giá và chống rò rỉ (Mục 2.3, Mục 5.4)

Phiên bản: v4. Ngày ban hành: 2026-11-10. Áp dụng cho toàn bộ E0-E8.
Thay đổi ở v4: thêm E8 lookup có cấu trúc trên `data/processed/table_records.jsonl` (company, year, statement, metric, value, unit, page, source_chunk_id, confidence) trước khi RAG giải thích; lần đầu numeric_match và exact_match đạt 1.0 trên câu bổ sung có đáp án. Thay đổi ở v3: mở rộng phạm vi sang E4-E7 (rerank nhẹ thay cross-encoder offline, rewrite truy vấn, index bảng riêng, contextual chunk); E3 trở thành baseline lọc cứng tái lập được. Thay đổi ở v2: tách bạch retrieval quality và answer quality, bổ sung context precision/recall,
refusal precision/recall, citation precision/recall, period/company/year/version/page accuracy,
unsupported-claim rate và hai heuristic thay thế faithfulness/answer_relevancy.

## 1. Phạm vi và nguyên tắc bất biến

- Split: dev 10 câu, test 40 câu, seed 42, khóa tại
  `data/splits/split_meta.json` (sha256 `43276e350a9aa755...`).
- Chỉ chọn tham số, prompt, mô hình bằng **dev**. Chỉ dùng **test** để công bố
  kết quả cuối. Ai nhìn test để tuning phải khai báo và thiết kế lại tập test
  độc lập.
- Cả 9 cấu hình E0-E8 dùng cùng test và cùng script chấm
  (`src/evaluate/evaluate.py`).

## 2. Định nghĩa metric (Đề tài 6, Mục 4.6.5, RAGAS)

### 2.1 Retrieval quality (chỉ trên câu có evidence)

| Metric | Ký hiệu | Định nghĩa | Cách chấm |
|---|---|---|---|
| Recall@k | R@3, R@5, R@10 | tỷ lệ câu có ít nhất một chunk bằng chứng gold lọt vào top-k | so `chunk_id` dự đoán với `evidence[].chunk_id` của gold |
| MRR@k | MRR@3, MRR@5, MRR@10 | trung bình nghịch đảo hạng của bằng chứng đúng đầu tiên, 0 nếu ngoài top-k | cùng tập relevance với R@k |
| Context precision@5 | ctxP@5 | tỷ lệ chunk trong top-5 thực sự là evidence | `|top-5 giao evidence| / 5` |
| Context recall@5 | ctxR@5 | tỷ lệ evidence được phủ bởi top-5 | `|top-5 giao evidence| / |evidence|` |

Ghi chú: file prediction hiện chỉ lưu top-5 nên R@10 và MRR@10 bằng với @5.
Test chỉ có 5 câu có evidence nên mỗi câu đúng sai làm R@5 nhảy 0.2.

### 2.2 Citation quality

| Metric | Định nghĩa | Cách chấm |
|---|---|---|
| Citation precision@top1 | top-1 có thực sự hỗ trợ câu trả lời không | top-1 `chunk_id` nằm trong evidence, giữ tên cũ `citation_correctness` để tương thích |
| Citation recall@5 | evidence có lọt vào top-5 trích dẫn không | giống R@5 trên nhóm có evidence |
| Page accuracy | trang trích dẫn có chứa giá trị hoặc bảng đúng không | `predicted_page` so với `source_page` của gold, chỉ trên câu có `source_page` |

### 2.3 Answer quality (số và nghiệp vụ tài chính)

| Metric | Định nghĩa | Cách chấm |
|---|---|---|
| Numeric match | đáp án số đúng sau chuẩn hóa đơn vị, dấu âm, dấu phẩy/thập phân | trích mọi số trong `predicted_answer`, chuẩn hóa `(983)` thành âm, `3,2` thành `3.2`, giữ `%`, so với `value` của gold với dung sai `max(1e-4, |gv|*1e-6)` |
| Exact match | khớp nguyên văn sau chuẩn hóa chuỗi | chữ thường, gọn khoảng trắng |
| Period accuracy | đúng đồng thời công ty, năm và bản báo cáo | `predicted_company`, `predicted_year`, `predicted_report_version` so với `company_id`, `fiscal_year`, `report_id` |
| Company/year/version accuracy | từng thành phần của period | chấm riêng để biết lỗi rơi vào đâu |
| Unsupported-claim rate | tỷ lệ câu trả lời có ít nhất một khẳng định số không tìm thấy trong context | mọi số trong đáp án phải xuất hiện trong top-5 chunk, thiếu chunk là tính không đạt |
| Faithfulness heuristic | thay thế minh bạch cho faithfulness của RAGAS | `1 - unsupported-claim rate`, đo tính nhất quán với context |
| Answer relevancy heuristic | thay thế minh bạch cho answer relevancy của RAGAS | `(numeric đúng + từ chối đúng) / tổng số câu`, đo mức câu trả lời giải quyết câu hỏi |

Faithfulness đo tính nhất quán của câu trả lời với context, còn answer relevancy
đo mức câu trả lời thực sự giải quyết câu hỏi. Hai chỉ số này bổ trợ chứ không thay thế nhau.
Bản LLM judge của cả hai chưa áp dụng vì pipeline không gọi LLM API, không có chi phí
suy luận ngoài, mọi cột heuristic đều tính được lại từ file prediction và `chunks.jsonl`.

### 2.4 Refusal (câu thiếu bằng chứng)

| Metric | Định nghĩa | Cách chấm |
|---|---|---|
| Refusal precision | hệ từ chối có đúng chỗ không, không từ chối sai khi có bằng chứng | `từ chối đúng / tổng số câu hệ từ chối` |
| Refusal recall | hệ có bỏ sót câu thiếu bằng chứng không | `từ chối đúng / 8 câu needs_more_evidence`, giữ tên cũ `refusal_rate` để tương thích |
| Refusal den | mẫu số của nhóm thiếu bằng chứng | 8 ở test, 0 ở dev |

Đánh giá retrieval và answer riêng, không chỉ chấm câu trả lời cuối.
Trường hợp retrieval đúng nhưng answer sai thể hiện qua R@k cao kèm numeric
match thấp, phải nêu trong `error_analysis.md`.

## 3. Xử lý câu không đủ bằng chứng

- 8 câu `needs_more_evidence=true` đều nằm ở test.
- Hệ thống phải trả lời đúng nguyên văn
  `Không đủ bằng chứng trong corpus để trả lời.`
- Mọi câu trả lời bằng số cho 8 câu này đều tính là sai, kể cả khi số trùng
  với một ô bảng nào đó trong corpus.
- Retrieval cho 8 câu này không tính R@k vào điểm chính, chỉ báo cáo riêng.

## 4. Chống rò rỉ

- Tách theo câu hỏi, không tách theo chunk. Mỗi chunk thuộc đúng một trang,
  không chia chunk qua hai split.
- Kiểm tra paraphrase gần trùng bằng chuẩn hóa chữ thường toàn câu hỏi trước
  khi chia (`src/build_gold.py`): 50 câu không trùng khớp nhau.
- Công bố rõ: cùng một báo cáo có thể xuất hiện ở cả dev và test. Đây là đặc
  trưng của QA trên báo cáo tài chính, corpus dùng chung cho mọi câu hỏi.
- Bản consolidated và separate của cùng công ty năm là hai tài liệu khác nhau,
  giữ cả hai, phân biệt bằng `report_version`.
- Test đã khóa trước khi chọn cấu hình cuối: hash trong `split_meta.json`,
  bản sao nguyên vẹn tại `evaluation/split_freeze.json`.
  Ngày khóa: 2026-11-10. Từ sau mốc này, mọi thay đổi split phải đổi version.

## 5. Khẳng định tổng quát

- Nhóm không khẳng định tổng quát sang doanh nghiệp hay năm ngoài corpus
  (HPG, HSG, NKG, MSR giai đoạn 2020-2024).
- Nếu sau này khẳng định tổng quát, phải thử nghiệm tách riêng theo doanh
  nghiệp hoặc năm và báo cáo riêng, không gộp vào metric chính.
