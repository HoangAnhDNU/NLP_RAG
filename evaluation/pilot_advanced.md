# Pilot nâng cao mục 7 (chạy nhanh, không train, không API)

Phạm vi: 184 câu có evidence (144 test + 40 dev, trên tổng 204 câu split v4: 44 dev / 160 test). E3 là run nâng cao làm gốc so sánh.
Script sinh file này: `src/evaluate/pilot_advanced.py`.

## 1. Robustness theo top-k (E3 test)

| k | recall@k E3 test (144 câu) | ghi chú |
|---|---|---|
| 1 | 8/144 = 0.06 | cắt trực tiếp ở top-1 |
| 3 | 19/144 = 0.13 | cắt trực tiếp ở top-3 |
| 5 | 34/144 = 0.24 | cắt trực tiếp ở top-5 |

Nhận xét: recall tăng theo k đúng kỳ vọng truy hồi.

## 2. Tổng quát tách theo công ty (E3 test)

| công ty | số câu có evidence | số câu E3 trúng top-5 |
|---|---|---|
| HPG | 23 (ViFinQA-97; ViFinQA-400; ViFinQA-450; S_NEW_04; ... (+19)) | 9 (39.1%) |
| HSG | 39 (ViFinQA-311; S_NEW_01; S_NEW_05; S_NEW_07; ... (+35)) | 5 (12.8%) |
| MSR | 28 (ViFinQA-186; ViFinQA-709; CLEAN-T1-MSR-2020-03; CLEAN-T1-MSR-2020-10; ... (+24)) | 9 (32.1%) |
| NKG | 36 (ViFinQA-316; ViFinQA-612; S_NEW_02; S_NEW_06; ... (+32)) | 6 (16.7%) |
| Đa công ty | 18 (ViFinQA-368; ViFinQA-369; ViFinQA-374; ViFinQA-410; ... (+14)) | 5 (27.8%) |

Nhận xét: E3 lọc cứng giữ đúng công ty khi câu hỏi ghi rõ mã CK;
chi tiết từng công ty xem bảng trên, tổng hợp đầy đủ tại `evaluation/comparison_E0_E1_E2.md`.
Đây là phép thử tách theo công ty ở mức tối thiểu, chưa phải cross-validation đầy đủ.

## 3. Multi-hop thí điểm (ViFinQA-368, đã gắn gold reviewed-agree ở v4)

Câu gốc (rút gọn): năm 2022, trong nhóm HPG HSG MSR NKG,
các công ty có hệ số thanh toán nhanh thấp hơn trung vị của nhóm
có biên lợi nhuận ròng bình quân là bao nhiêu phần trăm?

Bước 1: truy hồi hệ số thanh toán nhanh từng công ty năm 2022.
Bước 2: tính trung vị, lọc nhóm thấp hơn trung vị.
Bước 3: truy hồi biên lợi nhuận ròng của nhóm được lọc rồi tính bình quân.

- Truy hồi `he so thanh toan nhanh HPG nam 2022` -> MSR_2022_consolidated#p002 (10.15); MSR_2022_separate#p002 (10.15); MSR_2022_consolidated#p073 (10.01)
- Truy hồi `he so thanh toan nhanh HSG nam 2022` -> MSR_2022_consolidated#p002 (10.15); MSR_2022_separate#p002 (10.15); MSR_2022_consolidated#p073 (10.01)
- Truy hồi `bien loi nhuan rong NKG nam 2022` -> NKG_2022_consolidated#p013 (7.88); NKG_2023_consolidated#p013 (7.69); NKG_2023_separate#p013 (7.66)

Nhận xét: pipeline 2 bước chạy được về kỹ thuật; ViFinQA-368 ở v4 đã có gold tổng hợp cuối
(0.5909 %, 10 evidence chunks, reviewed-agree) nhưng chưa có gold từng bước con, nên vẫn đánh dấu needs_decomposition.
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

- BM25 1 câu mẫu: 35.6 ms (2407 chunk, chạy tại máy, không GPU).
- Kích thước chunks.jsonl: 6545504 bytes; lsa_index_E1.npz: 2360463 bytes.
- E3 chạy bản v3 (200 câu) mất khoảng 70 giây (alpha = 0.5, cand_k = 20); bản v4 có 204 câu (44 dev + 160 test).
- Cache TF-IDF + SVD giữ nguyên giữa các lần chạy, chỉ nạp 1 lần.
- Hướng giảm chi phí: giảm cand_k từ 20 xuống 10, hoặc lưu sẵn top-20 BM25.

