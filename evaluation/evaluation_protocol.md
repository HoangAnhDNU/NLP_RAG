# Giao thức đánh giá và chống rò rỉ (Mục 2.3, Mục 5.4)

Phiên bản: v8. Ngày ban hành: 2026-11-10. Áp dụng cho toàn bộ E0-E8.
Thay đổi ở v8: gold chính thức mở rộng từ 127 lên 200 câu
(giữ 127 câu v2, thêm 73 câu tổng hợp sạch `source=table-clean` đợt B do `src/build_expanded_gold_v3.py` sinh;
tổng table-clean 150 câu: 55 T1, 44 T2, 43 T3, 8 T5, đáp án quy về VND, chờ hậu kiểm thứ hai);
split v3 dev 40 câu, test 160 câu, seed 42, 16 câu thiếu bằng chứng đều nằm ở test.
Thay đổi ở v6: tách `evaluation/` thành `test_predictions/`, `dev_predictions/`,
`refusal_labels/` (mỗi loại một thư mục riêng).
Thay đổi ở v5: refusal thành chính sách đo được với 4 trạng thái
(answered, partial_answer, refused, ambiguous), thêm false_answer_rate,
citation_complete_rate và nhãn chi tiết từng câu
(`evaluation/refusal_labels/refusal_labels_E{0..8}.csv`); chính sách tại
`src/retrieval/answer_policy.py` và `config/answer_policy.yaml`.
Thay đổi ở v4: thêm E8 lookup có cấu trúc trên `data/processed/table_records.jsonl` (company, year, statement, metric, value, unit, page, source_chunk_id, confidence) trước khi RAG giải thích; lần đầu numeric_match và exact_match đạt 1.0 trên câu bổ sung có đáp án. Thay đổi ở v3: mở rộng phạm vi sang E4-E7 (rerank nhẹ thay cross-encoder offline, rewrite truy vấn, index bảng riêng, contextual chunk); E3 trở thành baseline lọc cứng tái lập được. Thay đổi ở v2: tách bạch retrieval quality và answer quality, bổ sung context precision/recall,
refusal precision/recall, citation precision/recall, period/company/year/version/page accuracy,
unsupported-claim rate và hai heuristic thay thế faithfulness/answer_relevancy.

## 1. Phạm vi và nguyên tắc bất biến

- Split v3: dev 40 câu, test 160 câu, seed 42, khóa tại
  `data/splits/split_meta.json` (sha256 `db325529e701a7ac...`).
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

### 2.2 Citation quality

| Metric | Định nghĩa | Cách chấm |
|---|---|---|
| Citation precision@top1 | top-1 có thực sự hỗ trợ câu trả lời không | top-1 `chunk_id` nằm trong evidence, giữ tên cũ `citation_correctness` để tương thích |
| Citation recall@5 | evidence có lọt vào top-5 trích dẫn không | giống R@5 trên nhóm có evidence |
| Citation complete rate | top-1 trích dẫn đủ 4 trường cho mỗi con số không | đủ `chunk_id, page, company_id, fiscal_year`, chính sách tại `config/answer_policy.yaml` |
| Page accuracy | trang trích dẫn có chứa giá trị hoặc bảng đúng không | `predicted_page` so với `source_page` của gold, chỉ trên câu có `source_page` |

Mỗi con số trong đáp án phải kèm trích dẫn `chunk_id, page, company, year`.
Prompt sinh đáp án bắt buộc: chỉ dùng thông tin từ các chunk được cấp,
không suy diễn ngoài context, thiếu dữ liệu thì trả đúng nguyên văn
`Không đủ bằng chứng trong corpus để trả lời.` Nếu nhiều giá trị mâu thuẫn
cho cùng chỉ tiêu thì gán `ambiguous` và nêu rõ cần làm rõ kỳ, công ty hay
đơn vị nào. Xem `src/retrieval/answer_policy.py` (`GENERATION_PROMPT`,
`build_evidence_block`, `build_generation_prompt`).

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

### 2.4 Refusal và trạng thái trả lời (câu thiếu bằng chứng)

Mỗi câu trả lời có một trạng thái đo được:

| Trạng thái | Định nghĩa | Cách gán |
|---|---|---|
| answered | có bằng chứng đủ và rõ | đáp án không trống, không từ chối, không mâu thuẫn, top-1 khớp công ty/năm được hỏi và có số trang |
| partial_answer | có bằng chứng nhưng thiếu một phần thông tin | top-1 lệch công ty/năm được hỏi, hoặc thiếu số trang |
| refused | không tìm thấy bằng chứng đủ tin cậy | khớp câu từ chối chuẩn, hoặc đáp án trống, hoặc không có chunk |
| ambiguous | có nhiều giá trị mâu thuẫn, cần làm rõ kỳ/công ty/đơn vị | câu hỏi đơn (1 công ty, 1 năm) nhưng top-1 lệch khỏi thực thể được hỏi trong khi top-5 chứa cả hai |

| Metric | Định nghĩa | Cách chấm |
|---|---|---|
| Refusal precision | hệ từ chối có đúng chỗ không, không từ chối sai khi có bằng chứng | `từ chối đúng / tổng số câu hệ từ chối` |
| Refusal recall | hệ có bỏ sót câu thiếu bằng chứng không | `từ chối đúng / 16 câu needs_more_evidence`, giữ tên cũ `refusal_rate` để tương thích |
| False-answer rate | tỷ lệ câu hệ trả lời sai hoặc né tránh sai | `1 - (numeric đúng + từ chối đúng) / tổng số câu`, càng thấp càng tốt |
| Nhãn refusal | đúng/sai từ chối cho từng câu | `true_refusal, missed_refusal, false_refusal, true_answer` trong `evaluation/refusal_labels/refusal_labels_E{0..8}.csv` |
| Refusal den | mẫu số của nhóm thiếu bằng chứng | 16 ở test, 0 ở dev (split v3) |

Đánh giá retrieval và answer riêng, không chỉ chấm câu trả lời cuối.
Trường hợp retrieval đúng nhưng answer sai thể hiện qua R@k cao kèm numeric
match thấp, phải nêu trong `error_analysis.md`.

## 3. Xử lý câu không đủ bằng chứng

- 16 câu `needs_more_evidence=true` đều nằm ở test.
- Hệ thống phải trả lời đúng nguyên văn
  `Không đủ bằng chứng trong corpus để trả lời.`
- Mọi câu trả lời bằng số cho 16 câu này đều tính là sai, kể cả khi số trùng
  với một ô bảng nào đó trong corpus.
- Retrieval cho 12 câu này không tính R@k vào điểm chính, chỉ báo cáo riêng.

## 4. Chống rò rỉ

- Tách theo câu hỏi, không tách theo chunk. Mỗi chunk thuộc đúng một trang,
  không chia chunk qua hai split.
- Kiểm tra paraphrase gần trùng bằng chuẩn hóa chữ thường toàn câu hỏi trước
  khi chia (`src/build_gold.py` cho v1, `src/build_expanded_gold_v2.py` cho v2, `src/build_expanded_gold_v3.py` cho v3):
  200 câu không trùng `question_id`, câu hỏi mới không trùng câu cũ.
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
