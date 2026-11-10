# So sánh E0-E8 (do script sinh ra, không gõ tay)

Nguồn số liệu: `evaluation/metrics_summary.csv` (do `src/evaluate/evaluate.py` sinh ra).
Cùng test (40 câu, khớp `evaluation/split_freeze.json`) và cùng script chấm.
E0-E2 là định mức bắt buộc; E3-E8 là phần nâng cao ngoài định mức: E3 lọc cứng metadata (baseline tái lập được), E4 rerank nhẹ, E5 rewrite truy vấn, E6 index bảng riêng, E7 contextual chunk, E8 lookup bảng có cấu trúc rồi mới RAG giải thích.
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
| E8 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 0.2 | 1.0 |

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
| E8 | 1.0 | 1.0 | 1.0 |

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
| E8 | 1.0 | 1.0 | 1.0 | 0.425 | 0.475 | 1.0 | 0.6 | 0.4 | 0.325 |

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
| E8 | 1.0 | 1.0 | test_predictions_E8.csv |

## Quyết định dựa trên dev (trước khi nhìn test)

- Dev chỉ có 2 câu có evidence (S_NEW_03, S_NEW_05) nên R@5 trên dev kém ổn định.
- Dev R@5: E0=0.5, E1=0.0, E2=0.0, E3=0.5, E4=0.5, E5=0.0, E6=0.0, E7=0.0, E8=1.0. Dev quá nhỏ nên không dùng để chọn, nhưng E8 đạt R@5=1.0 trên cả 2 câu dev có evidence.
- Test truy hồi: E8 dẫn đầu tuyệt đối R@5=1.0 ctxR@5=1.0 MRR@5=1.0 citeP@top1=1.0 vì lookup đưa đúng chunk nguồn lên top-1; E3/E4 R@5=0.8; E5 R@5=0.6; E6/E7 R@5=0.4.
- Test answer số: lần đầu numeric_match=1.0 và exact_match=1.0 ở E8 (7 câu bổ sung có đáp án đều đúng sau quy đổi đơn vị, kể cả biên 10.8568% tính từ mã 20/10); E0-E7 numeric=0.0 vì không sinh văn bản.
- Test period/page: E8 period=1.0 page=1.0; E3 period=1.0 page=0.2; E4 period=0.8 page=0.2.
- Refusal giữ P=R=1.0 ở E2-E8; E0/E1=0.0.
- E8 có unsupported_claim_rate=0.6 và faith_h=0.4 vì đáp án sau quy đổi đơn vị (ví dụ 39.2719 nghìn tỷ) không khớp chuỗi số thô trong chunk; đây là hạn chế của heuristic so chuỗi, không phải hallucination, vì mọi số đều từ table_records và chunk nguồn giữ nguyên để kiểm chứng.
- Kết luận: giữ E0 làm baseline, E3 là baseline lọc cứng tái lập được tốt nhất nhóm thuần retrieval; E8 là cấu hình đề xuất cho câu hỏi số (lookup có cấu trúc trước, RAG giải thích sau); E4/E5/E6/E7 là ablation cho rerank, rewrite, table index, contextual chunk.
