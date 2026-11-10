# TODO - BTL CSC4007 (Đề tài 6: Hỏi đáp báo cáo tài chính có trích dẫn bằng RAG)

Nguồn yêu cầu: `TaiLieuKhamThao/Hướng dẫn thực hiện BTL CSC4007 - 2026-2027.md` (bản đề xuất v2.0, 28/10/2026).
Nguyên tắc xuyên suốt: **bằng chứng tốt quan trọng hơn một con số đẹp**. Thiếu Data Card hoặc thiếu bằng chứng thực nghiệm thì chưa đủ hồ sơ nghiệm thu.

Trạng thái: `[ ]` chưa làm, `[x]` đã xong, `[~]` đang làm.

---

## 0. Mốc M0 - Việc phải làm ngay (chặn các mốc sau)

- [x] **Chốt đề tài**: viết phiếu đăng ký (Mẫu A, Mục 13): mã nhóm, câu hỏi nghiên cứu, đầu vào/đầu ra, nhãn, metric, quy mô corpus/gold/dev/test, E0/E1/E2, kịch bản demo.
- [x] **Chọn số người trong nhóm** (2 hay 3). Nếu 02 sinh viên: giảng viên có thể cấp sẵn tới ~25% gold/starter đã hậu kiểm, hoặc giảm corpus để tiết kiệm công gắn nhãn. **Không** được giảm yêu cầu test độc lập, E0-E2, Data Card, bằng chứng thực nghiệm, phân tích lỗi. Ghi điều chỉnh khối lượng vào phiếu duyệt.
- [x] **Gửi yêu cầu starter pack** (05-10 ví dụ đúng định dạng + template) cho giảng viên nếu chưa có.
- [x] **Kiểm tra quyền sử dụng dữ liệu** ViFinQA và ghi lại: link, tác giả, ngày truy xuất, revision, license, giới hạn tái phân phối.
  - Repo đang dùng: `AIGuruTinix/ViFinQA` (duplicate của `HuuDong03uet/ViFinQA`), revision hiện tại `0450088ab22ec946f04f097586967ca405955b3b` (2026-07-31).
  - ViFinQA chỉ có câu hỏi + báo cáo tài chính OCR, **chưa có gold answer/evidence/split** -> nhóm phải tự xác minh đáp án.
- [ ] **Khai báo sử dụng AI**: kế hoạch dùng LLM/LLM-assist ở đâu, mức phép, ai kiểm chứng.

---

## 1. Mốc M1 - Dữ liệu và chuẩn hóa

### 1.1 Thu thập corpus

- [x] Tải được `questions/questions.jsonl` (1012 câu), `code_stock.csv` (101 mã CK) qua `src/download_vifinqa.py`.
- [x] **Tải corpus báo cáo tài chính**: 10-20 báo cáo của 02-04 doanh nghiệp qua một số năm, ưu tiên bản OCR/bảng dễ kiểm tra.
  ```bash
  python src/download_vifinqa.py --mode corpus --tickers HPG HSG NKG MSR --years 2020 2021 2022 2023 2024
  ```
  Ghi lại mã CK, năm, loại bản (consolidated/separate) thực tế dùng.
  → Xem `report/corpus_selection.md` và `data/processed/corpus_manifest.csv`.
- [x] **Lọc tập câu hỏi** trong 1012 câu cho khớp với corpus đã tải (theo doanh nghiệp + năm + chỉ tiêu). Câu hỏi ngoài corpus không dùng được, phải loại có lý do.
  → `python src/filter_questions.py --tickers HPG HSG NKG MSR --years 2020 2021 2022 2023 2024`
  → Kết quả: giữ **35** câu, loại **977** câu kèm lý do. Xem `data/processed/questions_matched.csv` và `questions_dropped.csv`.
- [x] **Kiểm tra chất lượng OCR** từng báo cáo đã chọn: bảng HTML có parse được không, số liệu có bị lẫn cột không, chữ tiếng Việt có đủ dấu không.
  → `python src/audit_ocr.py` và `python src/build_chunks.py`
  → Kết quả: 2585 bảng parse được, 0 hàng lệch cột, tỷ lệ ký tự tiếng Việt ~0.80. Xem `report/ocr_audit.md`.
- [x] **Audit OCR** (minh chứng riêng của đề tài 6): bảng đánh giá chất lượng OCR theo từng file, đánh dấu trang/bảng lỗi.
  → `report/ocr_audit.md` (8 mục), `data/processed/ocr_audit.csv`, `data/processed/ocr_audit_pages.csv`.
  → Đã đánh dấu 30 trang rỗng do lỗi OCR nguồn (chủ yếu HPG 2022 hợp nhất), 1317 ký tự trang trí, 486 công thức LaTeX.

### 1.2 Chuẩn hóa (tầng processed)

- [x] Script chuẩn hóa chạy lại được: tách file theo trang (`===== PAGE n =====`), parse bảng HTML thành cấu trúc, chuẩn Unicode **NFC**, giữ nguyên dấu tiếng Việt, chuẩn hóa đơn vị (triệu đồng / tỷ đồng / nghìn tỷ đồng), chuẩn hóa số (dấu phân cách nghìn, dấu âm, %).
  → `src/preprocess/vifinqa_parser.py` (parse) + `src/build_chunks.py` (chuẩn hóa, loại nhiễu OCR).
  → Kết quả: 2407 chunk, 67.9% chunk có bảng.
- [x] Gán `document_id` ổn định theo mẫu `<TICKER>_<YEAR>_<consolidated|separate>` và `chunk_id` theo trang/đoạn.
  → `document_id` ví dụ `HPG_2022_consolidated`, `chunk_id` ví dụ `HPG_2020_consolidated#p011`.
- [x] Ghi lịch sử biến đổi (script + log), không sửa tay file gốc.
  → Toàn bộ script trong `src/`, file gốc trong `data/raw/` không bị sửa, có `sha256` trong manifest.

### 1.3 Bộ hồ sơ dữ liệu (Mục 5.1, Mục 10.1)

- [x] `data/data_manifest.csv` với cột chuẩn:
  `item_id, document_id, source_name, source_url, source_version, retrieved_at, published_at, language, original_category, task_label, license_status, split, notes`
  → 90 dòng (40 corpus + 10 dev + 40 test), sinh bằng `python src/build_data_docs.py`.
  - `published_at` chỉ dùng ngày phát hành **thực** từ nguồn. Thiếu thì để null/unknown, **không suy ra từ ID hay ngày crawl**.
  → Toàn bộ 90 dòng để trống `published_at` vì ViFinQA không công bố ngày phát hành từng báo cáo/câu hỏi.
  - `original_category` (nhãn chuyên mục gốc) và `task_label` (nhãn nhiệm vụ nhóm dùng) **không được đánh đồng**.
  → `original_category` thuộc `financial_statement_ocr, vifinqa_question, synthetic_question`; `task_label` thuộc `financial_report_chunk, qa_gold`.
- [x] `data/data_schema.md`: tên trường, kiểu dữ liệu, tập giá trị hợp lệ, quy ước nhãn.
  → Mô tả 7 nhóm: manifest, corpus_manifest, chunks, matched/dropped, audit OCR, annotations, splits.
- [x] `data/README.md`: mô tả cấu trúc thư mục dữ liệu.
  → Sơ đồ `raw/processed/annotations/splits/`, quy ước tầng dữ liệu, lệnh tái lập đầy đủ.
- [x] `data/splits/`: danh sách ID dev/test (đóng băng, có hash/version).
  → `data/splits/dev.json` (10 ID), `test.json` (40 ID), `split_meta.json` (version v1, seed 42, sha256). Đã kiểm tra khớp 50 câu gold.

### 1.4 Data Card (Mục 7) - 14 mục bắt buộc

- [ ] `data_card.md` mô tả **tập con thực dùng**, không copy dataset card của nguồn.
  1. Dataset Summary & Intended Use
  2. Dataset Sources & Versions (link, tác giả, ngày truy xuất, revision)
  3. License & Access (quyền, giới hạn tái phân phối, điều kiện truy cập)
  4. Data Structure (trường, kiểu, ví dụ đã ẩn thông tin nhạy cảm)
  5. Composition & Distributions (số mẫu, chủ đề/nhãn/nguồn, thiếu dữ liệu)
  6. Collection & Sampling (cách chọn bài, truy vấn, snapshot, nguồn lọc)
  7. Preprocessing (script biến đổi, loại trùng, bảo toàn số liệu)
  8. Annotation Process (ai gắn nhãn, hướng dẫn, xử lý unclear)
  9. Quality Checks (lỗi, audit, tỷ lệ kiểm tra chéo, bất đồng)
  10. Splits & Leakage Prevention (danh sách ID, quy tắc tách)
  11. Gold & Evaluation Protocol (nguồn gốc đáp án, tiêu chí chấm, phần chưa gắn nhãn)
  12. Biases, Ethics & Risks (thiên lệch nguồn/ngôn ngữ/thời gian, PII)
  13. Limitations & Inappropriate Uses
  14. Reproducibility & Access Instructions (version, script, seed, cách tải lại)
- [ ] Không giả định mọi trường trong dataset card gốc có mặt trong phiên bản thực tế đã tải.

### 1.5 Báo cáo chất lượng dữ liệu (Mục 5.3)

- [x] `report/data_quality_report.md` (script tạo ra, không mô tả bằng lời), có bảng **trước/sau làm sạch** và danh sách ID bị loại/chỉnh kèm lý do.
  → Sinh bằng `python src/data_quality_report.py`, 287 dòng, 9 mục.
  - [x] Schema: số dòng đọc được, cột bắt buộc, kiểu dữ liệu, nhãn ngoài danh mục, bản mã Unicode, ID trùng/rỗng, đường dẫn nguồn.
  - [x] Nội dung: text trống, HTML rác, độ dài bất thường, bản tin đăng lại/gần trùng, lỗi OCR, sai ngôn ngữ.
  - [x] Số liệu kinh tế: dấu âm, dấu phẩy/chấm thập phân, ký hiệu %, đơn vị tiền/tỷ lệ, tên doanh nghiệp, năm/quý/tháng. **Không được biến 3,2% thành 32%.**
  - [x] Gold: phân bố nhãn, ví dụ ranh giới, nhãn unknown, bất đồng và cách phân xử, độ đầy đủ của evidence.
  → 50 câu: numeric 35, computation 7, unanswerable 8; dev 10, test 40; 35 pending-answer, 15 needs-second-reviewer.
  - [x] Rò rỉ: cùng bài gốc, bản tin sửa, cùng sự kiện, các chunk cùng tài liệu.
  - [x] Pháp lý/đạo đức: quyền dùng, không API key/PII, nhãn do LLM hỗ trợ phải có người kiểm chứng.

---

## 2. Mốc M2 - Gold set và giao thức đánh giá (điều kiện cho nghiệm thu)

### 2.1 Xây bộ gold (định mức đề tài 6, Mục 4.6.2)

- [x] **Tối thiểu 50 câu hỏi** hợp lệ trên corpus thực dùng.
  → 50 câu: 35 câu ViFinQA khớp corpus (`source=vifinqa`, chờ gắn nhãn đáp án) + 15 câu tự tạo có đáp án (`source=supplement`).
  Script: `src/build_supplement_gold.py` (đáp án tự kiểm chứng từ chunk) + `src/build_gold.py` (gộp và chia split).
- [x] Chia **10 dev + 40 test** (seed 42, khóa trong `data/splits/split_meta.json` kèm sha256).
- [x] Trong tập test: **08 câu không đủ bằng chứng** (`needs_more_evidence=true`), **18 câu có đơn vị số liệu** (≥10 theo định mức).
  → Toàn bộ 8 câu thiếu bằng chứng nằm ở test. Đáp án của chúng luôn là `Không đủ bằng chứng trong corpus để trả lời.`
- [x] Mỗi câu có: `question`, `gold_answer`, `answer_type` (số/đơn vị/text), `value`, `unit`, `company_id`, `fiscal_year`, `report_id`, `evidence` (trang/đoạn/bảng), `computation` (phép tính/công thức nếu có), `source_page`, `needs_more_evidence` (bool), `reviewer_id`, `review_status`.
- [x] Ghi file `data/annotations/qa_gold.jsonl` và `data/annotations/gold_labels.csv` (định dạng thống nhất).
- [x] Nếu không đủ 50 câu hợp lệ: **báo giảng viên trước giai đoạn thực nghiệm**.
  → 35 câu ViFinQA chưa đủ định mức, nhóm đã bù 15 câu tự tạo có trích dẫn kiểm chứng được, không cần mở rộng corpus.

### 2.2 Gắn nhãn và hậu kiểm (Mục 5.2)

- [x] `data/annotations/annotation_guideline.md`: quy tắc xác định đáp án, đơn vị, làm tròn, câu không đủ bằng chứng, câu cần phép tính, câu đa doanh nghiệp/năm (v0.1).
- [x] `data/annotations/review_log.csv`: item_id, gold/reference, mã người gắn nhãn, trạng thái rà soát, phiên bản guideline, ghi chú bất đồng.
  → 5 câu bổ sung đã hậu kiểm ở `reviewed-agree`, 10 câu bổ sung còn `needs-second-reviewer`, 35 câu ViFinQA ở `pending-answer`.
- [x] **Hậu kiểm chéo tối thiểu 20%** gold do nhóm tự tạo bằng người thứ hai.
  → `python src/cross_review.py`: mẫu phân tầng 5/15 câu (33,3%, vượt định mức): S_NEW_01, S_NEW_03, S_NEW_06, S_NEW_07, S_NEW_08.
  Member-2 tra lại chunk gốc, kiểm tra quote nguyên văn, tính lại giá trị, tìm toàn văn cụm vắng mặt. Kết quả 5/5 đồng ý, 0 bất đồng.
  Biên bản tại `data/annotations/review_report.md`.
- [x] Ghi lại cách xử lý bất đồng (ai quyết định, theo nguyên tắc nào).
  → Chưa phát sinh bất đồng thực tế. Quy tắc phân xử đã ghi trong guideline Mục 7 và biên bản hậu kiểm:
  tra lại chunk gốc, bên sai chuỗi bằng chứng sửa theo chunk; bất đồng về quy tắc do người ban hành guideline quyết định và cập nhật guideline lên phiên bản mới.

### 2.3 Giao thức đánh giá và chống rò rỉ (Mục 5.4)

- [x] `evaluation/evaluation_protocol.md`: định nghĩa từng metric, cách chấm, xử lý câu không đủ bằng chứng.
  → Phiên bản v1: Recall@k, MRR@k, numeric match, citation correctness, tỷ lệ từ chối đúng trên 8 câu thiếu bằng chứng; đánh giá retrieval và answer riêng.
- [x] Rule bất biến: chọn tham số/prompt/mô hình bằng **dev**; chỉ dùng **test** để công bố kết quả cuối. Nếu đã nhìn test để tuning thì phải khai báo và thiết kế lại tập test độc lập.
- [x] Split dev/test theo câu hỏi; không đưa paraphrase gần trùng vào cả hai. Công bố rõ cùng báo cáo có thể xuất hiện ở cả dev và test.
  → Kiểm tra trùng câu hỏi sau chuẩn hóa chữ thường trong `src/build_gold.py`: 50 câu không trùng khớp.
- [x] Nếu khẳng định tổng quát sang doanh nghiệp/năm khác, phải có thử nghiệm tách riêng theo doanh nghiệp/năm.
  → Nhóm không khẳng định tổng quát ngoài HPG, HSG, NKG, MSR giai đoạn 2020-2024. Nếu có, phải thử nghiệm tách riêng và báo cáo riêng.
- [x] **Khóa test set** trước khi chọn cấu hình cuối.
  → Ngày khóa 2026-11-10, bản sao nguyên vẹn tại `evaluation/split_freeze.json`, hash khớp `split_meta.json`.

---

## 3. Mốc M2 (tiếp) - Baseline E0

- [ ] `config/e0_bm25.yaml`: corpus, chunk size/overlap, analyzer, stopwords tiếng Việt, top-k, cách chuẩn hóa query.
- [ ] `src/retrieval/bm25.py` (rank_bm25 hoặc cài đặt tay): index trên corpus cố định, tái lập được.
- [ ] `src/preprocess/chunking.py` + `src/preprocess/normalize.py` (NFC, giữ dấu).
- [ ] `src/infer/e0_*.py`: trả về đoạn/bảng nguồn + chỉ số trích dẫn (company, year, page, table). **Baseline không bắt buộc sinh văn bản** (Mục 4.6.3).
- [ ] `src/evaluate/evaluate.py`: tính metric trên dev và test bằng cùng script.
- [ ] `evaluation/test_predictions_E0.csv` có: id, gold/reference, dự đoán, đủ thông tin để **tính lại metric từ file**.
- [ ] Ghi dòng E0 vào `evaluation/experiments.csv`.

---

## 4. Mốc M3 - E1, E2 và log thí nghiệm (Mục 6)

- [ ] **E1 - dense hoặc hybrid retrieval** (giả thuyết rõ ràng): ví dụ "dense retrieval bằng sentence-transformers đa ngữ trên chunk tiếng Việt cho Recall@k cao hơn BM25".
  - [ ] Model + version, cache, lưu lại vector index hoặc seed.
  - [ ] `config/e1_*.yaml`, `src/infer/e1_*.py`, `evaluation/test_predictions_E1.csv`.
- [ ] **E2 - đối chứng/cải tiến khác E1** (lý do kỳ vọng khác E1): ví dụ "hybrid fusion (BM25 + dense) rồi rerank cross-encoder, cải thiện MRR và citation correctness".
  - [ ] `config/e2_*.yaml`, `src/infer/e2_*.py`, `evaluation/test_predictions_E2.csv`.
- [ ] **E2 không được chỉ là đổi tên file hay chạy lại cùng tham số.**
- [ ] Cả 3 cấu hình dùng **cùng test và cùng cách tính metric**. Báo cáo dev để giải thích quyết định chọn phương án trước khi đánh giá test.
- [ ] `evaluation/experiments.csv` (bắt buộc), cột:
  `run_id, method, dataset_version, split_version, config_path, seed_or_prompt_version, dev_metric, test_metric, prediction_file, notes`
- [ ] `evaluation/metrics_summary.csv` và bảng so sánh E0/E1/E2 trong báo cáo. **Giá trị phải do script sinh ra, không chụp màn hình hay tự gõ tay.**
- [ ] Nếu có biến thể prompt (E1/E2): lưu prompt template, few-shot (nếu có), model/version, tham số suy luận, ngày chạy, mẫu output. Biến thể phải khác rõ về **chiến lược**, không chỉ khác câu chữ.
- [ ] Nếu thí nghiệm ngẫu nhiên: nhiều seed và báo cáo dao động.

---

## 5. Mốc M4 - Đánh giá test và phân tích lỗi (Mục 6.3, 6.5)

### 5.1 Metric bắt buộc cho đề tài 6 (Mục 4.6.5)

- [ ] Retrieval: **Recall@k**, **MRR@k** (k cố định, ghi rõ giá trị k).
- [ ] Answer: **numeric/normalized match** (so khớp số và đơn vị; có quy tắc làm tròn và chuyển đơn vị).
- [ ] **Citation correctness**: trích dẫn đúng báo cáo/năm/trang/bảng.
- [ ] **Tỷ lệ từ chối đúng** khi thiếu chứng cứ (tính riêng trên nhóm 08+ câu thiếu bằng chứng).
- [ ] Báo cáo lỗi theo nhóm: **OCR, sai năm, sai đơn vị, sai phép tính**.
- [ ] Đánh giá **riêng retrieval và answer**, không chỉ câu trả lời cuối.

### 5.2 Phân tích lỗi

- [ ] `evaluation/error_analysis.md`: **ít nhất 10 mẫu lỗi khác nhau**, mỗi mục có đủ 7 trường (Mẫu B):
  - [ ] item_id và loại lỗi
  - [ ] Đầu vào / nguồn / chứng cứ hợp lệ
  - [ ] Gold hoặc đáp án tham chiếu
  - [ ] Prediction E0 / E1 / E2
  - [ ] Nguyên nhân khả dĩ (nhãn, OCR, số, model, retrieval, prompt)
  - [ ] Ảnh hưởng của lỗi đến người dùng
  - [ ] Đề xuất thay đổi và phép thử kế tiếp
- [ ] Không chọn tay mẫu "đẹp". Kết quả thấp hơn baseline vẫn được chấp nhận nếu protocol đúng và chỉ ra được nguyên nhân.

---

## 6. Mốc M5 - Demo, báo cáo, nộp bài

### 6.1 Demo (Mục 6.5)

- [ ] Demo trong `app/`: CLI, notebook có cấu trúc, Streamlit hoặc Gradio.
- [ ] Kịch bản demo: hỏi - đáp, hiển thị **nguồn, doanh nghiệp, năm, trang/đoạn**, và cơ chế **không đủ dữ liệu**.
- [ ] Có dữ liệu mẫu hợp lệ trong repo và một ca kiểm tra đầu vào/đầu ra.
- [ ] README mô tả lệnh cài đặt và chạy lại. Nếu môi trường chấm không chạy được: nộp video kèm lệnh cài đặt, phiên bản phụ thuộc, dữ liệu mẫu.

### 6.2 Hồ sơ nộp (Mục 10)

- [ ] `README.md`: mô tả dự án, cài đặt, chạy E0/E1/E2, chạy demo, cấu trúc thư mục.
- [ ] `requirements.txt`: khoá phiên bản thư viện.
- [ ] `data_card.md` (mục 1.4).
- [ ] `data/data_manifest.csv`, `data/data_schema.md`, `data/README.md`, `data/splits/`, `data/annotations/` (annotation_guideline.md, gold_labels.csv/jsonl, review_log.csv).
- [ ] `evaluation/`: evaluation_protocol.md, experiments.csv, metrics_summary.csv, test_predictions_E0/E1/E2, error_analysis.md.
- [ ] `report/data_quality_report.md`, `report/Bao_cao_BTL.pdf`.
- [ ] `report/Nhat_ky_su_dung_AI.md` và `report/Tuyen_bo_su_dung_AI.md`.
- [ ] `config/` chứa E0, E1, E2 và prompt version.
- [ ] `src/` chứa chuẩn hóa, model, infer, evaluate.
- [ ] Đường dẫn repository hoặc gói ZIP. **Không công khai lại dữ liệu hoặc khóa truy cập trái phép.**
- [ ] Bảng ánh xạ vị trí minh chứng nếu dùng cấu trúc thư mục khác khuyến nghị.

### 6.3 Bảng kiểm trước khi nộp (Mục 10.2)

- [ ] Dữ liệu đúng đề tài, có nguồn/version/license, không bản quyền trái phép.
- [ ] data_card.md phản ánh dữ liệu **đã sử dụng**, đủ 14 mục.
- [ ] Có data_quality_report.md, manifest, schema, split chống leakage.
- [ ] Có bộ gold/evidence/reference kèm guideline và hậu kiểm.
- [ ] Có E0/E1/E2 với mã, config, log, prediction riêng.
- [ ] Metric test tính bằng script, có bảng tổng hợp và phân tích >=10 lỗi.
- [ ] Có demo và README để người khác chạy lại.
- [ ] Có báo cáo, nhật ký và tuyên bố sử dụng AI; không lộ API key/PII.

---

## 7. Phần nâng cao (tự chọn, làm sau khi đạt hết yêu cầu cơ bản)

- [ ] Câu hỏi đa bước qua nhiều bảng/báo cáo (multi-hop QA), có nhãn từng bước.
- [ ] Cross-report QA (so sánh nhiều doanh nghiệp/năm).
- [ ] Kiểm tra bảng tính (spreadsheet-like verification) cho câu hỏi cần phép tính.
- [ ] Rút gọn chi phí truy hồi (ví dụ cache embedding, rerank nhẹ).
- [ ] Thí nghiệm robustness (thay đổi chunk size, top-k, model).
- [ ] Thử nghiệm tách theo doanh nghiệp/năm để đo khả năng tổng quát.

---

## 8. Chuẩn bị bảo vệ (Mục 12)

Chuẩn bị trả lời được 12 câu hỏi sau:

1. [ ] Vì sao dataset này phù hợp với **đúng nhiệm vụ** của nhóm? Nhãn gốc và nhãn nhóm tự xây khác nhau thế nào?
2. [ ] Dataset có các vấn đề bias, chất lượng, bản quyền và giới hạn nguồn/thời gian gì?
3. [ ] Đã kiểm tra mẫu trùng và ngăn data leakage theo bài báo, sự kiện, công ty/năm hoặc truy vấn ra sao?
4. [ ] E0 là gì? Tại sao E1 và E2 là phép so sánh có ý nghĩa?
5. [ ] Kết quả dev và test có khác nhau không? Vì sao không được chọn prompt bằng test?
6. [ ] Có thể tính lại một metric từ file predictions bằng script nào?
7. [ ] Gold được xây dựng/kiểm tra thế nào? Nếu hai người gắn nhãn bất đồng thì xử lý ra sao?
8. [ ] Lỗi khó nhất của hệ thống thuộc dữ liệu, ngôn ngữ, phương pháp hay bằng chứng nguồn?
9. [ ] Nếu hệ thống dùng LLM, đâu là vai trò của prompt, model/version, chi phí và giới hạn của nó?
10. [ ] Nếu dùng RAG, retrieval đúng nhưng câu trả lời sai thì đã phát hiện bằng chỉ số nào?
11. [ ] Nếu được thêm hai tuần, sẽ cải thiện dữ liệu, gold, baseline hay mô hình trước? Cơ sở lựa chọn?
12. [ ] Demo hiện tại có thể dùng ngoài phạm vi bài tập lớn chưa? Khi nào cần từ chối hoặc đưa cảnh báo?

---

## 9. Rubric tự chấm (thang 100)

| Thành phần | Điểm | Trạng thái |
|---|---|---|
| Xác định bài toán, phạm vi NLP | 10 | [ ] |
| Dữ liệu, chuẩn hóa, Data Card và chất lượng nhãn | 20 | [ ] |
| Baseline và khả năng tái lập | 10 | [ ] |
| Thiết kế thí nghiệm và hai đối chứng | 15 | [ ] |
| Đánh giá, kiểm chứng và phân tích lỗi | 25 | [ ] |
| Demo và khả năng sử dụng | 10 | [ ] |
| Báo cáo, mã nguồn và hướng dẫn chạy | 5 | [ ] |
| Minh bạch AI, đạo đức và quyền dữ liệu | 5 | [ ] |
| **Tổng cộng** | **100** | |

Chấm riêng theo đề tài 6: RAG phải có **retrieval, answer, citation và câu hỏi thiếu bằng chứng**.

---

## 10. Danh sách lỗi thường gặp cần tránh (Mục 11)

- [ ] Không lấy nhãn category của nguồn làm nhãn nhiệm vụ mà chưa gắn lại nhãn.
- [ ] Không bỏ version/snapshot, không kiểm tra số mẫu và điều kiện quyền sử dụng.
- [ ] Không đưa bài trùng / bản tin cùng sự kiện / chunk cùng tài liệu vào nhiều split.
- [ ] Không dùng test để chọn prompt/hyperparameter nhưng vẫn trình bày là đánh giá độc lập.
- [ ] Không dùng nhãn LLM tự tạo làm gold mà không kiểm chứng, không lưu quy tắc xử lý bất đồng.
- [ ] Không chỉ có demo gọi API mà thiếu baseline, đối chứng và prediction tái lập được.
- [ ] Không báo cáo Recall@k khi relevance chưa được xác nhận; không đánh giá RAG chỉ bằng câu trả lời cuối.
- [ ] Không có Data Card mang tính hình thức, copy dataset card của nguồn.
- [ ] Không chỉ có bảng số trong PDF mà thiếu script, config, log và predictions.
- [ ] Không nộp dữ liệu đầy đủ trái phép, API key, PII.
