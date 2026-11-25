# Demo hỏi đáp báo cáo tài chính có trích dẫn (Mục 6.1)

Demo Streamlit là pipeline RAG thuần, không đọc thuộc gold: nhận câu hỏi
-> trích metadata -> BM25 cộng điểm metadata công ty và năm (`[0.0, 1.0]`)
-> lookup & tổng hợp có cấu trúc trên `table_records.jsonl` (qua `src/retrieval/table_lookup.py`, gồm cả so sánh/chênh lệch T2/T3)
-> ghép top-k chunks thành CONTEXT có citation -> bộ sinh đáp án offline chỉ dùng CONTEXT theo
`config/answer_policy.yaml` và `src/retrieval/answer_policy.py`. Gold chỉ dùng offline để chấm điểm.

## Cài đặt

```bash
conda activate NLP
pip install -r requirements.txt
```

(Chạy trong môi trường Anaconda đã kích hoạt bằng `conda activate nlp_rag`; pipeline chạy hoàn toàn offline trên CPU, không tải mô hình ngoài.) Dữ liệu đọc từ `data/processed/chunks.jsonl` (`2407` chunk, 1 chunk = 1 trang) và `data/processed/table_records.jsonl` (`29615` bản ghi bảng).

## Chạy Streamlit (tương tác trên trình duyệt)

```bash
streamlit run app/streamlit_app.py
```

Trình duyệt mở địa chỉ do Streamlit in ra, thường là `http://localhost:8501`.
Giao diện theo hệ thống thiết kế **Financial Intelligence (Cobalt Navy / Slate / Amber)** gồm:

1. **Header & Corpus Chips**: hiển thị phạm vi 4 doanh nghiệp (`HPG`, `HSG`, `NKG`, `MSR`), 40 báo cáo (2020–2024), `2.407` chunks, `29.615` table records.
2. **Thanh nhập câu hỏi & Bộ câu mẫu thanh bên**: nhập câu hỏi trực tiếp hoặc bấm chọn nhanh trong danh sách 13 câu mẫu chia 4 nhóm ở thanh bên trái.
3. **Verdict Card (Trạng thái & Đáp án)**: pill trạng thái (`answered`, `partial_answer`, `refused`, `ambiguous` kèm `source`, `citation_complete`, `reason`), đáp án số chuẩn hóa, hộp phép tính/nguồn bảng, thẻ `chunk_id` chứng cứ và cảnh báo mâu thuẫn ngữ cảnh (nếu có).
4. **Lưới 4 KPI Thực thể đã trích**: `Doanh nghiệp`, `Năm tài chính`, `Phiên bản BCTC`, `Đơn vị & Chỉ tiêu`.
5. **2 Tab Chi tiết**:
   - **Tab `Chứng cứ Top-K & Bảng số liệu gốc`**: danh sách thẻ chunk kèm điểm chuẩn hóa `[0.0, 1.0]`, tài liệu gốc, đơn vị trang, đoạn highlight số liệu, bảng trích xuất `table_records.jsonl` (kèm nút xem toàn bộ bảng), và tùy chọn `Hiển thị toàn văn trang OCR` từ thanh bên.
   - **Tab `CONTEXT gửi bộ sinh & Nhật ký truy hồi`**: hiển thị đầy đủ chuỗi CONTEXT có trích dẫn được nạp cho bộ sinh (hoặc thông báo quy tắc từ chối nếu kích hoạt refusal).

## Kịch bản demo

1. **Câu hỏi số liệu (`S_NEW_01` đến `S_NEW_07`)**: pipeline tổng hợp đáp án trực tiếp từ `table_lookup` + BM25, kèm phép tính và `chunk_id` chứng cứ (ví dụ `S_NEW_07` sinh `10.8568 %`).
2. **Câu thiếu bằng chứng (`S_NEW_08` đến `S_NEW_10`)**: hệ thống kích hoạt refusal gating trả đúng nguyên văn `Không đủ bằng chứng trong corpus để trả lời.` với 0 chunk giả.
3. **Câu diễn đạt lại (`PARA_01`: `Biên lợi nhuận gộp của Hoa Sen năm 2024 bao nhiêu phần trăm?`)**: pipeline trích đúng `HSG` + `2024` + `consolidated` và sinh `10.8568 %` từ `HSG_2024_consolidated#p009`.
4. **Câu ViFinQA (`ViFinQA-97`, `ViFinQA-99`)**: ưu tiên lọc đơn vị tương thích (`%` so với `VND`) hoặc tra cứu bảng cân đối kế toán kèm kiểm chứng trong tab Chứng cứ.

## Dữ liệu mẫu và kiểm thử

- `app/sample_questions.jsonl`: 13 câu mẫu (7 trả lời được, 3 thiếu bằng chứng, 1 diễn đạt lại, 2 ViFinQA).
- `app/expected_outputs.md`: kết quả mẫu thực tế từ `app/qa_engine.py`.
- Kiểm thử demo 4 ca: `python app/check_demo.py`
- Kiểm thử unit test toàn bộ `qa_engine` & `table_lookup`: `python -m unittest discover -s tests -v`
