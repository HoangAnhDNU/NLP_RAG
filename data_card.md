# Data Card: tập con thực dùng cho RAG báo cáo tài chính tiếng Việt (Đề tài 6)

Phiên bản: v1. Ngày ban hành: 2026-11-10. Phạm vi: corpus, chunk và gold **thực tế dùng** trong repo này, không sao chép dataset card của nguồn.

## 1. Dataset Summary and Intended Use

Bài toán: hỏi đáp báo cáo tài chính tiếng Việt có trích dẫn bằng RAG. Đầu vào là câu hỏi tiếng Việt về chỉ tiêu trong báo cáo, đầu ra là đáp án số kèm trích dẫn `company_id`, `fiscal_year`, `report_version`, `page`, `chunk_id`. Mục đích sử dụng là nghiên cứu và chấm môn học CSC4007, không dùng cho tư vấn đầu tư. Phạm vi khẳng định chỉ trong 4 mã HPG, HSG, NKG, MSR giai đoạn 2020-2024. Ngoài phạm vi này hệ thống phải từ chối hoặc cảnh báo.

## 2. Dataset Sources and Versions

Nguồn duy nhất: `https://huggingface.co/datasets/AIGuruTinix/ViFinQA`, bản duplicate của `HuuDong03uet/ViFinQA`. Revision thực dùng: `0450088ab22ec946f04f097586967ca405955b3b`, snapshot ngày 2026-07-31, nhóm truy xuất ngày 2026-11-10 bằng `src/download_vifinqa.py`. Tập gốc gồm `questions/questions.jsonl` (1012 câu, chỉ có `id` và `question`), `code_stock.csv` (101 mã chứng khoán) và `financial_statements/<TICKER>/<YEAR>/*_extracted.txt` (OCR có thẻ `<table>`, mốc `===== PAGE n =====`). ViFinQA công khai **không có gold answer, không có evidence và không có split**, toàn bộ gold và split do nhóm tự xây trong `data/annotations/` và `data/splits/`.

## 3. License and Access

`license_status` trong `data/data_manifest.csv` ghi `unknown_verify_with_teacher` cho cả 90 dòng vì nguồn không công bố giấy phép tái phân phối. Nhóm không công khai lại file OCR gốc, chỉ công bố manifest kèm `sha256`, chunk đã xử lý và script tải lại bằng `huggingface_hub`. Dữ liệu là báo cáo tài chính công khai, không phát hiện PII và API key qua kiểm tra ở `report/data_quality_report.md` mục 7. Trước khi công bố ngoài môn học phải hỏi giảng viên về quyền sử dụng. Truy cập lại hợp lệ duy nhất là chạy `python src/download_vifinqa.py --mode corpus --tickers HPG HSG NKG MSR --years 2020 2021 2022 2023 2024` với revision nêu trên.

## 4. Data Structure

Bốn tầng, mọi file đọc và ghi bằng `encoding="utf-8"`, văn bản chuẩn NFC và giữ dấu tiếng Việt. Chi tiết kiểu và tập giá trị xem `data/data_schema.md`.

- `data/processed/corpus_manifest.csv` (40 dòng): một dòng một báo cáo, gồm `document_id` dạng `<TICKER>_<YEAR>_<consolidated|separate>`, `company_id`, `fiscal_year`, `report_version`, `local_path`, `n_pages`, `n_chars`, `sha256`.
- `data/processed/chunks.jsonl` (2407 dòng): một dòng một trang, gồm `chunk_id` dạng `<document_id>#p<NNN>`, ví dụ `HPG_2020_consolidated#p011`, `document_id`, `company_id`, `fiscal_year`, `report_version`, `page`, `n_tables`, `unit`, `text`, `text_chars`.
- `data/processed/questions_matched.csv` (35 dòng) và `questions_dropped.csv` (977 dòng): kết quả lọc 1012 câu theo corpus.
- `data/annotations/qa_gold.jsonl` (50 dòng): mỗi bản ghi gồm `question_id`, `question`, `gold_answer`, `answer_type` (`numeric`, `computation`, `unanswerable`), `value`, `unit`, `company_id`, `fiscal_year`, `report_id`, `evidence` (mỗi phần tử gồm `chunk_id`, `source_page`, `quote` nguyên văn), `computation`, `source_page`, `needs_more_evidence`, `reviewer_id`, `review_status`, `source`, `split`.
- `data/splits/dev.json` (10 ID), `test.json` (40 ID), `split_meta.json` (version v1, seed 42, sha256 `43276e350a9aa7555f139eb1c1ce192840fd9b84f4c7fa7cdff2ca480eb45f86`).

## 5. Composition and Distributions

Corpus: 40 báo cáo bằng 4 mã nhân 5 năm nhân 2 bản. Tổng 2437 trang OCR, loại 30 trang rỗng do lỗi nguồn, giữ 2407 chunk. Trong đó 1634 chunk có bảng (67,9%), 2585 bảng parse được, 0 hàng lệch cột. Phân bố đều theo thiết kế, MSR là báo cáo dài nhất (tới 151 trang một báo cáo). Gold: 50 câu gồm 35 câu ViFinQA ở `pending-answer` và 15 câu tự tạo `S_NEW_01` đến `S_NEW_15`. Trong đó 7 câu trả lời được có đáp án kiểm chứng (`S_NEW_01` đến `S_NEW_07`), 8 câu thiếu bằng chứng (`S_NEW_08` đến `S_NEW_15`), 35 câu ViFinQA chờ gắn nhãn. Theo `answer_type`: numeric 35, computation 7, unanswerable 8. Theo split: dev 10, test 40. Có 26 câu có đơn vị số liệu, 7 câu có evidence. Đơn vị gồm nghìn tỷ đồng 7, tỷ đồng 4, triệu đồng 3, phần trăm 3, đồng 1, trăm tỷ đồng 1, lần 7, rỗng 24. Thiếu dữ liệu lớn nhất: 35/50 câu chưa có đáp án nên metric answer và citation hiện chỉ phản ánh 7 câu bổ sung và 8 câu từ chối.

## 6. Collection and Sampling

Không thu thập mới ngoài ViFinQA. Cách chọn corpus ghi tại `report/corpus_selection.md`: xếp hạng theo mật độ câu hỏi khớp, cùng ngành phi tài chính dùng chung mẫu Thông tư 202/2014/TT-BTC, chất lượng OCR parse được. Đã cân nhắc và loại các cấu hình HPG HSG NKG MSR 2020-2025 (24 báo cáo, vượt định mức), thêm DCM (25 báo cáo), nhóm ngân hàng VCB ACB (chỉ 9 câu khớp). Lọc câu hỏi bằng `src/filter_questions.py`: ưu tiên mã CK trong ngoặc, rồi mã viết tắt, rồi tên công ty theo chuỗi từ liên tiếp để tránh nhầm tên gần giống. Kết quả giữ 35, loại 977 kèm lý do từng dòng. 15 câu tự tạo bù định mức 50 theo 3 mẫu: tra cứu trực tiếp trong bảng, so sánh hai năm hoặc hai doanh nghiệp, câu thiếu bằng chứng về giá thị trường, quý và kế hoạch. Snapshot và ngày truy xuất ghi ở mục 2, toàn bộ file gốc giữ nguyên trong `data/raw/`.

## 7. Preprocessing

Chuỗi tái lập: `select_corpus.py` rồi `filter_questions.py` rồi `audit_ocr.py` rồi `build_chunks.py` rồi `build_supplement_gold.py` rồi `build_gold.py` rồi `build_data_docs.py`. Biến đổi chính trong `src/preprocess/vifinqa_parser.py` và `src/build_chunks.py`: tách file theo `===== PAGE n =====`, parse bảng HTML thành cấu trúc, chuẩn NFC, giữ dấu, loại 1317 ký tự trang trí và 486 công thức LaTeX, loại 30 trang rỗng, chuẩn hóa số (bỏ chấm phân cách nghìn khi tính, đổi phẩy thập phân thành chấm, ngoặc thành số âm, giữ `%`), suy đơn vị theo header bảng rồi dự phòng theo văn bản trang, chunk để rỗng nếu không xác định được đơn vị. Quy ước 1 chunk bằng 1 trang, overlap 0, `chunk_id` ổn định. Không sửa tay file gốc, lịch sử biến đổi là script cộng log, mỗi báo cáo có `sha256` trong manifest để kiểm lại.

## 8. Annotation Process

Người gắn nhãn: member-1 đặt 15 câu bổ sung bằng `src/build_supplement_gold.py`, đáp án trích từ ô bảng đúng báo cáo, đúng năm và đúng bản, quote nguyên văn để tra lại. Quy tắc duy nhất là `data/annotations/annotation_guideline.md` v0.1: phân biệt consolidated và separate theo phạm vi công ty mẹ, chỉ lấy ô đúng năm, quy đổi đơn vị về đơn vị câu hỏi và làm tròn 4 chữ số thập phân, câu thiếu bằng chứng phải tìm toàn văn trong `chunks.jsonl` trước khi gắn. Xử lý unclear: chunk thiếu đơn vị thì ghi vào `review_log.csv` và chuyển sang diện kiểm chứng, không đoán. Người hậu kiểm: member-2 kiểm chéo 5/15 câu (33,3%, vượt định mức 20%) gồm S_NEW_01, S_NEW_03, S_NEW_06, S_NEW_07, S_NEW_08, tra lại chunk gốc và tính lại giá trị, biên bản tại `data/annotations/review_report.md`, kết quả 5/5 đồng ý và 0 bất đồng. Quy tắc phân xử bất đồng tại guideline mục 7: tra lại chunk gốc, bên sai chuỗi bằng chứng sửa theo chunk, bất đồng về quy tắc do người ban hành guideline quyết định và nâng phiên bản guideline.

## 9. Quality Checks

Ba lớp kiểm tra, tất cả do script sinh ra. Lớp schema trong `report/data_quality_report.md` mục 1: 6 file kiểm tra 0 ID trùng và 0 ID rỗng, nhãn trong danh mục, mọi `local_path` tồn tại, mọi `report_id` của 15 câu bổ sung khớp manifest. Lớp nội dung và số liệu mục 2 và 3: 803/2437 trang không bảng được giữ vì chứa thuyết minh, 966 số phân cách nghìn, 615 số thập phân dấu phẩy và 1145 ký hiệu `%` được chuẩn hóa không nhân 100, đơn vị chunk gồm đồng 478, triệu đồng 142, tỷ đồng 107 và rỗng 1680. Lớp OCR tại `report/ocr_audit.md` (8 mục) và `data/processed/ocr_audit*.csv`: tỷ lệ ký tự tiếng Việt khoảng 0,80, 0 hàng lệch cột, ký tự thay thế 0, 30 trang rỗng đã đánh dấu theo từng `document_id` và số trang. Hậu kiểm gold: 5 câu reviewed-agree, 10 câu bổ sung needs-second-reviewer, 35 câu ViFinQA pending-answer, toàn bộ 50 dòng theo dõi tại `review_log.csv`.

## 10. Splits and Leakage Prevention

Dev 10 câu, test 40 câu, seed 42, version v1, khóa ngày 2026-11-10, hash khớp giữa `data/splits/split_meta.json` và `evaluation/split_freeze.json`. Toàn bộ 8 câu thiếu bằng chứng nằm ở test, dev chỉ gồm câu trả lời được. Tách theo câu hỏi, kiểm tra paraphrase gần trùng bằng chuẩn hóa chữ thường toàn câu trong `src/build_gold.py`, 50 câu không trùng khớp. Mỗi chunk thuộc đúng một trang nên không tách chunk qua hai split. Công bố rõ cùng một báo cáo có thể xuất hiện ở cả dev và test vì corpus dùng chung cho mọi câu hỏi, đây là đặc trưng của QA trên báo cáo tài chính. Bản consolidated và separate của cùng công ty năm là hai tài liệu khác nhau, giữ cả hai và phân biệt bằng `report_version`. Từ sau mốc khóa, mọi thay đổi split phải đổi version. Quy tắc bất biến: chỉ tuning trên dev, chỉ công bố số liệu cuối trên test.

## 11. Gold and Evaluation Protocol

Nguồn gốc đáp án: 7 câu bổ sung do nhóm trích từ chunk và tính lại, 35 câu ViFinQA chưa gắn nhãn ở `pending-answer`. Tiêu chí chấm tại `evaluation/evaluation_protocol.md` v1 bằng cùng script `src/evaluate/evaluate.py`: Recall@k và MRR@k theo `chunk_id` (k bằng 5), citation đúng khi top-1 chunk nằm trong evidence gold, numeric match sau chuẩn hóa số và quy đổi đơn vị với làm tròn 4 chữ số thập phân, refusal đúng khi trả đúng nguyên văn `Không đủ bằng chứng trong corpus để trả lời.` trên 8 câu `needs_more_evidence=true`. Retrieval và answer chấm riêng, trường hợp retrieval đúng nhưng answer sai thể hiện qua R@k cao kèm numeric thấp. Phần chưa gắn nhãn: 35 câu ViFinQA có `gold_answer` rỗng và `evidence` rỗng nên recall hiện chỉ tính trên 5 câu test có evidence, mỗi câu đúng sai làm Recall@k nhảy 0,2, đọc cùng `evaluation/comparison_E0_E1_E2.md` và `evaluation/error_analysis.md` (12 ca theo Mẫu B, đủ 4 nhóm OCR, sai năm, sai đơn vị, sai phép tính).

## 12. Biases, Ethics and Risks

Thiên lệch nguồn: chỉ 4 mã ngành thép và vật liệu giai đoạn 2020-2024 nên không khẳng định sang ngân hàng, doanh nghiệp khác hoặc năm khác. Thiên lệch ngôn ngữ: toàn bộ là tiếng Việt giữ dấu, tokenizer và stopwords tiếng Việt trong `config/e0_bm25.yaml` có thể kém trên câu hỏi song ngữ. Thiên lệch thời gian: thiếu 2025 và thiếu quý, mọi câu hỏi quý, bán niên, kế hoạch và giá thị trường đều thiếu bằng chứng theo thiết kế. Rủi ro đạo đức: đáp án sai đơn vị tiền (ví dụ nhầm nghìn đồng với tỷ đồng) có thể gây hiểu lầm tài chính, demo luôn hiển thị chunk chứng cứ và đoạn trích để đối chiếu thủ công. Không có PII, không có API key, nhãn LLM không dùng làm gold nếu chưa có người kiểm chứng. Quyền tái phân phối chưa xác minh nên không công khai lại dữ liệu gốc.

## 13. Limitations and Inappropriate Uses

Dữ liệu không chứng minh được: tỷ lệ sở hữu và số dư chi tiết của 35 câu ViFinQA vì chưa gắn nhãn, mọi câu hỏi giá đóng cửa, vốn hóa, quý, bán niên, kế hoạch và dự báo vì chủ đề vắng mặt hoàn toàn trong corpus, và mọi khẳng định ngoài HPG, HSG, NKG, MSR 2020-2024. Không dùng hệ thống để tư vấn đầu tư, không dùng retrieval đúng một mình để khẳng định đáp án đúng vì citation hiện bằng 0,0 ở cả 3 runs, không dùng test để chọn tham số rồi trình bày như đánh giá độc lập. OCR còn 30 trang rỗng và 803 trang không bảng nên câu hỏi thuần văn bản có thể thiếu nguồn. Đơn vị tiền là điểm lỗi lớn nhất, phải quy đổi thủ công khi chunk để đơn vị rỗng.

## 14. Reproducibility and Access Instructions

Phiên bản: dataset `0450088ab22ec946f04f097586967ca405955b3b`, split v1 seed 42, guideline v0.1, protocol v1, code tại commit hiện hành của repo này. Môi trường: conda env `NLP` (Python 3.10.21, scikit-learn 1.7.2, pandas 2.3.3, numpy 2.2.6, scipy 1.15.3, PyYAML 6.0.3, streamlit 1.65.0), cài bằng `pip install -r requirements.txt`. Tái lập dữ liệu: `select_corpus.py` rồi `filter_questions.py` rồi `audit_ocr.py` rồi `build_chunks.py` rồi `build_supplement_gold.py` rồi `build_gold.py` rồi `build_data_docs.py` với đúng ticker, năm và bản nêu ở mục 6. Tái lập thí nghiệm: `python src/infer/e0_bm25.py`, `python src/infer/e1_lsa.py`, `python src/infer/e2_hybrid.py`, rồi `python src/evaluate/evaluate.py --run E0` (lặp cho E1, E2), `python src/evaluate/compare_runs.py`, `python src/evaluate/seed_check_e1.py`, `python src/evaluate/build_error_analysis.py`. Tái lập demo: `streamlit run app/streamlit_app.py` và `python app/check_demo.py` (4 ca đều đạt). Mọi script đọc và ghi bằng `encoding="utf-8"`, không dùng `conda run` để xem bảng tiếng Việt.
