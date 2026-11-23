# Cấu trúc thư mục dữ liệu

## Tổng quan

```text
data/
├── README.md              # file này: mô tả cấu trúc thư mục dữ liệu
├── data_manifest.csv      # bản kê chuẩn 13 cột (Mục 5.1, 10.1): 40 báo cáo + 204 câu gold
├── data_schema.md         # lược đồ: tên trường, kiểu, tập giá trị, quy ước nhãn
├── raw/
│   └── vifinqa/           # snapshot ViFinQA cục bộ (chỉ đọc, không commit git; tải bằng download_vifinqa.py)
│       ├── questions/questions.jsonl   # 1012 câu hỏi gốc
│       ├── code_stock.csv              # 101 mã chứng khoán
│       ├── README.md                   # readme của nguồn
│       └── financial_statements/       # báo cáo OCR theo <TICKER>/<YEAR>/<bản>/
│           └── HPG|HSG|NKG|MSR/2020-2024/
│               └── *_extracted.txt     # OCR có thẻ <table>, mốc trang ===== PAGE n =====
├── processed/             # dữ liệu đã chuẩn hóa, tái lập bằng script trong src/
│   ├── corpus_manifest.csv      # 40 báo cáo thực dùng (sha256, số trang, số ký tự)
│   ├── chunks.jsonl             # 2407 chunk, mỗi dòng một trang đã chuẩn NFC
│   ├── table_records.jsonl      # 29615 bản ghi số từ 2585 bảng HTML
│   ├── questions_matched.csv    # 35 câu ViFinQA khớp corpus
│   ├── questions_dropped.csv    # 977 câu bị loại kèm lý do
│   ├── ocr_audit.csv            # audit OCR theo file
│   └── ocr_audit_pages.csv      # audit OCR theo trang
├── annotations/           # gold và hồ sơ gắn nhãn
│   ├── annotation_guideline.md  # guideline v0.2
│   ├── qa_gold_supplement.jsonl # 15 câu tự tạo có đáp án kiểm chứng
│   ├── qa_gold.jsonl            # 204 câu gold v4 (35 ViFinQA + 15 bổ sung + 150 table-clean + 4 dev-refusal; 0 pending-answer)
│   ├── gold_labels.csv          # bản CSV gọn để chấm thủ công (204 dòng)
│   ├── review_log.csv           # trạng thái hậu kiểm từng item (204 dòng)
│   └── review_report.md         # báo cáo hậu kiểm chéo phân tầng (53 mẫu v4 = 25.98%; 57/204 = 27.94% reviewed-agree)
└── splits/                # split đã đóng băng
    ├── dev.json           # 44 ID dev (40 trả lời được + 4 dev-refusal)
    ├── test.json          # 160 ID test (giữ nguyên hoàn toàn từ v3, gồm 16 câu từ chối)
    └── split_meta.json    # seed 42, version v4, hash sha256
```

## Quy ước tầng dữ liệu

- `raw/`: snapshot cục bộ tải từ Hugging Face (`AIGuruTinix/ViFinQA`,
  revision `0450088ab22ec946f04f097586967ca405955b3b`), không commit lên Git. Không sửa tay.
- `processed/`: kết quả của `src/select_corpus.py`, `src/filter_questions.py`,
  `src/audit_ocr.py`, `src/build_chunks.py`, `src/build_table_records.py`. Chạy lại được, ghi đè toàn bộ.
- `annotations/`: kết quả của `src/build_supplement_gold.py`, `src/build_gold.py` (có guard `--force-v1`, từ chối ghi đè nếu `qa_gold.jsonl` đã có > 50 dòng), `src/build_expanded_gold_v2.py`, `src/build_expanded_gold_v3.py`, `src/resolve_vifinqa_and_dev_refusal.py` và `src/cross_review.py`.
  Toàn bộ **35** câu ViFinQA đã được giải kèm trích dẫn nguyên văn từ `chunks.jsonl` (`0` `pending-answer`); **57/204 (27.94%)** câu đạt `reviewed-agree` (`0` bất đồng).
- `splits/`: bản đóng băng `v4` theo Mục 10.1 (`dev=44` gồm 4 câu từ chối ngoài corpus `DEV-REF-01..04`; `test=160` giữ nguyên vẹn từ `v3` gồm 16 câu thiếu bằng chứng). Không dùng test để chọn prompt hay siêu tham số.

## Tái lập

```bash
python src/select_corpus.py --tickers HPG HSG NKG MSR --years 2020 2021 2022 2023 2024 --versions consolidated separate
python src/filter_questions.py --tickers HPG HSG NKG MSR --years 2020 2021 2022 2023 2024
python src/audit_ocr.py
python src/build_chunks.py
python src/build_table_records.py
python src/build_supplement_gold.py
python src/build_gold.py --force-v1
python src/build_expanded_gold_v2.py
python src/build_expanded_gold_v3.py
python src/resolve_vifinqa_and_dev_refusal.py
python src/cross_review.py
python src/build_data_docs.py
python src/data_quality_report.py
```

`src/build_data_docs.py` sinh `data/data_manifest.csv` (244 dòng: 40 corpus + 204 gold)
và kiểm tra `data/splits/` khớp 204 câu gold (split `v4`).
