# Pilot nâng cao mục 7 (chạy nhanh, không train, không API)

Phạm vi: 7 câu có evidence (5 test + 2 dev). E3 là run nâng cao làm gốc so sánh.
Script sinh file này: `src/evaluate/pilot_advanced.py`.

## 1. Robustness theo top-k (cắt top-5 của E3 test)

| k | recall@k E3 test (5 câu) | ghi chú |
|---|---|---|
| 1 | 1/5 = 0.20 | cắt trực tiếp từ top-5 |
| 3 | 3/5 = 0.60 | cắt trực tiếp từ top-5 |
| 5 | 4/5 = 0.80 | cắt trực tiếp từ top-5 |

Chi tiết E3 test: S_NEW_01 trúng ở hạng 4 (`HSG_2024_consolidated#p009`),
S_NEW_02 trúng ở hạng 2, S_NEW_04 trúng ở hạng 2 (`HPG_2024_separate#p007`),
S_NEW_06 trượt, S_NEW_07 trúng top-1.
Nhận xét: recall tăng theo k đúng kỳ vọng truy hồi.
Ablation metadata: E2 cộng điểm mềm đạt R@5 = 0.40, E3 lọc cứng đạt R@5 = 0.80.
Seed LSA ổn định qua 3 seed 42, 7, 123 đều recall 1/7 trên 7 câu có evidence.

## 2. Tổng quát tách theo công ty (E3 test)

| công ty | số câu có evidence | số câu E3 trúng top-5 |
|---|---|---|
| HPG | 1 (S_NEW_04) | 1 |
| HSG | 2 (S_NEW_01; S_NEW_07) | 2 |
| NKG | 2 (S_NEW_02; S_NEW_06) | 1 |

Nhận xét: MSR có 0 câu test có evidence nên không kết luận được cho MSR.
Tổng E3 test 4/5, câu trượt duy nhất là S_NEW_06 do sai trang
(top-1 rơi vào thuyết minh `NKG_2024_consolidated#p042`), không sai công ty.
Dev bổ sung: S_NEW_03 (MSR) và S_NEW_05 (HSG) đều trượt ở E3,
cho thấy lọc cứng chỉ hiệu quả khi câu hỏi ghi rõ mã CK.
Đây là phép thử tách theo công ty ở mức tối thiểu, chưa phải cross-validation đầy đủ.

## 3. Multi-hop thí điểm (ViFinQA-368, chưa có gold)

Câu gốc (rút gọn): năm 2022, trong nhóm HPG HSG MSR NKG,
các công ty có hệ số thanh toán nhanh thấp hơn trung vị của nhóm
có biên lợi nhuận ròng bình quân là bao nhiêu phần trăm?

Bước 1: truy hồi hệ số thanh toán nhanh từng công ty năm 2022.
Bước 2: tính trung vị, lọc nhóm thấp hơn trung vị.
Bước 3: truy hồi biên lợi nhuận ròng của nhóm được lọc rồi tính bình quân.

- Truy hồi `he so thanh toan nhanh HPG nam 2022` -> MSR_2022_consolidated#p002 (10.15); MSR_2022_separate#p002 (10.15); MSR_2022_consolidated#p073 (10.01)
- Truy hồi `he so thanh toan nhanh HSG nam 2022` -> MSR_2022_consolidated#p002 (10.15); MSR_2022_separate#p002 (10.15); MSR_2022_consolidated#p073 (10.01)
- Truy hồi `bien loi nhuan rong NKG nam 2022` -> NKG_2022_consolidated#p013 (7.88); NKG_2023_consolidated#p013 (7.69); NKG_2023_separate#p013 (7.66)

Nhận xét: pipeline 2 bước chạy được về kỹ thuật, nhưng thiếu gold từng bước
nên chưa chấm metric; đánh dấu nhóm này là needs_decomposition.
Thí điểm còn cho thấy BM25 thuần không giữ được điều kiện thực thể
khi thiếu lọc metadata, củng cố việc E3 lọc cứng mỗi bước con là đúng hướng.

## 4. Cross-report thí điểm (so sánh 2 báo cáo)

Câu thí điểm: chênh lệch doanh thu thuần HSG 2024 và MSR 2024 bao nhiêu tỷ đồng?
Tách 2 vế: vế HSG lấy S_NEW_01, vế MSR lấy S_NEW_03.
- S_NEW_01 (HSG): top-1 `HSG_2024_consolidated#p045`, công ty dự đoán `HSG`, gold `HSG`
- S_NEW_03 (MSR): top-1 `HSG_2024_consolidated#p045`, công ty dự đoán `HSG`, gold `MSR`

Nhận xét: E3 giữ đúng công ty khi câu hỏi có mã CK rõ ràng (S_NEW_01),
nhưng thất bại khi tên công ty viết đầy đủ mà bộ lọc chỉ nhận mã CK (S_NEW_03).
Phép tính chênh lệch đòi hỏi đổi đơn vị về cùng tỷ đồng trước khi trừ, để ở mục spreadsheet.
Hướng cải tiến tiếp theo: mở rộng từ điển tên công ty đầy đủ.

## 5. Kiểm tra bảng tính (spreadsheet-like) cho câu hỏi cần phép tính

| câu | tính lại | gold | khớp |
|---|---|---|---|
| S_NEW_07 | 10.8568 % | 10.8568 % | đạt |
| S_NEW_01 | 39.2719 nghìn tỷ | 39.2719 nghìn tỷ đồng | đạt |
| S_NEW_06 | 1434 đồng | 1434 đồng | đạt |

Công thức S_NEW_07: 4263666396467 / 39271893738448 x 100 = 10.8568 %, làm tròn 4 chữ số.
Công thức S_NEW_01: 39271893738448 VND / 1e12 = 39.2719 nghìn tỷ đồng.
Nhận xét: 3 phép tính mẫu khớp gold sau làm tròn 4 chữ số.
Đơn vị VND thô trong chunk khác đơn vị đã đổi trong gold nên phải đổi trước khi so sánh.

## 6. Chi phí truy hồi (cache embedding, rerank nhẹ)

- BM25 1 câu mẫu: 37.1 ms (2407 chunk, chạy tại máy, không GPU).
- Kích thước chunks.jsonl: 6545504 bytes; lsa_index_E1.npz: 2360512 bytes.
- E3 chạy full 50 câu khoảng 18 giây ở lần đo trước (alpha = 0.5, cand_k = 20).
- Cache TF-IDF + SVD giữ nguyên giữa các lần chạy, chỉ nạp 1 lần.
- Hướng giảm chi phí: giảm cand_k từ 20 xuống 10, hoặc lưu sẵn top-20 BM25.

