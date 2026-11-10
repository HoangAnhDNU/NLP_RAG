# Pilot nâng cao mục 7 (chạy nhanh, không train, không API)

Phạm vi: 149 câu có evidence (118 test + 31 dev). E3 là run nâng cao làm gốc so sánh.
Script sinh file này: `src/evaluate/pilot_advanced.py`.

## 1. Robustness theo top-k (cắt top-5 của E3 test)

| k | recall@k E3 test (118 câu) | ghi chú |
|---|---|---|
| 1 | 6/118 = 0.05 | cắt trực tiếp từ top-5 |
| 3 | 15/118 = 0.13 | cắt trực tiếp từ top-5 |
| 5 | 24/118 = 0.20 | cắt trực tiếp từ top-5 |

Nhận xét: recall tăng theo k đúng kỳ vọng truy hồi.

## 2. Tổng quát tách theo công ty (E3 test)

| công ty | số câu có evidence | số câu E3 trúng top-5 |
|---|---|---|
| HPG | 20 (S_NEW_04; CLEAN-T1-HPG-2020-01; CLEAN-T1-HPG-2020-12; CLEAN-T1-HPG-2020-16; CLEAN-T2-HPG-2020-2021-01; CLEAN-T2-HPG-2021-2022-05; CLEAN-T2-HPG-2022-2023-09; CLEAN-T2-HPG-2020-2021-13; CLEAN-T2-HPG-2021-2022-17; CLEAN-T3-HPG-2020-2021-01; CLEAN-T3-HPG-2021-2022-05; CLEAN-T3-HPG-2022-2023-09; CLEAN-T3-HPG-2023-2024-13; CLEAN-T1-HPG-2021-B01; CLEAN-T1-HPG-2020-B05; CLEAN-T1-HPG-2020-B10; CLEAN-T1-HPG-2020-B14; CLEAN-T1-HPG-2021-B18; CLEAN-T1-HPG-2021-B19; CLEAN-T1-HPG-2021-B23) | 7 |
| HSG | 38 (S_NEW_01; S_NEW_05; S_NEW_07; CLEAN-T1-HSG-2020-02; CLEAN-T1-HSG-2024-07; CLEAN-T1-HSG-2020-09; CLEAN-T1-HSG-2020-13; CLEAN-T1-HSG-2020-17; CLEAN-T1-HSG-2020-23; CLEAN-T1-HSG-2020-27; CLEAN-T2-HSG-2020-2021-10; CLEAN-T2-HSG-2021-2022-14; CLEAN-T2-HSG-2023-2024-22; CLEAN-T3-HSG-2020-2021-02; CLEAN-T3-HSG-2020-2021-06; CLEAN-T3-HSG-2021-2022-10; CLEAN-T3-HSG-2022-2023-14; CLEAN-T3-HSG-2020-2021-20; CLEAN-T1-HSG-2020-B02; CLEAN-T1-HSG-2020-B07; CLEAN-T1-HSG-2020-B11; CLEAN-T1-HSG-2020-B20; CLEAN-T2-HSG-2021-2022-B01; CLEAN-T2-HSG-2023-2024-B07; CLEAN-T2-HSG-2020-2021-B10; CLEAN-T2-HSG-2021-2022-B13; CLEAN-T2-HSG-2022-2023-B16; CLEAN-T2-HSG-2020-2021-B20; CLEAN-T2-HSG-2021-2022-B22; CLEAN-T3-HSG-2022-2023-B01; CLEAN-T3-HSG-2023-2024-B03; CLEAN-T3-HSG-2020-2021-B05; CLEAN-T3-HSG-2023-2024-B11; CLEAN-T3-HSG-2020-2021-B13; CLEAN-T3-HSG-2021-2022-B15; CLEAN-T3-HSG-2022-2023-B17; CLEAN-T3-HSG-2023-2024-B19; CLEAN-T3-HSG-2020-2021-B21) | 4 |
| MSR | 26 (CLEAN-T1-MSR-2020-03; CLEAN-T1-MSR-2020-10; CLEAN-T1-MSR-2020-14; CLEAN-T1-MSR-2020-19; CLEAN-T1-MSR-2022-28; CLEAN-T1-MSR-2020-29; CLEAN-T2-MSR-2020-2021-03; CLEAN-T2-MSR-2021-2022-07; CLEAN-T2-MSR-2022-2023-11; CLEAN-T3-MSR-2021-2022-03; CLEAN-T3-MSR-2022-2023-07; CLEAN-T3-MSR-2023-2024-11; CLEAN-T3-MSR-2020-2021-15; CLEAN-T3-MSR-2021-2022-18; CLEAN-T3-MSR-2022-2023-21; CLEAN-T1-MSR-2020-B03; CLEAN-T1-MSR-2020-B08; CLEAN-T1-MSR-2020-B12; CLEAN-T1-MSR-2020-B16; CLEAN-T1-MSR-2020-B21; CLEAN-T1-MSR-2020-B25; CLEAN-T2-MSR-2023-2024-B02; CLEAN-T2-MSR-2020-2021-B05; CLEAN-T2-MSR-2021-2022-B08; CLEAN-T2-MSR-2022-2023-B11; CLEAN-T2-MSR-2023-2024-B14) | 8 |
| NKG | 34 (S_NEW_02; S_NEW_06; CLEAN-T1-NKG-2021-04; CLEAN-T1-NKG-2020-06; CLEAN-T1-NKG-2020-11; CLEAN-T1-NKG-2020-15; CLEAN-T1-NKG-2020-18; CLEAN-T1-NKG-2020-21; CLEAN-T1-NKG-2020-25; CLEAN-T2-NKG-2023-2024-08; CLEAN-T2-NKG-2021-2022-12; CLEAN-T2-NKG-2022-2023-16; CLEAN-T2-NKG-2023-2024-20; CLEAN-T3-NKG-2021-2022-04; CLEAN-T3-NKG-2022-2023-08; CLEAN-T3-NKG-2023-2024-12; CLEAN-T3-NKG-2021-2022-16; CLEAN-T3-NKG-2022-2023-19; CLEAN-T1-NKG-2020-B04; CLEAN-T1-NKG-2020-B09; CLEAN-T1-NKG-2020-B13; CLEAN-T1-NKG-2020-B17; CLEAN-T1-NKG-2020-B22; CLEAN-T2-NKG-2023-2024-B09; CLEAN-T2-NKG-2021-2022-B12; CLEAN-T2-NKG-2022-2023-B15; CLEAN-T2-NKG-2021-2022-B19; CLEAN-T2-NKG-2022-2023-B21; CLEAN-T3-NKG-2023-2024-B02; CLEAN-T3-NKG-2020-2021-B04; CLEAN-T3-NKG-2021-2022-B06; CLEAN-T3-NKG-2023-2024-B10; CLEAN-T3-NKG-2021-2022-B14; CLEAN-T3-NKG-2020-2021-B20) | 5 |

Nhận xét: E3 lọc cứng giữ đúng công ty khi câu hỏi ghi rõ mã CK;
chi tiết từng công ty xem bảng trên, tổng hợp đầy đủ tại `evaluation/comparison_E0_E1_E2.md`.
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

- BM25 1 câu mẫu: 37.0 ms (2407 chunk, chạy tại máy, không GPU).
- Kích thước chunks.jsonl: 6545504 bytes; lsa_index_E1.npz: 2360512 bytes.
- E3 chạy full 200 câu khoảng 70 giây ở lần đo trước (alpha = 0.5, cand_k = 20).
- Cache TF-IDF + SVD giữ nguyên giữa các lần chạy, chỉ nạp 1 lần.
- Hướng giảm chi phí: giảm cand_k từ 20 xuống 10, hoặc lưu sẵn top-20 BM25.

