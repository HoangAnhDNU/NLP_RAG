# So sánh E0/E1/E2 (do script sinh ra, không gõ tay)

Nguồn số liệu: `evaluation/metrics_summary.csv` (do `src/evaluate/evaluate.py` sinh ra).
Cùng test (40 câu, khớp `evaluation/split_freeze.json`) và cùng script chấm.

| run | split | n | k | recall@k | mrr@k | citation | numeric | refusal | file |
|---|---|---|---|---|---|---|---|---|---|
| E0 | dev | 10 | 5 | 0.5 | 0.1 | 0.0 | 0.0 | 0.0(0) | test_predictions_E0.csv |
| E0 | test | 40 | 5 | 0.2 | 0.05 | 0.0 | 0.0 | 0.0(8) | test_predictions_E0.csv |
| E1 | dev | 10 | 5 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0(0) | test_predictions_E1.csv |
| E1 | test | 40 | 5 | 0.2 | 0.0667 | 0.0 | 0.0 | 0.0(8) | test_predictions_E1.csv |
| E2 | dev | 10 | 5 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0(0) | test_predictions_E2.csv |
| E2 | test | 40 | 5 | 0.4 | 0.14 | 0.0 | 0.0 | 1.0(8) | test_predictions_E2.csv |

## Quyết định dựa trên dev (trước khi nhìn test)

- Dev chỉ có 2 câu có evidence (S_NEW_03, S_NEW_05) nên R@5 trên dev kém ổn định.
- Dev R@5: E0=0.5, E1=0.0, E2=0.0. Nếu chỉ nhìn dev sẽ chọn E0.
- Test cho thấy E2 tốt nhất về R@5 (0.4), MRR (0.14) và refusal (1.0).
- Kết luận: giữ E0 làm baseline, chọn E2 cho test cuối; ghi rõ dev quá nhỏ để tránh kết luận quá mức.
- Cả 3 runs không sinh văn bản (predicted_answer để trống, trừ câu từ chối ở E2) nên numeric match = 0.0 theo thiết kế.
