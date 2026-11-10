# Hướng dẫn gắn nhãn gold cho bộ câu hỏi RAG báo cáo tài chính (Đề tài 6)

Phiên bản: v0.2.

Tài liệu này là quy tắc duy nhất để xác định đáp án. Mọi nhãn gold đều phải
tuân thủ, mọi bất đồng đều phân xử theo thứ tự ưu tiên trong Mục 7.
Thay đổi ở v0.2: thêm Mục 8 về mở rộng có kiểm soát lên 100-150 câu với 5 tầng,
schema giàu (expected_answer, supporting_chunk_ids, evidence_type, answer_type,
difficulty, value, unit chuẩn hóa), và bảng quy đổi đơn vị chống nhầm tỷ/triệu.

## 1. Phạm vi và định mức

- Bộ gold tối thiểu 50 câu trên corpus thực dùng: HPG, HSG, NKG, MSR, giai đoạn
2020-2024, hai bản hợp nhất và riêng. Định mức v1 giữ nguyên để đối chiếu:
chia 10 dev + 40 test, trong test ít nhất 08 câu không đủ bằng chứng,
ít nhất 10 câu liên quan số liệu hoặc đơn vị, gồm 35 câu ViFinQA
(khớp corpus bằng `src/filter_questions.py`) và 15 câu tự tạo bằng
`src/build_supplement_gold.py` (7 trả lời được, 8 thiếu bằng chứng).
- Bản v3 hiện hành mở rộng lên 200 câu: giữ nguyên 50 câu v1 và 127 câu v2,
thêm 73 câu tổng hợp sạch `source=table-clean` (đợt B)
nâng tổng table-clean lên 150 câu (55 T1, 44 T2, 43 T3, 8 T5), chia 40 dev + 160 test,
16 câu thiếu bằng chứng đều nằm ở test.

## 2. Quy tắc xác định đáp án

1. Đáp án số chỉ lấy từ đúng ô bảng trong đúng báo cáo, đúng năm, đúng bản

   (hợp nhất hoặc riêng). Không dùng số ở cột năm khác, không dùng số của
    doanh nghiệp khác, không dùng số ở bản báo cáo khác.
2. Phạm vi "công ty mẹ" chỉ dùng bản `separate`. Phạm vi không ghi rõ hoặc chỉ

   tiêu hợp nhất dùng bản `consolidated`.
3. Chuỗi bằng chứng (`quote`) phải là nguyên văn dòng trong chunk, đủ để người

   thứ hai tìm lại đúng trang và đúng bảng.
4. Mỗi câu trả lời được phải có ít nhất một dòng bằng chứng chứa số đáp án và

   một dòng chứa đơn vị hoặc header năm.

## 3. Đơn vị

1. Đơn vị của câu hỏi ViFinQA gốc giữ nguyên như trong câu hỏi

   (triệu đồng, tỷ đồng, nghìn tỷ đồng, trăm tỷ đồng, %, lần).
2. Đơn vị trong báo cáo: `VND` nghĩa là đồng tuyệt đối, `Nghìn VND` nghĩa là

   nghìn đồng. Luôn quy đổi về đơn vị câu hỏi trước khi ghi `value`.
3. Không bao giờ đoán đơn vị của chunk để trống. Nếu không xác định được đơn vị

   trong trang, ghi chú vào `review_log.csv` và chuyển câu sang diện kiểm chứng.

## 4. Số và làm tròn

1. Số có dấu chấm phân cách nghìn trong OCR (ví dụ `91.279.041.771.826`) giữ

   nguyên khi trích, bỏ dấu chấm khi tính toán.
2. Số thập phân dấu phẩy (ví dụ `3,2`) chuyển thành `3.2`. Không nhân với 100.
3. Số âm trong ngoặc (ví dụ `(983.237)`) chuyển thành `-983237`.
4. Ký hiệu `%` giữ nguyên kèm dấu phần trăm.
5. Kết quả quy đổi đơn vị và tỷ lệ phần trăm làm tròn 4 chữ số thập phân.
6. Lãi cơ bản trên cổ phiếu ghi theo quy ước dấu chấm phân cách nghìn:

   ô `1.434` nghĩa là 1434 đồng.

## 5. Câu không đủ bằng chứng

1. Chỉ gắn `needs_more_evidence = true` khi chủ đề câu hỏi vắng mặt hoàn toàn

   trong toàn bộ corpus. Kiểm chứng bằng tìm kiếm toàn văn trong `chunks.jsonl`,
    không kiểm chứng bằng trí nhớ.
2. `gold_answer` của câu thiếu bằng chứng luôn là

   `Không đủ bằng chứng trong corpus để trả lời.`
3. Cấm dùng kiến thức ngoài corpus để trả lời câu thiếu bằng chứng.
4. Lý do thiếu bằng chứng ghi vào `unanswerable_reason`, nêu rõ chủ đề nào vắng

   mặt và đã kiểm tra bằng cụm từ nào.

## 6. Câu cần phép tính và câu đa doanh nghiệp

1. Câu cần phép tính phải ghi đầy đủ `computation`: công thức, số đầu vào và

   kết quả từng bước.
2. Câu đa doanh nghiệp phải có bằng chứng cho từng doanh nghiệp được nhắc tới,

   hoặc ghi rõ doanh nghiệp nào thiếu bằng chứng và xử lý theo Mục 5.
3. Câu so sánh nhiều năm phải lấy số cùng chỉ tiêu, cùng bản báo cáo cho mọi năm.

## 7. Xử lý bất đồng

1. Hậu kiểm chéo tối thiểu 20% số câu bởi người thứ hai.
2. Bất đồng về số hoặc đơn vị: người kiểm chứng tra lại chunk gốc, bên nào sai

   chuỗi bằng chứng thì sửa theo chunk.
3. Bất đồng về quy tắc (ví dụ đơn vị mơ hồ): ghi vào `review_log.csv`, quyết

   định cuối cùng thuộc về người ban hành guideline, và cập nhật guideline lên
    phiên bản mới thay vì sửa lẻ từng nhãn.
4. Không dùng nhãn do LLM tự tạo làm gold nếu chưa có người kiểm chứng.

   Nếu có LLM hỗ trợ, ghi rõ trong `review_log.csv` và nhật ký sử dụng AI.

## 8. Mở rộng có kiểm soát lên 100-150 câu (v0.2)

### 8.1 Năm tầng và quota cho mốc 120 câu

| Tầng | Nhóm câu hỏi | Tỷ lệ | Quota ở 120 câu | Mục đích |
|---|---|---|---|---|
| T1 | Tra cứu một giá trị | 35% | 42 | Đo khả năng tìm đúng số liệu |
| T2 | So sánh theo thời gian | 20% | 24 | Đo hiểu đúng kỳ và biến động |
| T3 | Tính toán đơn giản | 20% | 24 | Đo suy luận số liệu từ bảng |
| T4 | So sánh giữa công ty | 15% | 18 | Đo khả năng tổng hợp nhiều tài liệu |
| T5 | Không đáp án / ngoài corpus | 10% | 12 | Đo refusal |

Hiện trạng bộ 50 câu: T1=13, T2=2, T3=2, T4=25, T5=8. T4 đang thừa vì
35 câu ViFinQA khớp corpus có 25 câu đa công ty. Khi mở rộng, ưu tiên thêm T1/T2/T3
và T5, giữ T4 không vượt 18 câu ở mốc 120, còn lại chuyển sang dự trữ.

### 8.2 Quy tắc xếp tầng

1. T5 trước: `needs_more_evidence=true` thì luôn là T5, không xét tầng khác.
2. T4: câu nhắc từ 2 công ty trở lên trong corpus (HPG, HSG, NKG, MSR).
3. T2: một công ty nhưng nhắc từ 2 năm trở lên (ví dụ 2022-2024, 2020|2024).
4. T3: một công ty, một kỳ, nhưng `answer_type= onclick computation` hoặc câu có

   từ tính, trung bình, chênh lệch, biên, tỷ lệ suy ra từ hai ô bảng.
5. T1: còn lại, một công ty, một kỳ, tra một ô bảng.

### 8.3 Schema giàu cho mỗi gold

Mỗi gold mở rộng phải có đủ:

- `expected_answer`: chuỗi đáp án hiển thị, ví dụ `39.2719 nghìn tỷ đồng`.
- `supporting_chunk_ids`: danh sách `chunk_id` chứng minh, ví dụ
`["HSG_2024_consolidated#p009"]`.
- `evidence_type`: `single_cell`, `multi_cell_same_page`, `multi_page`,
`computed_from_table`, `no_evidence`.
- `answer_type`: `numeric`, `computation`, `unanswerable`, `text`.
- `difficulty`: `easy`, `medium`, `hard` theo số bước tra cứu và tính toán.
- `value`: số đã chuẩn hóa về đơn vị câu hỏi, làm tròn 4 chữ số thập phân.
- `unit`: đơn vị chuẩn của đáp án, một trong
`đồng, nghìn đồng, triệu đồng, tỷ đồng, nghìn tỷ đồng, trăm tỷ đồng, %, lần`.

Trường cũ vẫn giữ để tương thích: `gold_answer=expected_answer`,
`evidence[].chunk_id=supporting_chunk_ids`, `value`, `unit`, `computation`.

### 8.4 Bảng quy đổi đơn vị chống nhầm tỷ và triệu

| Đơn vị trong chunk | Hệ số về đồng | Quy đổi về đơn vị câu hỏi |
|---|---|---|
| `VND` | 1 | chia cho hệ số đơn vị đích |
| `Nghìn VND` | 1000 | nhân 1000 rồi chia cho hệ số đơn vị đích |
| `đồng` | 1 | giữ nguyên |
| `triệu đồng` | 1e6 | `value_vnd / 1e6` |
| `tỷ đồng` | 1e9 | `value_vnd / 1e9` |
| `nghìn tỷ đồng` | 1e12 | `value_vnd / 1e12` |
| `trăm tỷ đồng` | 1e11 | `value_vnd / 1e11` |

Chấm tự động chỉ so `value` sau quy đổi, không so chuỗi thô, nên đáp án
`39.2719 nghìn tỷ đồng` và `39271.8937 tỷ đồng` được coi là một nếu cùng
`value_vnd=39271893738448`. Ghi cả `value_vnd` vào trường `computation`
hoặc ghi chú để người chấm lại kiểm được.

### 8.5 Quy trình thêm câu mới

1. Lấy ứng viên từ 1.012 câu ViFinQA còn lại và từ `table_records.jsonl`

   theo quota tầng còn thiếu.
2. Mỗi câu mới phải gán tầng đề xuất theo Mục 8.1,
   kiểm tra trùng câu hỏi, kiểm tra phủ công ty và năm.
3. Người gắn nhãn điền đủ schema Mục 8.3, trích đúng ô bảng, đúng năm, đúng bản.
4. Hậu kiểm chéo tối thiểu 20%, bất đồng xử lý theo Mục 7.
5. Đóng băng split mới bằng seed cố định, giữ 16 câu thiếu bằng chứng ở test.
