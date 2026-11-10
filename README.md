# Hỏi đáp báo cáo tài chính tiếng Việt có trích dẫn với RAG (CSC4007 Đề tài 6)

Repo thực hiện pipeline RAG khép kín trên báo cáo tài chính OCR tiếng Việt:
truy hồi theo trang, trích dẫn `company_id`, `fiscal_year`, `report_version`,
`page`, `chunk_id`, chấm retrieval và answer riêng, từ chối đúng nguyên văn
khi thiếu bằng chứng.

## 1. Dữ liệu và phạm vi

- Nguồn: `AIGuruTinix/ViFinQA`, revision `0450088ab22ec946f04f097586967ca405955b3b`.
- Corpus thực dùng: 4 mã HPG, HSG, NKG, MSR, giai đoạn 2020-2024,
  40 báo cáo gồm cả 2 bản `consolidated` và `separate`.
- Chunk: 2407 chunk trong `data/processed/chunks.jsonl`, 1 chunk bằng 1 trang,
  văn bản chuẩn NFC và giữ dấu tiếng Việt.
- Gold: 50 câu trong `data/annotations/qa_gold.jsonl`:
  35 câu ViFinQA ở trạng thái `pending-answer`,
  7 câu bổ sung `S_NEW_01` đến `S_NEW_07` đã có đáp án kiểm chứng kèm phép tính,
  8 câu thiếu bằng chứng `S_NEW_08` đến `S_NEW_10` và 5 câu tương tự
  có `needs_more_evidence=true` và đáp án đúng là
  `Không đủ bằng chứng trong corpus để trả lời.`
- Split: dev 10 câu, test 40 câu, seed 42, khóa tại
  `data/splits/split_meta.json`, bản sao nguyên vẹn tại
  `evaluation/split_freeze.json`. Toàn bộ 8 câu thiếu bằng chứng nằm ở test.
  Chỉ tuning trên dev, chỉ công bố số liệu cuối trên test.

## 2. Môi trường

Dùng conda env `NLP` trên Windows (PowerShell):

```bash
conda activate NLP
python -c "import sys, sklearn; print(sys.version); print(sklearn.__version__)"
```

Phiên bản đã kiểm chứng ngày 2026-11-10:

| Thư viện | Phiên bản |
|---|---|
| Python | 3.10.21 |
| scikit-learn | 1.7.2 |
| pandas | 2.3.3 |
| numpy | 2.2.6 |
| scipy | 1.15.3 |
| pyyaml | 6.0.3 |
| streamlit | 1.65.0 |
| torch | 2.14.0+cu130 |
| transformers | 5.17.0 |
| datasets | 5.0.1 |
| huggingface_hub | 1.30.0 |

Cài đặt:

```bash
conda activate NLP
pip install -r requirements.txt
pip install pyyaml streamlit
```

Mọi script đọc và ghi file bằng `encoding="utf-8"`.
Không dùng `conda run` để xem bảng tiếng Việt vì dễ gây mojibake.

## 3. Tái lập dữ liệu

Dữ liệu `raw` đã có sẵn trong repo nên có thể bỏ qua bước tải.
Nếu tải lại từ Hugging Face:

```bash
conda activate NLP
python src/download_vifinqa.py --mode questions
python src/download_vifinqa.py --mode corpus --tickers HPG HSG NKG MSR --years 2020 2021 2022 2023 2024
```

Dựng corpus, câu hỏi, chunk và gold:

```bash
conda activate NLP
python src/select_corpus.py --tickers HPG HSG NKG MSR --years 2020 2021 2022 2023 2024 --versions consolidated separate
python src/filter_questions.py --tickers HPG HSG NKG MSR --years 2020 2021 2022 2023 2024
python src/audit_ocr.py
python src/build_chunks.py
python src/build_supplement_gold.py
python src/build_gold.py
python src/build_data_docs.py
```

Kết quả chính: `data/processed/chunks.jsonl`,
`data/processed/questions_matched.csv` (35 câu khớp),
`data/processed/questions_dropped.csv` (977 câu loại),
`data/annotations/qa_gold.jsonl` (50 câu),
`data/data_manifest.csv`, `data/data_schema.md`, `data/README.md`.

## 4. Chạy E0, E1, E2 và E3 nâng cao

| Run | Phương pháp | Config | Ghi chú |
|---|---|---|---|
| E0 | BM25 unigram, `k1=1.5`, `b=0.75`, top 5 | `config/e0_bm25.yaml` | Baseline, không sinh văn bản |
| E1 | Dense LSA trên TF-IDF bigram, SVD 128, seed 42 | `config/e1_tfidf.yaml` | Đối chứng dense với BM25 |
| E2 | Hybrid `0.5 BM25 + 0.5 LSA` trên top 20, cộng 0.15 điểm metadata, 10 mẫu từ chối | `config/e2_hybrid.yaml` | Khác E1 ở chiến lược fusion và refusal |
| E3 | Lọc cứng metadata công ty/năm/bản rồi mới fusion `0.5 BM25 + 0.5 LSA`, 10 mẫu từ chối | `config/e3_filter.yaml` | Phần nâng cao: khác E2 ở lọc cứng pool trước khi fusion |

```bash
conda activate NLP
python src/infer/e0_bm25.py
python src/infer/e1_lsa.py
python src/infer/e2_hybrid.py
python src/infer/e3_filter.py
```

Mỗi lệnh sinh 2 file dev và test, ví dụ:

- `evaluation/dev_predictions_E0.csv`
- `evaluation/test_predictions_E0.csv`

## 5. Chấm metric và so sánh

Chấm bằng cùng một script `src/evaluate/evaluate.py`:

```bash
conda activate NLP
python src/evaluate/evaluate.py --run E0
python src/evaluate/evaluate.py --run E1
python src/evaluate/evaluate.py --run E2
python src/evaluate/evaluate.py --run E3
```

Mỗi lệnh ghi 2 dòng dev và test vào `evaluation/metrics_summary.csv`.
Chạy đủ 4 run để có 8 dòng E0, E1, E2, E3 rồi sinh bảng so sánh và phân tích lỗi:

```bash
conda activate NLP
python src/evaluate/compare_runs.py
python src/evaluate/seed_check_e1.py
python src/evaluate/build_error_analysis.py
```

Số liệu test hiện tại (`evaluation/metrics_summary.csv`, k=5, test n=40):

| run | recall@k | mrr@k | citation | numeric | refusal |
|---|---|---|---|---|---|
| E0 | 0.2 | 0.05 | 0.0 | 0.0 | 0.0 |
| E1 | 0.2 | 0.0667 | 0.0 | 0.0 | 0.0 |
| E2 | 0.4 | 0.14 | 0.0 | 0.0 | 1.0 |
| E3 | 0.8 | 0.45 | 0.2 | 0.0 | 1.0 |

Test chỉ có 5 câu có evidence nên mỗi câu đúng sai làm Recall@k nhảy 0.2,
đọc cùng `evaluation/comparison_E0_E1_E2.md` (đã gồm E3) và
`evaluation/error_analysis.md` (12 ca theo Form B) để tránh diễn giải quá mức.
E2 vượt E0/E1 ở refusal vì điền câu từ chối đúng nguyên văn; E3 vượt tiếp nhờ lọc cứng metadata.

## 6. Chạy demo Streamlit

```bash
conda activate NLP
streamlit run app/streamlit_app.py
```

Trình duyệt mở địa chỉ do Streamlit in ra, thường là `http://localhost:8501`.
Thanh bên có 13 câu mẫu chia 4 nhóm: 7 câu có đáp án kiểm chứng,
3 câu thiếu bằng chứng, 1 câu diễn đạt lại, 2 câu ViFinQA.
Bấm nút câu mẫu để nạp nguyên văn vào ô hỏi đáp.

Hành vi demo dùng chung `app/qa_engine.py`:

- Khớp nguyên văn 7 câu `S_NEW_01` đến `S_NEW_07`: trả đáp án kèm phép tính
  và `chunk_id` chứng cứ, ví dụ `S_NEW_07` trả `10.8568 %`.
- Câu ngoài corpus: trả đúng nguyên văn
  `Không đủ bằng chứng trong corpus để trả lời.`
- Câu còn lại: liệt kê số ứng viên trong đoạn liên quan, gợi ý 3 câu gold
  gần nhất, hiển thị top-k nguồn gồm công ty, năm, bản báo cáo, trang,
  `chunk_id`, điểm số và đoạn liên quan 1200 ký tự kèm nút xem toàn văn.

Kiểm thử demo:

```bash
conda activate NLP
python app/check_demo.py
```

4 ca đều đạt: từ chối đúng nguyên văn, trả lời kiểm chứng đúng công ty,
đoạn trích dài hơn 300 ký tự, câu diễn đạt lại được gợi ý `S_NEW_07`.
Kết quả mẫu xem tại `app/expected_outputs.md`, hướng dẫn chi tiết tại `app/README.md`.

## 7. Cấu trúc thư mục

```text
.
├── README.md                    # file này
├── requirements.txt             # khóa phiên bản thư viện
├── config/
│   ├── e0_bm25.yaml             # baseline BM25
│   ├── e1_tfidf.yaml            # dense LSA
│   ├── e2_hybrid.yaml           # hybrid và refusal
│   └── e3_filter.yaml           # lọc cứng metadata rồi fusion (nâng cao)
├── data/
│   ├── README.md                # cấu trúc thư mục dữ liệu
│   ├── data_manifest.csv        # 40 báo cáo và 50 câu gold
│   ├── data_schema.md           # lược đồ trường
│   ├── raw/vifinqa/            # snapshot ViFinQA, chỉ đọc
│   ├── processed/               # chunks, matched, dropped, audit OCR
│   ├── annotations/             # qa_gold, guideline, review log
│   └── splits/                  # dev, test, split_meta seed 42
├── src/
│   ├── download_vifinqa.py      # tải ViFinQA
│   ├── select_corpus.py         # chọn 40 báo cáo
│   ├── filter_questions.py      # lọc 35 câu khớp và 977 câu loại
│   ├── audit_ocr.py             # audit OCR
│   ├── build_chunks.py         # 2407 chunk theo trang
│   ├── build_supplement_gold.py # 15 câu bổ sung
│   ├── build_gold.py            # 50 câu gold và split
│   ├── build_data_docs.py       # manifest và schema
│   ├── preprocess/              # normalize, chunking, company match, parser
│   ├── retrieval/bm25.py        # BM25 dùng chung E0 và E2
│   ├── infer/                   # e0_bm25, e1_lsa, e2_hybrid, e3_filter
│   └── evaluate/                # evaluate, compare, seed check, error analysis
├── evaluation/
│   ├── evaluation_protocol.md   # giao thức chấm và chống rò rỉ
│   ├── experiments.csv          # bảng tracking E0 E1 E2 E3
│   ├── metrics_summary.csv      # metric dev và test
│   ├── comparison_E0_E1_E2.md   # bảng so sánh do script sinh (đã gồm E3)
│   ├── error_analysis.md        # 12 ca lỗi Form B
│   ├── dev_predictions_E*.csv   # dự đoán dev
│   ├── test_predictions_E*.csv  # dự đoán test
│   └── split_freeze.json        # bản sao split đã khóa
├── app/
│   ├── README.md                # hướng dẫn demo
│   ├── streamlit_app.py         # demo Streamlit
│   ├── qa_engine.py             # engine trả lời và gợi ý
│   ├── sample_questions.jsonl   # 13 câu mẫu
│   ├── check_demo.py            # kiểm thử 4 ca
│   └── expected_outputs.md      # kết quả mẫu
├── report/
│   ├── data_quality_report.md   # chất lượng dữ liệu
│   ├── corpus_selection.md      # lựa chọn corpus
│   ├── ocr_audit.md             # audit OCR
│   ├── Bao_cao_BTL.md           # báo cáo BTL 8 mục (nộp thay PDF)
│   ├── Nhat_ky_su_dung_AI.md    # nhật ký AI theo mốc
│   ├── Tuyen_bo_su_dung_AI.md   # tuyên bố AI
│   └── Bang_anh_xa_minh_chung.md # bảng ánh xạ Mục 10
└── TaiLieuKhamThao/
    ├── TODO.md                  # checklist mốc M1 đến M5
    └── Hướng dẫn thực hiện BTL CSC4007 - 2026-2027.md
```

## 8. Hồ sơ nộp đã đủ (Mục 10) và pilot nâng cao (Mục 7)

- `data_card.md` đủ 14 mục theo mục 1.4.
- `report/Bao_cao_BTL.md` 8 mục nộp thay PDF (bỏ bước PDF theo yêu cầu).
- `report/Nhat_ky_su_dung_AI.md`, `report/Tuyen_bo_su_dung_AI.md`.
- `report/Bang_anh_xa_minh_chung.md` ánh xạ 5 nhóm minh chứng.
- Pilot nâng cao `evaluation/pilot_advanced.md` do `src/evaluate/pilot_advanced.py` sinh:
  multi-hop ViFinQA-368, cross-report HSG và MSR 2024, kiểm bảng tính 3 mẫu khớp gold,
  BM25 khoảng 30 ms/câu, robustness R@1=0.20 R@3=0.60 R@5=0.80, tổng quát HPG 1/1 HSG 2/2 NKG 1/2.
- `requirements.txt` đã khóa đúng phiên bản ở mục 2, có thể đóng gói ZIP.
- Không công khai lại dữ liệu ngoài giấy phép, không lộ API key hay PII.
