# Giao thức đánh giá và chống rò rỉ (Mục 2.3, Mục 5.4)

Phiên bản: v9. Ngày cập nhật: 2026-11-15. Áp dụng cho toàn bộ E0-E8.
- **Thay đổi ở v9 (split v4)**: giải quyết toàn bộ 35 câu `vifinqa` kèm quote nguyên văn từ `chunks.jsonl` (`0` `pending-answer`), bổ sung 4 câu từ chối ngoài corpus `DEV-REF-01..04` riêng cho `dev` (`dev` 40 -> 44 câu, `refusal_den_dev = 4`), và giữ nguyên hoàn toàn 160 câu `test` từ `v3` (`evidence_den = 144`, `refusal_den = 16`, không rò rỉ `test`).
  Đồng thời nâng cấp pipeline đánh giá & suy luận:
  1. Các script suy luận `src/infer/e0_bm25.py`..`e8_table_lookup.py` lưu **top-10** `predicted_chunk_ids` (thay vì cắt ở top-5), giúp `Recall@10` và `MRR@10` đo thực chất ngoài phạm vi top-5.
  2. `src/evaluate/evaluate.py` siết `numbers_in_context()` theo từng chunk độc lập qua `CHUNK_SEP` (chặn khớp chéo chunk), chỉ cho phép quy đổi đơn vị trong phạm vi `1e3..1e12` với dung sai tương đối `1e-3`, loại bỏ tiêu đề năm (`2020..2025`), và bổ sung `parse_pipe_set()` cho `company_accuracy`, `year_accuracy`, `period_accuracy` dạng tập hợp `|` (như `2020|2021`).
  3. `src/retrieval/answer_policy.py` kiểm tra bao phủ đa thực thể trên `top_chunks[:5]` (`asked_tickers <= chunk_companies` khi hỏi `>= 2` mã và `asked_years <= chunk_years` khi hỏi `>= 2` năm), gán `partial_answer` (`missing_multi_entity_evidence`) khi thiếu vế so sánh.
- **Lịch sử các bản trước**: v8 mở rộng gold lên 200 câu (`table-clean` 150 câu: 55 T1, 44 T2, 43 T3, 8 T5); v6 tách `evaluation/` thành `test_predictions/`, `dev_predictions/`, `refusal_labels/`; v5 đưa refusal thành 4 trạng thái (`answered`, `partial_answer`, `refused`, `ambiguous`) kèm `false_answer_rate`, `citation_complete_rate` và `refusal_labels_E*.csv`; v4 thêm `E8` lookup `table_records.jsonl`; v3 thêm E4–E7 và giữ E3 lọc cứng; v2 tách retrieval/answer và thêm các metric heuristic RAGAS.

## 1. Phạm vi và nguyên tắc bất biến

- Split `v4`: `dev` **44** câu (40 câu có evidence + 4 câu `dev-refusal`), `test` **160** câu (144 câu có evidence + 16 câu `unanswerable` giữ nguyên hoàn toàn từ `v3`), `seed = 42`, khóa tại `data/splits/split_meta.json` và bản sao `evaluation/split_freeze.json` (`sha256`: `0012ebccd6712b44cdd1faf18f020c547c82973db09d37ab2b9e96b0a94a34b4`).
- Chỉ chọn tham số, prompt, mô hình bằng **dev**. Chỉ dùng **test** để công bố kết quả cuối. Mọi thay đổi trên tập `test` đều bị cấm sau khi đóng băng.
- Cả 9 cấu hình E0-E8 dùng cùng tập test 160 câu và cùng script chấm (`src/evaluate/evaluate.py`).

## 2. Định nghĩa metric (Đề tài 6, Mục 4.6.5, RAGAS)

### 2.1 Retrieval quality (trên tập `evidence_den`: 144 test / 40 dev)

| Metric | Ký hiệu | Định nghĩa | Cách chấm |
|---|---|---|---|
| Recall@k | R@3, R@5, R@10 | tỷ lệ câu có ít nhất một chunk bằng chứng gold lọt vào top-k | so `predicted_chunk_ids[:k]` (lưu đủ top-10) với `evidence[].chunk_id` của gold |
| MRR@k | MRR@3, MRR@5, MRR@10 | trung bình nghịch đảo hạng của bằng chứng đúng đầu tiên trong top-k, 0 nếu ngoài top-k | tính thực chất trên `[:3]`, `[:5]`, `[:10]` |
| Context precision@5 | ctxP@5 | tỷ lệ chunk trong top-5 thực sự là evidence | `|top-5 giao evidence| / 5` |
| Context recall@5 | ctxR@5 | tỷ lệ evidence được phủ bởi top-5 | `|top-5 giao evidence| / |evidence|` |

### 2.2 Citation quality

| Metric | Định nghĩa | Cách chấm |
|---|---|---|
| Citation precision@top1 | top-1 có thực sự hỗ trợ câu trả lời không | top-1 `chunk_id` nằm trong evidence (`citation_correctness` giữ lại để tương thích) |
| Citation recall@5 | evidence có lọt vào top-5 trích dẫn không | giống R@5 trên nhóm có evidence |
| Citation complete rate | top-1 trích dẫn đủ 4 trường cho mỗi con số không | đủ `chunk_id, page, company_id, fiscal_year`, chính sách tại `config/answer_policy.yaml` |
| Page accuracy | trang trích dẫn có chứa giá trị hoặc bảng đúng không | `predicted_page` so với `source_page` của gold, chỉ trên câu có `source_page` |

Mỗi con số trong đáp án phải kèm trích dẫn `chunk_id, page, company, year`.
Xem `src/retrieval/answer_policy.py` (`GENERATION_PROMPT`, `build_evidence_block`, `build_generation_prompt`, `decide_status`).

### 2.3 Answer quality (số và nghiệp vụ tài chính)

| Metric | Định nghĩa | Cách chấm |
|---|---|---|
| Numeric match | đáp án số đúng sau chuẩn hóa đơn vị, dấu âm, dấu phẩy/thập phân | trích số trong `predicted_answer`, chuẩn hóa `(983)` thành âm, `3,2` thành `3.2`, giữ `%`, so với `value` của gold với dung sai `max(1e-4, |gv|*1e-6)` |
| Exact match | khớp nguyên văn sau chuẩn hóa chuỗi | chữ thường, gọn khoảng trắng |
| Period accuracy | đúng đồng thời công ty, năm và bản báo cáo | so khớp tập hợp chuẩn hóa `parse_pipe_set()` (`HPG\|HSG`, `2020\|2021`) cho `company_accuracy`, `year_accuracy` và `version_accuracy` |
| Company/year/version accuracy | từng thành phần của period | chấm riêng để phân định lỗi công ty, năm hay bản hợp nhất/riêng |
| Unsupported-claim rate | tỷ lệ câu trả lời có ít nhất một khẳng định số không xác minh được trong context | kiểm tra độc lập trên từng chunk qua `numbers_in_context()` (tách chunk qua `CHUNK_SEP`, quy đổi đơn vị `1e3..1e12` có chặn trên `1e-3` rel tol, tách riêng tiêu đề năm `2020..2025`, cộng/trừ/chia cơ bản trong cùng chunk) |
| Faithfulness heuristic | thay thế minh bạch cho faithfulness của RAGAS | `1 - unsupported-claim rate` trên câu có dự đoán số hợp lệ |
| Answer relevancy heuristic | thay thế minh bạch cho answer relevancy của RAGAS | `(numeric đúng + từ chối đúng) / tổng số câu` |

Faithfulness đo tính nhất quán của câu trả lời với context, còn answer relevancy đo mức độ đáp ứng câu hỏi; cả hai đều tính offline tái lập 100% từ prediction CSV và `chunks.jsonl`.

### 2.4 Refusal và trạng thái trả lời (câu thiếu bằng chứng)

Mỗi câu trả lời có một trạng thái đo được qua `decide_status()`:

| Trạng thái | Định nghĩa | Cách gán |
|---|---|---|
| `answered` | có bằng chứng đủ và rõ | đáp án không trống, không từ chối, không mâu thuẫn, top-5 phủ đủ `asked_tickers` và `asked_years`, top-1 khớp thực thể và có số trang |
| `partial_answer` | có bằng chứng nhưng thiếu một phần thông tin | top-1 lệch công ty/năm được hỏi, thiếu số trang, hoặc thiếu vế đa công ty/đa năm trên `top_chunks[:5]` (`missing_multi_entity_evidence`) |
| `refused` | không tìm thấy bằng chứng đủ tin cậy | khớp câu từ chối chuẩn, hoặc đáp án trống, hoặc không có chunk |
| `ambiguous` | có nhiều giá trị mâu thuẫn, cần làm rõ kỳ/công ty/đơn vị | câu hỏi đơn nhưng top-1 lệch khỏi thực thể được hỏi trong khi top-5 chứa cả hai |

| Metric | Định nghĩa | Cách chấm |
|---|---|---|
| Refusal precision | hệ từ chối có đúng chỗ không | `từ chối đúng / tổng số câu hệ từ chối` |
| Refusal recall | hệ có bỏ sót câu thiếu bằng chứng không | `từ chối đúng / refusal_den` (`refusal_rate` giữ để tương thích) |
| False-answer rate | tỷ lệ câu hệ trả lời sai hoặc né tránh sai | `1 - (numeric đúng + từ chối đúng) / tổng số câu`, càng thấp càng tốt |
| Nhãn refusal | đúng/sai từ chối cho từng câu | `true_refusal, missed_refusal, false_refusal, true_answer` trong `evaluation/refusal_labels/refusal_labels_E{0..8}.csv` |
| Refusal den | mẫu số của nhóm thiếu bằng chứng | **16** ở `test`, **4** ở `dev` (split `v4`) |

## 3. Xử lý câu không đủ bằng chứng

- Có **20** câu `needs_more_evidence=true`: **16** câu ở `test` (giữ nguyên từ v3) và **4** câu `DEV-REF-01..04` ở `dev` (mới ở v4).
- Hệ thống phải trả lời đúng nguyên văn `Không đủ bằng chứng trong corpus để trả lời.`
- Mọi câu trả lời bằng số cho các câu này đều tính là sai (`false_answer`).
- Nhóm thiếu bằng chứng không tính vào `evidence_den` của R@k, được đo riêng qua `refusal_precision`, `refusal_recall` và `false_answer_rate`.

## 4. Chống rò rỉ

- Tách theo câu hỏi, không tách theo chunk. Mỗi chunk thuộc đúng một trang.
- Kiểm tra trùng lặp chuẩn hóa chữ thường trước khi chia qua `build_gold.py` (được bảo vệ bởi cờ `--force-v1` để tránh ghi đè nhầm `qa_gold.jsonl`), `build_expanded_gold_v2.py`, `build_expanded_gold_v3.py`, và `resolve_vifinqa_and_dev_refusal.py`: **204** câu không trùng `question_id` hay nội dung câu hỏi giữa `dev` và `test`.
- Công bố rõ: cùng một báo cáo có thể xuất hiện ở cả dev và test (corpus dùng chung, phân biệt `consolidated` và `separate` qua `report_version`).
- `test` (160 câu từ v3) được khóa tuyệt đối; mọi mở rộng ở `v4` để khắc phục `refusal_den=0` chỉ bổ sung trên `dev` và cập nhật `split_meta.json` + `evaluation/split_freeze.json` kèm checksum SHA-256 mới (`v4`).

## 5. Khẳng định tổng quát

- Nhóm không khẳng định tổng quát sang doanh nghiệp hay năm ngoài corpus (`HPG`, `HSG`, `NKG`, `MSR` giai đoạn `2020-2024`).
- Nếu mở rộng sang doanh nghiệp hoặc năm ngoài corpus ở công việc tiếp theo, phải thử nghiệm tách riêng theo doanh nghiệp/năm và báo cáo tách biệt khỏi tập test chuẩn.
