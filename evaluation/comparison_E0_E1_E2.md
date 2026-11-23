# So sánh E0-E8 (do script sinh ra, không gõ tay)

Nguồn số liệu: `evaluation/metrics_summary.csv` (do `src/evaluate/evaluate.py` sinh ra).
Cùng test (160 câu, khớp `evaluation/split_freeze.json`) và cùng script chấm. Prediction nằm ở `evaluation/test_predictions/` và `evaluation/dev_predictions/`, nhãn refusal ở `evaluation/refusal_labels/`.
E0-E2 là định mức bắt buộc; E3-E8 là phần nâng cao ngoài định mức: E3 lọc cứng metadata (baseline tái lập được), E4 rerank nhẹ, E5 rewrite truy vấn, E6 index bảng riêng, E7 contextual chunk, E8 lookup bảng có cấu trúc rồi mới RAG giải thích.
Ghi chú @10: file prediction lưu top-10 `predicted_chunk_ids` (`k>=10`) nên `R@10` và `MRR@10` được tính trên đủ 10 chunk, còn `R@5`, `MRR@5`, `ctxP@5`, `ctxR@5` tính chặt trên top-5.
Faithfulness và answer relevancy bản LLM judge chưa áp dụng vì pipeline không gọi LLM;
hai cột heuristic đo câu trả lời số không tìm thấy trong context và tỷ lệ câu giải quyết đúng.

## A. Chất lượng truy hồi (chỉ trên câu có evidence, test n=144 evidence)

| run | R@3 | R@5 | R@10 | MRR@3 | MRR@5 | MRR@10 | ctxP@5 | ctxR@5 |
|---|---|---|---|---|---|---|---|---|
| E0 | 0.0486 | 0.0764 | 0.125 | 0.044 | 0.0502 | 0.0563 | 0.0153 | 0.0764 |
| E1 | 0.0278 | 0.0417 | 0.0903 | 0.0185 | 0.022 | 0.0284 | 0.0083 | 0.0296 |
| E2 | 0.1042 | 0.1389 | 0.2083 | 0.0567 | 0.065 | 0.0743 | 0.0278 | 0.1267 |
| E3 | 0.1319 | 0.2361 | 0.4167 | 0.0903 | 0.1142 | 0.1377 | 0.0514 | 0.2016 |
| E4 | 0.1389 | 0.1944 | 0.2986 | 0.0961 | 0.1082 | 0.1226 | 0.0403 | 0.1772 |
| E5 | 0.1042 | 0.1458 | 0.2222 | 0.0556 | 0.0642 | 0.0734 | 0.0306 | 0.135 |
| E6 | 0.1042 | 0.1875 | 0.25 | 0.059 | 0.0785 | 0.0861 | 0.0417 | 0.1388 |
| E7 | 0.1042 | 0.1458 | 0.2153 | 0.0637 | 0.0734 | 0.0827 | 0.0292 | 0.1208 |
| E8 | 0.8472 | 0.8611 | 0.8889 | 0.8472 | 0.8507 | 0.8547 | 0.1722 | 0.849 |

## B. Chất lượng trích dẫn (trích dẫn có hỗ trợ câu trả lời không)

| run | citeP@top1 | citeR@5 | page_acc | citeFull |
|---|---|---|---|---|
| E0 | 0.0417 | 0.0764 | 0.0486 | 1.0 |
| E1 | 0.0139 | 0.0417 | 0.0278 | 1.0 |
| E2 | 0.0208 | 0.1389 | 0.0278 | 1.0 |
| E3 | 0.0556 | 0.2361 | 0.0764 | 1.0 |
| E4 | 0.0625 | 0.1944 | 0.0694 | 1.0 |
| E5 | 0.0208 | 0.1458 | 0.0347 | 1.0 |
| E6 | 0.0278 | 0.1875 | 0.0417 | 1.0 |
| E7 | 0.0347 | 0.1458 | 0.0347 | 1.0 |
| E8 | 0.8472 | 0.8611 | 0.8472 | 1.0 |

## C. Chất lượng câu trả lời (số và nghiệp vụ tài chính)

| run | numeric | exact | period | company | year | version | unsup | faith_h | relev_h | falseAns |
|---|---|---|---|---|---|---|---|---|---|---|
| E0 | 0.0 | 0.0 | 0.3036 | 0.4437 | 0.3187 | 0.7679 | 0.0 | 0.0 | 0.0 | 1.0 |
| E1 | 0.0 | 0.0 | 0.4286 | 0.6625 | 0.2375 | 0.8393 | 0.0 | 0.0 | 0.0 | 1.0 |
| E2 | 0.0 | 0.0 | 0.4464 | 0.5437 | 0.3563 | 0.875 | 0.0 | 0.0 | 0.1 | 0.9 |
| E3 | 0.0 | 0.0 | 0.5893 | 0.5188 | 0.45 | 0.9643 | 0.0 | 0.0 | 0.075 | 0.925 |
| E4 | 0.0 | 0.0 | 0.6429 | 0.675 | 0.45 | 0.8393 | 0.0 | 0.0 | 0.075 | 0.925 |
| E5 | 0.0 | 0.0 | 0.4464 | 0.5375 | 0.3937 | 0.8571 | 0.0 | 0.0 | 0.075 | 0.925 |
| E6 | 0.0 | 0.0 | 0.4286 | 0.5625 | 0.3375 | 0.8929 | 0.0 | 0.0 | 0.075 | 0.925 |
| E7 | 0.0 | 0.0 | 0.4107 | 0.5062 | 0.3563 | 0.9286 | 0.0 | 0.0 | 0.075 | 0.925 |
| E8 | 0.8472 | 0.7847 | 0.9821 | 0.8688 | 0.8313 | 0.9821 | 0.0 | 1.0 | 0.8625 | 0.1375 |

## D. Từ chối và trạng thái trả lời (thiếu bằng chứng, test n=16)

| run | refP | refR | TR | MR | FR | TA | ans | part | ref | amb | file |
|---|---|---|---|---|---|---|---|---|---|---|---|
| E0 | 0.0 | 0.0 | 0 | 16 | 0 | 144 | 0 | 125 | 0 | 35 | test_predictions_E0.csv |
| E1 | 0.0 | 0.0 | 0 | 16 | 0 | 144 | 0 | 132 | 0 | 28 | test_predictions_E1.csv |
| E2 | 1.0 | 1.0 | 16 | 0 | 0 | 144 | 0 | 120 | 16 | 24 | test_predictions_E2.csv |
| E3 | 1.0 | 0.75 | 12 | 4 | 0 | 144 | 0 | 128 | 12 | 20 | test_predictions_E3.csv |
| E4 | 1.0 | 0.75 | 12 | 4 | 0 | 144 | 0 | 138 | 12 | 10 | test_predictions_E4.csv |
| E5 | 1.0 | 0.75 | 12 | 4 | 0 | 144 | 0 | 128 | 12 | 20 | test_predictions_E5.csv |
| E6 | 1.0 | 0.75 | 12 | 4 | 0 | 144 | 0 | 120 | 12 | 28 | test_predictions_E6.csv |
| E7 | 1.0 | 0.75 | 12 | 4 | 0 | 144 | 0 | 121 | 12 | 27 | test_predictions_E7.csv |
| E8 | 1.0 | 1.0 | 16 | 0 | 0 | 144 | 121 | 23 | 16 | 0 | test_predictions_E8.csv |

## Quyet dinh dua tren dev (truoc khi nhin test)

- Dev co 40 cau co evidence va 4 cau thieu bang chung tren 44 cau. Dev R@5: E0=0.1, E1=0.125, E2=0.125, E3=0.3, E4=0.275, E5=0.125, E6=0.15, E7=0.1, E8=0.85.
- Dev refusal P/R: E0=0.0/0.0, E1=0.0/0.0, E2=1.0/1.0, E3=1.0/1.0, E4=1.0/1.0, E5=1.0/1.0, E6=1.0/1.0, E7=1.0/1.0, E8=1.0/1.0.
- Test truy hoi R@5: E0=0.0764, E1=0.0417, E2=0.1389, E3=0.2361, E4=0.1944, E5=0.1458, E6=0.1875, E7=0.1458, E8=0.8611.
- Test answer so numeric_match: E0=0.0, E1=0.0, E2=0.0, E3=0.0, E4=0.0, E5=0.0, E6=0.0, E7=0.0, E8=0.8472.
- Test refusal P/R: E0=0.0/0.0, E1=0.0/0.0, E2=1.0/1.0, E3=1.0/0.75, E4=1.0/0.75, E5=1.0/0.75, E6=1.0/0.75, E7=1.0/0.75, E8=1.0/1.0.
- Test false_answer_rate: E0=1.0, E1=1.0, E2=0.9, E3=0.925, E4=0.925, E5=0.925, E6=0.925, E7=0.925, E8=0.1375.
- E8 la cau hinh de xuat cho cau hoi so (lookup co cau truc truoc, RAG giai thich sau); E3 la baseline loc cung tai lap duoc tot nhat nhom thuan retrieval; E0 giu lam baseline; E4/E5/E6/E7 la ablation cho rerank, rewrite, table index, contextual chunk.
