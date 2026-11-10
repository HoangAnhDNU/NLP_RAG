# So sánh E0-E8 (do script sinh ra, không gõ tay)

Nguồn số liệu: `evaluation/metrics_summary.csv` (do `src/evaluate/evaluate.py` sinh ra).
Cùng test (160 câu, khớp `evaluation/split_freeze.json`) và cùng script chấm. Prediction nằm ở `evaluation/test_predictions/` và `evaluation/dev_predictions/`, nhãn refusal ở `evaluation/refusal_labels/`.
E0-E2 là định mức bắt buộc; E3-E8 là phần nâng cao ngoài định mức: E3 lọc cứng metadata (baseline tái lập được), E4 rerank nhẹ, E5 rewrite truy vấn, E6 index bảng riêng, E7 contextual chunk, E8 lookup bảng có cấu trúc rồi mới RAG giải thích.
Ghi chú: file prediction hiện chỉ lưu top-5 nên recall@10 và mrr@10 bằng @5.
Faithfulness và answer relevancy bản LLM judge chưa áp dụng vì pipeline không gọi LLM;
hai cột heuristic đo câu trả lời số không tìm thấy trong context và tỷ lệ câu giải quyết đúng.

## A. Chất lượng truy hồi (chỉ trên câu có evidence, test n=118 evidence)

| run | R@3 | R@5 | R@10 | MRR@3 | MRR@5 | MRR@10 | ctxP@5 | ctxR@5 |
|---|---|---|---|---|---|---|---|---|
| E0 | 0.0508 | 0.0847 | 0.0847 | 0.0452 | 0.0528 | 0.0528 | 0.0169 | 0.0847 |
| E1 | 0.0169 | 0.0254 | 0.0254 | 0.0113 | 0.0134 | 0.0134 | 0.0051 | 0.0254 |
| E2 | 0.1102 | 0.1356 | 0.1356 | 0.0523 | 0.0582 | 0.0582 | 0.0271 | 0.1356 |
| E3 | 0.1271 | 0.2034 | 0.2034 | 0.0876 | 0.1049 | 0.1049 | 0.0407 | 0.2034 |
| E4 | 0.1525 | 0.1864 | 0.1864 | 0.1003 | 0.1079 | 0.1079 | 0.0373 | 0.1864 |
| E5 | 0.1102 | 0.1441 | 0.1441 | 0.0508 | 0.0576 | 0.0576 | 0.0288 | 0.1441 |
| E6 | 0.0847 | 0.1441 | 0.1441 | 0.0452 | 0.0592 | 0.0592 | 0.0288 | 0.1441 |
| E7 | 0.1102 | 0.1271 | 0.1271 | 0.0607 | 0.0645 | 0.0645 | 0.0254 | 0.1271 |
| E8 | 0.4746 | 0.4831 | 0.4831 | 0.4703 | 0.4725 | 0.4725 | 0.0966 | 0.4831 |

## B. Chất lượng trích dẫn (trích dẫn có hỗ trợ câu trả lời không)

| run | citeP@top1 | citeR@5 | page_acc | citeFull |
|---|---|---|---|---|
| E0 | 0.0424 | 0.0847 | 0.0508 | 1.0 |
| E1 | 0.0085 | 0.0254 | 0.0254 | 1.0 |
| E2 | 0.0085 | 0.1356 | 0.0169 | 1.0 |
| E3 | 0.0508 | 0.2034 | 0.0763 | 1.0 |
| E4 | 0.0593 | 0.1864 | 0.0678 | 1.0 |
| E5 | 0.0085 | 0.1441 | 0.0169 | 1.0 |
| E6 | 0.0169 | 0.1441 | 0.0254 | 1.0 |
| E7 | 0.0254 | 0.1271 | 0.0254 | 1.0 |
| E8 | 0.4661 | 0.4831 | 0.822 | 1.0 |

## C. Chất lượng câu trả lời (số và nghiệp vụ tài chính)

| run | numeric | exact | period | company | year | version | unsup | faith_h | relev_h | falseAns |
|---|---|---|---|---|---|---|---|---|---|---|
| E0 | 0.0 | 0.0 | 0.3137 | 0.4437 | 0.3187 | 0.7843 | 0.0 | 0.0 | 0.0 | 1.0 |
| E1 | 0.0 | 0.0 | 0.451 | 0.6625 | 0.2375 | 0.8627 | 0.0 | 0.0 | 0.0 | 1.0 |
| E2 | 0.0 | 0.0 | 0.4314 | 0.5437 | 0.3563 | 0.8824 | 0.0 | 0.0 | 0.075 | 0.925 |
| E3 | 0.0 | 0.0 | 0.5686 | 0.5188 | 0.45 | 0.9804 | 0.0 | 0.0 | 0.075 | 0.925 |
| E4 | 0.0 | 0.0 | 0.6471 | 0.675 | 0.45 | 0.8627 | 0.0 | 0.0 | 0.075 | 0.925 |
| E5 | 0.0 | 0.0 | 0.4314 | 0.5375 | 0.3937 | 0.8627 | 0.0 | 0.0 | 0.075 | 0.925 |
| E6 | 0.0 | 0.0 | 0.4314 | 0.5625 | 0.3375 | 0.9216 | 0.0 | 0.0 | 0.075 | 0.925 |
| E7 | 0.0 | 0.0 | 0.4118 | 0.5062 | 0.3563 | 0.9608 | 0.0 | 0.0 | 0.075 | 0.925 |
| E8 | 0.4068 | 0.3983 | 0.9804 | 0.8688 | 0.4313 | 0.9804 | 0.2288 | 0.7712 | 0.375 | 0.625 |

## D. Từ chối và trạng thái trả lời (thiếu bằng chứng, test n=16)

| run | refP | refR | TR | MR | FR | TA | ans | part | ref | amb | file |
|---|---|---|---|---|---|---|---|---|---|---|---|
| E0 | 0.0 | 0.0 | 0 | 16 | 0 | 144 | 0 | 125 | 0 | 35 | test_predictions_E0.csv |
| E1 | 0.0 | 0.0 | 0 | 16 | 0 | 144 | 0 | 132 | 0 | 28 | test_predictions_E1.csv |
| E2 | 1.0 | 0.75 | 12 | 4 | 0 | 144 | 0 | 124 | 12 | 24 | test_predictions_E2.csv |
| E3 | 1.0 | 0.75 | 12 | 4 | 0 | 144 | 0 | 128 | 12 | 20 | test_predictions_E3.csv |
| E4 | 1.0 | 0.75 | 12 | 4 | 0 | 144 | 0 | 138 | 12 | 10 | test_predictions_E4.csv |
| E5 | 1.0 | 0.75 | 12 | 4 | 0 | 144 | 0 | 128 | 12 | 20 | test_predictions_E5.csv |
| E6 | 1.0 | 0.75 | 12 | 4 | 0 | 144 | 0 | 120 | 12 | 28 | test_predictions_E6.csv |
| E7 | 1.0 | 0.75 | 12 | 4 | 0 | 144 | 0 | 121 | 12 | 27 | test_predictions_E7.csv |
| E8 | 1.0 | 0.75 | 12 | 4 | 0 | 144 | 148 | 0 | 12 | 0 | test_predictions_E8.csv |

## Quyet dinh dua tren dev (truoc khi nhin test)

- Dev co 31 cau co evidence tren 40 cau. Dev R@5: E0=0.0968, E1=0.0968, E2=0.129, E3=0.2581, E4=0.2903, E5=0.129, E6=0.129, E7=0.0968, E8=0.3871.
- Test truy hoi R@5: E0=0.0847, E1=0.0254, E2=0.1356, E3=0.2034, E4=0.1864, E5=0.1441, E6=0.1441, E7=0.1271, E8=0.4831.
- Test answer so numeric_match: E0=0.0, E1=0.0, E2=0.0, E3=0.0, E4=0.0, E5=0.0, E6=0.0, E7=0.0, E8=0.4068.
- Test refusal P/R: E0=0.0/0.0, E1=0.0/0.0, E2=1.0/0.75, E3=1.0/0.75, E4=1.0/0.75, E5=1.0/0.75, E6=1.0/0.75, E7=1.0/0.75, E8=1.0/0.75.
- Test false_answer_rate: E0=1.0, E1=1.0, E2=0.925, E3=0.925, E4=0.925, E5=0.925, E6=0.925, E7=0.925, E8=0.625.
- E8 la cau hinh de xuat cho cau hoi so (lookup co cau truc truoc, RAG giai thich sau); E3 la baseline loc cung tai lap duoc tot nhat nhom thuan retrieval; E0 giu lam baseline; E4/E5/E6/E7 la ablation cho rerank, rewrite, table index, contextual chunk.
