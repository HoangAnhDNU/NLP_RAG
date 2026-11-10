# Cấu trúc thư mục dữ liệu

## Tổng quan

```text
data/
├── README.md              # file này: mô tả cấu trúc thư mục dữ liệu
├── data_manifest.csv      # bản kê chuẩn 13 cột (Mục 5.1, 10.1): 40 báo cáo + 50 câu gold
├── data_schema.md         # lược đồ: tên trường, kiểu, tập giá trị, quy ước nhãn
├── raw/
│   └── vifinqa/           # snapshot ViFinQA, chỉ đọc, không sửa
│       ├── questions/questions.jsonl   # 1012 câu hỏi gốc
│       ├── code_stock.csv              # 101 mã chứng khoán
│       ├── README.md                   # readme của nguồn
│       └── financial_statements/       # báo cáo OCR theo <TICKER>/<YEAR>/<bản>/
│           └── HPG|HSG|NKG|MSR/2020-2024/
│               └── *_extracted.txt     # OCR có thẻ <table>, mốc trang ===== PAGE n =====
├── processed/             # dữ liệu đã chuẩn hóa, tái lập bằng script trong src/
│   ├── corpus_manifest.csv      # 40 báo cáo thực dùng (sha256, số trang, số ký tự)
│   ├── chunks.jsonl             # 2407 chunk, mỗi dòng một trang đã chuẩn NFC
│   ├── table_records.jsonl      # 29834 bản ghi số từ 2585 bảng HTML
│   ├── questions_matched.csv    # 35 câu ViFinQA khớp corpus
│   ├── questions_dropped.csv    # 977 câu bị loại kèm lý do
│   ├── ocr_audit.csv            # audit OCR theo file
│   └── ocr_audit_pages.csv      # audit OCR theo trang
├── annotations/           # gold và hồ sơ gắn nhãn
│   ├── annotation_guideline.md  # guideline v0.1
│   ├── qa_gold_supplement.jsonl # 15 câu tự tạo có đáp án kiểm chứng
│   ├── qa_gold.jsonl            # 50 câu gold thống nhất (35 ViFinQA + 15 bổ sung)
│   ├── gold_labels.csv          # bản CSV gọn để chấm thủ công
│   └── review_log.csv           # trạng thái hậu kiểm từng item
└── splits/                # split đã đóng băng
    ├── dev.json           # 10 ID dev
    ├── test.json          # 40 ID test
    └── split_meta.json    # seed 42, version v1, hash sha256
```

## Quy ước tầng dữ liệu

- `raw/`: dữ liệu gốc từ Hugging Face (`AIGuruTinix/ViFinQA`,
  revision `0450088ab22ec946f04f097586967ca405955b3b`). Không sửa tay.
- `processed/`: kết quả của `src/select_corpus.py`, `src/filter_questions.py`,
  `src/audit_ocr.py`, `src/build_chunks.py`, `src/build_table_records.py`. Chạy lại được, ghi đè toàn bộ.
- `annotations/`: kết quả của `src/build_supplement_gold.py` và `src/build_gold.py`.
  35 câu ViFinQA đang ở trạng thái `pending-answer`, 15 câu bổ sung đã có đáp án
  và chờ người thứ hai hậu kiểm.
- `splits/`: bản đóng băng theo Mục 10.1. Toàn bộ 8 câu thiếu bằng chứng nằm ở
  test. Không dùng test để chọn prompt hay siêu tham số.

## Tái lập

```bash
conda activate NLP
python src/select_corpus.py --tickers HPG HSG NKG MSR --years 2020 2021 2022 2023 2024 --versions consolidated separate
python src/filter_questions.py --tickers HPG HSG NKG MSR --years 2020 2021 2022 2023 2024
python src/audit_ocr.py
python src/build_chunks.py
python src/build_table_records.py
python src/build_supplement_gold.py
python src/build_gold.py
python src/build_data_docs.py
```

`src/build_data_docs.py` sinh `data/data_manifest.csv` (90 dòng: 40 corpus + 50 gold)
và kiểm tra `data/splits/` khớp 50 câu gold.
