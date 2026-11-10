# Giao thức đánh giá và chống rò rỉ (Mục 2.3, Mục 5.4)

Phiên bản: v1. Ngày ban hành: 2026-11-10. Áp dụng cho toàn bộ E0/E1/E2.

## 1. Phạm vi và nguyên tắc bất biến

- Split: dev 10 câu, test 40 câu, seed 42, khóa tại
  `data/splits/split_meta.json` (sha256 `43276e350a9aa755...`).
- Chỉ chọn tham số, prompt, mô hình bằng **dev**. Chỉ dùng **test** để công bố
  kết quả cuối. Ai nhìn test để tuning phải khai báo và thiết kế lại tập test
  độc lập.
- Cả 3 cấu hình E0/E1/E2 dùng cùng test và cùng script chấm
  (`src/evaluate/evaluate.py`, chưa viết ở mốc này).

## 2. Định nghĩa metric (Đề tài 6, Mục 4.6.5)

| Metric | Ký hiệu | Định nghĩa | Cách chấm |
|---|---|---|---|
| Recall@k | R@k, k cố định và công bố | tỷ lệ câu có ít nhất một chunk bằng chứng gold lọt vào top-k | so `chunk_id` dự đoán với `evidence[].chunk_id` của gold |
| MRR@k | MRR@k | trung bình nghịch đảo hạng của bằng chứng đúng đầu tiên, 0 nếu ngoài top-k | cùng tập relevance với R@k |
| Numeric match | - | đáp án số đúng sau chuẩn hóa số và đơn vị | `normalize_number` + quy đổi đơn vị, làm tròn 4 chữ số thập phân; `%` giữ dấu phần trăm |
| Citation correctness | - | trích dẫn đúng báo cáo, năm, trang, bảng | `report_id`, `fiscal_year`, `source_page`, `chunk_id` khớp gold |
| Tỷ lệ từ chối đúng | - | tỷ lệ câu thiếu bằng chứng được trả lời đúng câu từ chối | chỉ tính trên 8 câu `needs_more_evidence=true`; đáp án đúng phải là `Không đủ bằng chứng trong corpus để trả lời.` |

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
