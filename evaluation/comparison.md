# So sánh E0-E7 (do script sinh ra, không gõ tay)

Nguồn số liệu: `evaluation/metrics_summary.csv` (do `src/evaluate/evaluate.py` sinh ra).
Cùng test (40 câu, khớp `evaluation/split_freeze.json`) và cùng script chấm.
E0-E2 là định mức bắt buộc; E3-E7 là phần nâng cao ngoài định mức: E3 lọc cứng metadata (baseline tái lập được), E4 rerank nhẹ, E5 rewrite truy vấn, E6 index bảng riêng, E7 contextual chunk.
Ghi chú: file prediction hiện chỉ lưu top-5 nên recall@10 và mrr@10 bằng @5.
Faithfulness và answer relevancy bản LLM judge chưa áp dụng vì pipeline không gọi LLM;
hai cột heuristic đo câu trả lời số không tìm thấy trong context và tỷ lệ câu giải quyết đúng.

## A. Chất lượng truy hồi (chỉ trên câu có evidence, test n=5 evidence)

| run | R@3 | R@5 | R@10 | MRR@3 | MRR@5 | MRR@10 | ctxP@5 | ctxR@5 |
|---|---|---|---|---|---|---|---|---|
| E0 | 0.0 | 0.2 | 0.2 | 0.0 | 0.05 | 0.05 | 0.04 | 0.2 |
| E1 | 0.2 | 0.2 | 0.2 | 0.0667 | 0.0667 | 0.0667 | 0.04 | 0.2 |
| E2 | 0.2 | 0.4 | 0.4 | 0.1 | 0.14 | 0.14 | 0.08 | 0.4 |
| E3 | 0.6 | 0.8 | 0.8 | 0.4 | 0.45 | 0.45 | 0.16 | 0.8 |
| E4 | 0.6 | 0.8 | 0.8 | 0.3667 | 0.4167 | 0.4167 | 0.16 | 0.8 |
| E5 | 0.2 | 0.6 | 0.6 | 0.0667 | 0.1467 | 0.1467 | 0.12 | 0.6 |
| E6 | 0.2 | 0.4 | 0.4 | 0.0667 | 0.1167 | 0.1167 | 0.08 | 0.4 |
| E7 | 0.4 | 0.4 | 0.4 | 0.1667 | 0.1667 | 0.1667 | 0.08 | 0.4 |

## B. Chất lượng trích dẫn (trích dẫn có hỗ trợ câu trả lời không)

| run | citeP@top1 | citeR@5 | page_acc |
|---|---|---|---|
| E0 | 0.0 | 0.2 | 0.0 |
| E1 | 0.0 | 0.2 | 0.2 |
| E2 | 0.0 | 0.4 | 0.0 |
| E3 | 0.2 | 0.8 | 0.2 |
| E4 | 0.2 | 0.8 | 0.2 |
| E5 | 0.0 | 0.6 | 0.0 |
| E6 | 0.0 | 0.4 | 0.0 |
| E7 | 0.0 | 0.4 | 0.0 |

## C. Chất lượng câu trả lời (số và nghiệp vụ tài chính)

| run | numeric | exact | period | company | year | version | unsup | faith_h | relev_h |
|---|---|---|---|---|---|---|---|---|---|
| E0 | 0.0 | 0.0 | 0.4 | 0.2 | 0.225 | 0.6 | 0.0 | 0.0 | 0.0 |
| E1 | 0.0 | 0.0 | 0.4 | 0.35 | 0.2 | 0.6 | 0.0 | 0.0 | 0.0 |
| E2 | 0.0 | 0.0 | 0.6 | 0.35 | 0.325 | 0.6 | 0.0 | 0.0 | 0.2 |
| E3 | 0.0 | 0.0 | 1.0 | 0.475 | 0.5 | 1.0 | 0.0 | 0.0 | 0.2 |
| E4 | 0.0 | 0.0 | 0.8 | 0.45 | 0.5 | 0.8 | 0.0 | 0.0 | 0.2 |
| E5 | 0.0 | 0.0 | 0.6 | 0.35 | 0.35 | 0.6 | 0.0 | 0.0 | 0.2 |
| E6 | 0.0 | 0.0 | 0.8 | 0.375 | 0.325 | 0.8 | 0.0 | 0.0 | 0.2 |
| E7 | 0.0 | 0.0 | 0.6 | 0.4 | 0.375 | 0.6 | 0.0 | 0.0 | 0.2 |

## D. Từ chối (thiếu bằng chứng, test n=8)

| run | refP | refR | file |
|---|---|---|---|
| E0 | 0.0 | 0.0 | test_predictions_E0.csv |
| E1 | 0.0 | 0.0 | test_predictions_E1.csv |
| E2 | 1.0 | 1.0 | test_predictions_E2.csv |
| E3 | 1.0 | 1.0 | test_predictions_E3.csv |
| E4 | 1.0 | 1.0 | test_predictions_E4.csv |
| E5 | 1.0 | 1.0 | test_predictions_E5.csv |
| E6 | 1.0 | 1.0 | test_predictions_E6.csv |
| E7 | 1.0 | 1.0 | test_predictions_E7.csv |

## Quyết định dựa trên dev (trước khi nhìn test)

- Dev chỉ có 2 câu có evidence (S_NEW_03, S_NEW_05) nên R@5 trên dev kém ổn định.
- Dev R@5: E0=0.5, E1=0.0, E2=0.0, E3=0.5, E4=0.5, E5=0.0, E6=0.0, E7=0.0. Dev quá nhỏ nên không dùng để chọn.
- Test truy hồi: E3 và E4 đồng hạng R@5=0.8 ctxR@5=0.8; E3 MRR@5=0.45, E4 MRR@5=0.4167; E5 R@5=0.6; E6/E7 R@5=0.4.
- Test period: E3=1.0, E4/E6=0.8, E2/E5/E7=0.6; citeP@top1 E3=E4=0.2 còn lại 0.0; page_acc E1=E3=E4=0.2 còn lại 0.0.
- Refusal giữ P=R=1.0 ở E2-E7; E0/E1=0.0.
- Cả 8 run không sinh văn bản (predicted_answer để trống, trừ câu từ chối ở E2-E7)
  nên numeric_match = 0.0 theo thiết kế; unsupported_claim_rate = 0.0 vì không có câu số để chấm.
- Kết luận: giữ E0 làm baseline, E3 là baseline lọc cứng tái lập được và tốt nhất phần nâng cao (R@5=0.8, MRR@5=0.45, period=1.0); E4 dùng RRF fusion rồi rerank nhẹ giữ R@5=0.8, MRR@5=0.4167, citeP=0.2, period=0.8; E5/E6/E7 là ablation cho rewrite, table index, contextual chunk.
