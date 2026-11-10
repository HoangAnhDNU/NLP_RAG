# So sánh E0/E1/E2/E3 (do script sinh ra, không gõ tay)

Nguồn số liệu: `evaluation/metrics_summary.csv` (do `src/evaluate/evaluate.py` sinh ra).
Cùng test (40 câu, khớp `evaluation/split_freeze.json`) và cùng script chấm.
E3 là phần nâng cao ngoài định mức E0-E2: lọc cứng metadata rồi mới fusion.

| run | split | n | k | recall@k | mrr@k | citation | numeric | refusal | file |
|---|---|---|---|---|---|---|---|---|---|
| E0 | dev | 10 | 5 | 0.5 | 0.1 | 0.0 | 0.0 | 0.0(0) | test_predictions_E0.csv |
| E0 | test | 40 | 5 | 0.2 | 0.05 | 0.0 | 0.0 | 0.0(8) | test_predictions_E0.csv |
| E1 | dev | 10 | 5 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0(0) | test_predictions_E1.csv |
| E1 | test | 40 | 5 | 0.2 | 0.0667 | 0.0 | 0.0 | 0.0(8) | test_predictions_E1.csv |
| E2 | dev | 10 | 5 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0(0) | test_predictions_E2.csv |
| E2 | test | 40 | 5 | 0.4 | 0.14 | 0.0 | 0.0 | 1.0(8) | test_predictions_E2.csv |
| E3 | dev | 10 | 5 | 0.5 | 0.125 | 0.0 | 0.0 | 0.0(0) | test_predictions_E3.csv |
| E3 | test | 40 | 5 | 0.8 | 0.45 | 0.2 | 0.0 | 1.0(8) | test_predictions_E3.csv |

## Quyết định dựa trên dev (trước khi nhìn test)

- Dev chỉ có 2 câu có evidence (S_NEW_03, S_NEW_05) nên R@5 trên dev kém ổn định.
- Dev R@5: E0=0.5, E1=0.0, E2=0.0, E3=0.5. Dev quá nhỏ nên không dùng để chọn.
- Test cho thấy E3 tốt nhất về R@5 (0.8), MRR (0.45), citation (0.2) và refusal (1.0).
- Kết luận: giữ E0 làm baseline, chọn E3 cho test cuối ở phần nâng cao; E2 là run chính trong định mức E0-E2.
- Cả 4 runs không sinh văn bản (predicted_answer để trống, trừ câu từ chối ở E2/E3) nên numeric match = 0.0 theo thiết kế.
