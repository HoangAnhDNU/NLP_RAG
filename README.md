# Hỏi đáp báo cáo tài chính tiếng Việt có trích dẫn với RAG (CSC4007 Đề tài 6)

Repo thực hiện pipeline RAG khép kín trên báo cáo tài chính OCR tiếng Việt:
truy hồi theo trang, trích dẫn `company_id`, `fiscal_year`, `report_version`,
`page`, `chunk_id`, chấm retrieval và answer riêng, từ chối đúng nguyên văn
khi thiếu bằng chứng.

## 1. Dữ liệu và phạm vi

- **Nguồn:** `AIGuruTinix/ViFinQA`, revision `0450088ab22ec946f04f097586967ca405955b3b` (giấy phép trong manifest: `unknown_verify_with_teacher`).
- **Corpus thực dùng:** 4 mã `HPG`, `HSG`, `NKG`, `MSR`, giai đoạn `2020-2024`,
- Nguồn: `AIGuruTinix/ViFinQA`, revision `0450088ab22ec946f04f097586967ca405955b3b` (giấy phép trong manifest: `unknown_verify_with_teacher`).
- Corpus thực dùng: 4 mã `HPG`, `HSG`, `NKG`, `MSR`, giai đoạn `2020-2024`,
  40 báo cáo gồm cả 2 bản `consolidated` và `separate` (tổng 2.437 trang OCR, 2.585 bảng HTML).
- **Chunk & Bảng số:** **2.407** chunk trong `data/processed/chunks.jsonl` (1 chunk = 1 trang không rỗng, loại 30 trang rỗng OCR, văn bản chuẩn NFC giữ dấu tiếng Việt) và **29.615** bản ghi bảng số chuẩn hóa trong `data/processed/table_records.jsonl`.
- **Gold (`v4`):** **204** câu trong `data/annotations/qa_gold.jsonl` (`0` `pending-answer`):
- Chunk và Bảng số: **2.407** chunk trong `data/processed/chunks.jsonl` (1 chunk = 1 trang không rỗng, loại 30 trang rỗng OCR, văn bản chuẩn NFC giữ dấu tiếng Việt) và **29.615** bản ghi bảng số chuẩn hóa trong `data/processed/table_records.jsonl`.
- Gold (`v4`): **204** câu trong `data/annotations/qa_gold.jsonl` (`0` `pending-answer`):
  - **35** câu `vifinqa` đã được giải đầy đủ kèm phép tính và trích dẫn `quote` nguyên văn từ `chunks.jsonl`;
  - **15** câu `supplement` (`S_NEW_01..07` số liệu kiểm chứng, `S_NEW_08..15` từ chối);
  - **150** câu `table-clean` (`55` T1 tra cứu, `44` T2 thời gian, `43` T3 chênh lệch, `8` T5 ngoài corpus);
  - **4** câu `dev-refusal` (`DEV-REF-01..04`) bổ sung riêng vào `dev` ở bản `v4`.
  Bản v1 giữ tại `data/annotations/qa_gold_v1_50.jsonl` để đối chiếu.
  Hậu kiểm chéo phân tầng qua `src/cross_review.py` (`data/annotations/review_report.md`): kiểm tra độc lập **53/204 (25.98%)** câu đạt **0 bất đồng** (tổng cộng **57/204 = 27.94%** đạt `reviewed-agree`).
- **Split `v4`:** `dev` **44** câu (40 trả lời được + 4 câu thiếu bằng chứng `dev-refusal`), `test` **160** câu (144 câu có evidence + 16 câu thiếu bằng chứng, giữ nguyên vẹn 100% từ `v3`), `seed = 42`, khóa tại `data/splits/split_meta.json` và bản sao nguyên vẹn tại `evaluation/split_freeze.json` (`sha256`: `0012ebccd6712b44cdd1faf18f020c547c82973db09d37ab2b9e96b0a94a34b4`). Chỉ tuning trên `dev`, chỉ công bố số liệu cuối trên `test`.
- Split `v4`: `dev` **44** câu (40 trả lời được + 4 câu thiếu bằng chứng `dev-refusal`), `test` **160** câu (144 câu có evidence + 16 câu thiếu bằng chứng, giữ nguyên vẹn 100% từ `v3`), `seed = 42`, khóa tại `data/splits/split_meta.json` và bản sao nguyên vẹn tại `evaluation/split_freeze.json` (`sha256`: `0012ebccd6712b44cdd1faf18f020c547c82973db09d37ab2b9e96b0a94a34b4`). Chỉ tuning trên `dev`, chỉ công bố số liệu cuối trên `test`.

## 2. Môi trường

Sử dụng Python virtual environment `.venv` trên Windows (khuyến nghị PowerShell):

```powershell
.\.venv\Scripts\python.exe -c "import sys, sklearn, streamlit; print(sys.version.split()[0], sklearn.__version__, streamlit.__version__)"
```

Phiên bản đã kiểm chứng trong `.venv` (ngày `2026-11-15`; chạy hoàn toàn trên CPU với thư viện nhẹ, không yêu cầu framework deep learning nặng):

| Thư viện | Phiên bản | Vai trò |
|---|---|---|
| Python | 3.10.22 | Runtime |
| scikit-learn | 1.7.2 | TF-IDF & SVD (E1-E7) |
| pandas | 2.3.3 | Xử lý CSV, metrics & báo cáo |
| numpy | 2.2.6 | Tính toán vector |
| scipy | 1.15.3 | Ma trận thưa & thống kê |
| PyYAML | 6.0.3 | Đọc cấu hình YAML (`config/`) |
| streamlit | 1.65.0 | Giao diện Web demo (`app/streamlit_app.py`) |
| huggingface_hub | 1.30.0 | Tải snapshot dữ liệu nguồn (`download_vifinqa.py`) |
| matplotlib | 3.10.9 | Vẽ biểu đồ (`report/figures/`) |
| Pillow | 12.3.0 | Xử lý ảnh biểu đồ |

Cài đặt sạch toàn bộ phụ thuộc cốt lõi:
Cài đặt các thư viện trong `requirements.txt`:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Mọi script đọc và ghi file bằng `encoding="utf-8"`.

## 3. Tái lập dữ liệu

Thư mục `data/raw/` **không được commit lên Git** (chỉ lưu snapshot cục bộ khi chạy pipeline). Nếu clone mới chưa có dữ liệu thô, tải từ Hugging Face trước:

```powershell
.\.venv\Scripts\python.exe src\download_vifinqa.py --mode questions
.\.venv\Scripts\python.exe src\download_vifinqa.py --mode corpus --tickers HPG HSG NKG MSR --years 2020 2021 2022 2023 2024
```

Tái lập corpus, chunk, bảng số, bộ gold `v4`, hậu kiểm chéo và tài liệu dữ liệu:

```powershell
.\.venv\Scripts\python.exe src\select_corpus.py --tickers HPG HSG NKG MSR --years 2020 2021 2022 2023 2024 --versions consolidated separate
.\.venv\Scripts\python.exe src\filter_questions.py --tickers HPG HSG NKG MSR --years 2020 2021 2022 2023 2024
.\.venv\Scripts\python.exe src\audit_ocr.py
.\.venv\Scripts\python.exe src\build_chunks.py
.\.venv\Scripts\python.exe src\build_table_records.py
.\.venv\Scripts\python.exe src\build_supplement_gold.py
.\.venv\Scripts\python.exe src\build_gold.py --force-v1   # Mặc định khóa không cho ghi đè qa_gold.jsonl > 50 dòng nếu thiếu --force-v1
.\.venv\Scripts\python.exe src\build_expanded_gold_v2.py
.\.venv\Scripts\python.exe src\build_expanded_gold_v3.py
.\.venv\Scripts\python.exe src\resolve_vifinqa_and_dev_refusal.py
.\.venv\Scripts\python.exe src\cross_review.py
.\.venv\Scripts\python.exe src\build_data_docs.py
.\.venv\Scripts\python.exe src\data_quality_report.py
```

Kết quả chính: `data/processed/chunks.jsonl` (`2.407` chunk), `data/processed/table_records.jsonl` (`29.615` bản ghi), `data/processed/questions_matched.csv` (`35` câu), `data/processed/questions_dropped.csv` (`977` câu), `data/annotations/qa_gold.jsonl` (`204` câu `v4`), `data/data_manifest.csv` (`244` dòng), `data/data_schema.md`, `data/README.md`, `report/data_quality_report.md`.

## 4. Chạy E0-E2 và E3-E8 nâng cao

| Run | Phương pháp | Config | Ghi chú |
|---|---|---|---|
| E0 | BM25 unigram, `k1=1.5`, `b=0.75`, top-10 lưu | `config/e0_bm25.yaml` | Baseline, không sinh văn bản |
| E1 | Dense LSA trên TF-IDF bigram, SVD 128, seed 42 | `config/e1_tfidf.yaml` | Đối chứng dense với BM25 |
| E2 | Hybrid `0.5 BM25 + 0.5 LSA` trên top 20, cộng metadata bonus & refusal gating | `config/e2_hybrid.yaml` | Khác E1 ở chiến lược fusion và refusal |
| E3 | Lọc cứng metadata công ty/năm/bản rồi fusion `0.5 BM25 + 0.5 LSA` | `config/e3_filter.yaml` | Baseline lọc cứng tái lập được |
| E4 | `RRF(k=60)` BM25 + LSA rồi rerank nhẹ thay cross-encoder | `config/e4_rerank.yaml` | Pipeline hai tầng offline |
| E5 | Tách công ty/năm/chỉ tiêu, sinh tối đa 3 biến thể truy vấn, max-pooling | `config/e5_query_rewrite.yaml` | Ablation query rewrite |
| E6 | Index riêng nội dung bảng (`0.7` full-text + `0.3` bảng) rồi hybrid | `config/e6_table_index.yaml` | Ablation index bảng |
| E7 | Gắn header `[CTY \| Năm \| Bản \| Trang \| Đơn vị \| Bảng]` vào chunk rồi hybrid | `config/e7_contextual.yaml` | Ablation contextual chunk |
| E8 | Lookup & tổng hợp có cấu trúc (`src/retrieval/table_lookup.py`, gồm so sánh T2/T3) + hybrid RAG | `config/e8_table_lookup.yaml` | Trả lời số trực tiếp kèm chứng cứ gốc |

```powershell
.\.venv\Scripts\python.exe src\infer\e0_bm25.py
.\.venv\Scripts\python.exe src\infer\e1_lsa.py
.\.venv\Scripts\python.exe src\infer\e2_hybrid.py
.\.venv\Scripts\python.exe src\infer\e3_filter.py
.\.venv\Scripts\python.exe src\infer\e4_rerank.py
.\.venv\Scripts\python.exe src\infer\e5_query_rewrite.py
.\.venv\Scripts\python.exe src\infer\e6_table_index.py
.\.venv\Scripts\python.exe src\infer\e7_contextual.py
.\.venv\Scripts\python.exe src\infer\e8_table_lookup.py
```

Mỗi script suy luận lưu đủ **top-10** `predicted_chunk_ids` vào `evaluation/dev_predictions/dev_predictions_E*.csv` (`n=44`) và `evaluation/test_predictions/test_predictions_E*.csv` (`n=160`).

## 5. Chấm metric, Unit Tests và So sánh

Chạy chấm metric, tổng hợp, phân tích lỗi và bộ 35 unit test trong `tests/`:

```powershell
foreach ($r in "E0","E1","E2","E3","E4","E5","E6","E7","E8") { .\.venv\Scripts\python.exe src\evaluate\evaluate.py --run $r }
.\.venv\Scripts\python.exe src\evaluate\compare_runs.py
.\.venv\Scripts\python.exe src\evaluate\seed_check_e1.py
.\.venv\Scripts\python.exe src\evaluate\build_error_analysis.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

### Số liệu `test` chuẩn (`evaluation/metrics_summary.csv`, `n=160`, `evidence_den=144`, `refusal_den=16`)

| Run | R@5 | R@10 | MRR@5 | ctxR@5 | citeP@top1 | period | numeric | exact | refP | refR |
|---|---|---|---|---|---|---|---|---|---|---|
| E0 | 0.0764 | 0.125 | 0.0502 | 0.0764 | 0.0417 | 0.3036 | 0.0 | 0.0 | 0.0 | 0.0 |
| E1 | 0.0417 | 0.0903 | 0.022 | 0.0296 | 0.0139 | 0.4286 | 0.0 | 0.0 | 0.0 | 0.0 |
| E2 | 0.1389 | 0.2083 | 0.065 | 0.1267 | 0.0208 | 0.4464 | 0.0 | 0.0 | 1.0 | 1.0 |
| E3 | 0.2361 | 0.4167 | 0.1142 | 0.2016 | 0.0556 | 0.5893 | 0.0 | 0.0 | 1.0 | 0.75 |
| E4 | 0.1944 | 0.2986 | 0.1082 | 0.1772 | 0.0625 | 0.6429 | 0.0 | 0.0 | 1.0 | 0.75 |
| E5 | 0.1458 | 0.2222 | 0.0642 | 0.135 | 0.0208 | 0.4464 | 0.0 | 0.0 | 1.0 | 0.75 |
| E6 | 0.1875 | 0.25 | 0.0785 | 0.1388 | 0.0278 | 0.4286 | 0.0 | 0.0 | 1.0 | 0.75 |
| E7 | 0.1458 | 0.2153 | 0.0734 | 0.1208 | 0.0347 | 0.4107 | 0.0 | 0.0 | 1.0 | 0.75 |
| E8 | **0.8611** | **0.8889** | **0.8507** | **0.849** | **0.8472** | **0.9821** | **0.8472** | **0.7847** | **1.0** | **1.0** |

Chỉ số bổ sung của **E8**:
- Trên **`test` (`n=160`)**: `MRR@10 = 0.8547`, `version_accuracy = 0.9821`, `page_accuracy = 0.8472`, `unsupported_claim_rate = 0.0`, `faithfulness_heuristic = 1.0`, `answer_relevancy_heuristic = 0.8625`, `false_answer_rate = 0.1375`.
- Trên **`dev` (`n=44`, `evidence_den=40`, `refusal_den=4`)**: `R@5 = 0.85`, `R@10 = 0.925`, `MRR@5 = 0.85`, `MRR@10 = 0.8602`, `numeric_match = 0.825`, `exact_match = 0.8`, `unsupported_claim_rate = 0.0`, `faithfulness_heuristic = 1.0`, `refusal_precision = 1.0`, `refusal_recall = 1.0`.

Chi tiết đầy đủ xem tại `evaluation/comparison_E0_E1_E2.md`, `evaluation/error_analysis.md`, và `evaluation/evaluation_protocol.md` (v9).

## 6. Chạy demo Streamlit (Financial Intelligence UI)

```powershell
.\.venv\Scripts\streamlit.exe run app\streamlit_app.py
```

Giao diện Streamlit thiết kế theo **Financial Intelligence** sử dụng chung `src/retrieval/table_lookup.py` + `app/qa_engine.py`:
- Header với 4 corpus chips (`4 doanh nghiệp`, `40 báo cáo`, `2.407 Chunks`, `29.615 Table Records`), thanh bên 13 câu mẫu chia 4 nhóm và 4 nút Preset nhanh.
- **Verdict Card** hiển thị trạng thái (`answered`, `partial_answer`, `refused`, `ambiguous`), đáp án, hộp phép tính/nguồn, thẻ `chunk_id` chứng cứ; lưới 4 **KPI thực thể** (`Doanh nghiệp`, `Năm tài chính`, `Phiên bản BCTC`, `Đơn vị & Chỉ tiêu`); và 2 tab (**Chứng cứ Top-K & Bảng số liệu gốc** với điểm chuẩn hóa `[0.0, 1.0]` và **CONTEXT gửi bộ sinh & Nhật ký truy hồi**).

Kiểm thử demo & unit test:

```powershell
.\.venv\Scripts\python.exe app\check_demo.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

4 ca trong `app/check_demo.py` đạt (refusal nguyên văn, đáp án kèm phép tính `10.8568 %`, snippet > 300 ký tự, paraphrase `10.8568 %`); kết quả mẫu chi tiết xem tại `app/expected_outputs.md` và `app/README.md`.

## 7. Cấu trúc thư mục

```text
.
├── README.md                              # file này
├── data_card.md                           # hồ sơ dữ liệu chuẩn v4
├── requirements.txt                       # khóa phiên bản thư viện cốt lõi (.venv)
├── config/
│   ├── answer_policy.yaml                 # quy tắc trích dẫn & từ chối
│   ├── e0_bm25.yaml .. e8_table_lookup.yaml
├── data/
│   ├── README.md                          # cấu trúc thư mục dữ liệu (204 gold, 29615 table records)
│   ├── data_manifest.csv                  # 244 dòng (40 báo cáo + 44 dev + 160 test)
│   ├── data_schema.md                     # lược đồ dữ liệu v4
│   ├── raw/vifinqa/                       # snapshot ViFinQA cục bộ (không commit Git)
│   ├── processed/                         # chunks (2407), table_records (29615), matched (35), dropped (977), OCR audit
│   ├── annotations/                       # qa_gold.jsonl (204), review_log, review_report.md, guideline v0.2
│   └── splits/                            # dev (44), test (160), split_meta.json v4 seed 42
├── src/
│   ├── download_vifinqa.py                # tải ViFinQA
│   ├── select_corpus.py                   # chọn 40 báo cáo
│   ├── filter_questions.py                # lọc 35 câu khớp và 977 câu loại
│   ├── audit_ocr.py                       # audit OCR
│   ├── build_chunks.py                    # 2407 chunk theo trang
│   ├── build_table_records.py             # 29615 bản ghi số từ bảng HTML
│   ├── build_supplement_gold.py           # 15 câu bổ sung
│   ├── build_gold.py                      # 50 câu gold v1 (có guard --force-v1)
│   ├── build_expanded_gold_v2.py          # 127 câu gold v2
│   ├── build_expanded_gold_v3.py          # 200 câu gold v3
│   ├── resolve_vifinqa_and_dev_refusal.py # hoàn thiện 35 ViFinQA + 4 DEV-REF -> 204 câu v4
│   ├── cross_review.py                    # hậu kiểm chéo phân tầng (53/204 = 25.98%, 57/204 cumulative)
│   ├── build_data_docs.py                 # manifest và kiểm tra split
│   ├── data_quality_report.py             # sinh report/data_quality_report.md
│   ├── preprocess/                        # normalize, chunking, company match, parser, table_extract
│   ├── retrieval/                         # bm25.py, pipeline_two_stage.py, table_lookup.py, answer_policy.py
│   ├── infer/                             # e0_bm25 .. e8_table_lookup (lưu top-10 predicted_chunk_ids)
│   └── evaluate/                          # evaluate, compare_runs, seed_check_e1, build_error_analysis, pilot_advanced, generate_charts, build_report_docx
├── tests/                                 # 35 unit test (test_answer_policy, test_evaluate, test_table_lookup, test_qa_engine)
├── evaluation/
│   ├── evaluation_protocol.md             # giao thức chấm v9 và chống rò rỉ (split v4)
│   ├── experiments.csv                    # bảng tracking E0-E8
│   ├── metrics_summary.csv                # metric dev (n=44) và test (n=160)
│   ├── comparison_E0_E1_E2.md             # bảng so sánh E0-E8 do script sinh
│   ├── error_analysis.md                  # 12 ca lỗi Form B
│   ├── pilot_advanced.md                  # kết quả pilot nâng cao
│   ├── dev_predictions/                   # dự đoán dev E0-E8
│   ├── test_predictions/                  # dự đoán test E0-E8
│   ├── refusal_labels/                    # nhãn refusal chi tiết E0-E8
│   └── split_freeze.json                  # bản sao split v4 đã khóa
├── app/
│   ├── README.md                          # hướng dẫn demo Streamlit
│   ├── streamlit_app.py                   # giao diện Financial Intelligence
│   ├── qa_engine.py                       # engine chia sẻ với table_lookup
│   ├── sample_questions.jsonl             # 13 câu mẫu
│   ├── check_demo.py                      # kiểm thử 4 ca
│   └── expected_outputs.md                # kết quả mẫu kiểm chứng
└── report/
    ├── figures/                           # biểu đồ trực quan & UI (01..11_*.png)
    ├── Bao_cao_BTL.md                     # báo cáo học phần chuẩn mẫu Đại Nam (Markdown nguồn)
    ├── Bao_cao_BTL.docx                   # báo cáo Word có bìa mẫu, TOC, Hình/Bảng tự động
    ├── Bao_cao_BTL.pdf                    # bản PDF xuất trực tiếp từ Word (.docx)
    ├── data_quality_report.md             # chất lượng dữ liệu
    ├── corpus_selection.md                # lựa chọn corpus
    └── ocr_audit.md                       # audit OCR
```

## 8. Hồ sơ nộp và kiểm chứng

- `data_card.md`: hồ sơ dữ liệu chuẩn `v4` đủ 14 mục theo Mục 7 Hướng dẫn BTL (40 báo cáo, 2.407 chunks, 29.615 table records, split `v4`, hậu kiểm 57/204 `reviewed-agree`, OCR audit, giấy phép `unknown_verify_with_teacher`, giới hạn).
- `report/Bao_cao_BTL.md`, `report/Bao_cao_BTL.docx`, `report/Bao_cao_BTL.pdf`: báo cáo học phần hoàn chỉnh theo mẫu báo cáo (2 trang bìa chuẩn, Lời nói đầu, Mục lục tự động, Bảng từ viết tắt, Chương 1-3, Kết luận 3 đoạn và Tài liệu tham khảo `[1]..[9]`), sinh tự động từ `src/evaluate/build_report_docx.py`.
- `report/data_quality_report.md`, `report/corpus_selection.md`, `report/ocr_audit.md`: kiểm định chất lượng dữ liệu, tiêu chí chọn corpus và audit OCR.
- `report/figures/`: `01_corpus_ocr_overview.png` .. `11_streamlit_ui_context_and_trace.png` (`10_pipeline_and_error_taxonomy.png` minh họa kiến trúc và phân rã lỗi; `11_streamlit_ui_context_and_trace.png` chụp tab CONTEXT và nhật ký truy hồi trên `ViFinQA-97`).
- `evaluation/pilot_advanced.md`: báo cáo pilot nâng cao sinh bởi `src/evaluate/pilot_advanced.py`.
- `requirements.txt` đã khóa đúng phiên bản `.venv`, không phụ thuộc thư viện nặng dư thừa, không lộ API key hay PII.
