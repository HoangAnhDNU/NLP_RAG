# Demo hỏi đáp báo cáo tài chính có trích dẫn (Mục 6.1)

Demo Streamlit là pipeline RAG thuần, không đọc thuộc gold: nhận câu hỏi
-> trích metadata -> BM25 cộng điểm metadata công ty và năm
-> lookup có cấu trúc trên `table_records.jsonl` -> ghép top-k chunks thành
CONTEXT có citation -> bộ sinh đáp án offline chỉ dùng CONTEXT theo
`config/answer_policy.yaml`. Quy tắc từ chối dùng đúng 10 mẫu trong
`config/e2_hybrid.yaml`. Gold chỉ dùng offline để chấm điểm.

## Cài đặt

```bash
conda activate NLP
pip install pyyaml streamlit
```

Không cần tải thêm mô hình. Dữ liệu đọc từ `data/processed/chunks.jsonl`
(2407 chunk, 1 chunk bằng 1 trang).

## Chạy Streamlit (tương tác trên trình duyệt)

```bash
conda activate NLP
streamlit run app/streamlit_app.py
```

Trình duyệt mở địa chỉ do Streamlit in ra, thường là `http://localhost:8501`.
Nhập câu hỏi, chỉnh top-k ở thanh bên, bấm Hỏi để xem mạch ra quyết định đủ 7 mục:
1. câu hỏi người dùng; 2. thực thể trích (công ty, năm, bản báo cáo, đơn vị hỏi, chỉ tiêu đoán từ bảng);
3. trạng thái refusal và quyết định (`answered`, `partial_answer`, `refused`, `ambiguous` kèm lý do);
4. top evidence chunks với đoạn highlight số liệu và từ khóa;
5. đường dẫn tài liệu gốc (`local_path :: document_id trang N`) và số trang;
6. cảnh báo mâu thuẫn khi top-1 lệch công ty/năm/bản được hỏi;
7. nút Xem bảng gốc đầy đủ lấy từ `table_records.jsonl` (metric, mã số, năm, giá trị thô, đơn vị, trang).
Tick chọn Hiện toàn văn chunk để đọc hết văn bản.
Thanh bên có 13 câu mẫu chia 4 nhóm: 7 câu sinh đáp án từ pipeline,
3 câu thiếu bằng chứng, 1 câu diễn đạt lại, 2 câu ViFinQA.
Bấm nút câu mẫu để nạp nguyên văn vào ô hỏi đáp.

## Kịch bản demo

1. Câu hỏi số liệu (`S_NEW_01` đến `S_NEW_07`): pipeline sinh đáp án trực tiếp
từ CONTEXT (lookup bảng trước, BM25 sau), kèm phép tính và chunk chứng cứ,
cùng top-k nguồn gồm doanh nghiệp, năm,
phiên bản báo cáo, trang và `chunk_id` kèm điểm số.
Ví dụ `S_NEW_07` sinh 10.8568 % kèm phép tính biên gộp.
2. Câu thiếu bằng chứng (`S_NEW_08` đến `S_NEW_10`): hệ thống trả đúng nguyên văn
`Không đủ bằng chứng trong corpus để trả lời.`
3. Câu diễn đạt lại (ví dụ `Biên lợi nhuận gộp của Hoa Sen năm 2024 bao nhiêu phần trăm?`):
pipeline sinh trực tiếp 10.8568 % từ chunk `HSG_2024_consolidated#p009`,
không đi tắt qua gold. Khi pipeline không chắc chắn mới hiện gợi ý câu gần nhất.
4. Câu ViFinQA (`ViFinQA-97`, `ViFinQA-99`): pipeline sinh từ bảng nếu khớp;
nếu không khớp chắc chắn mới liệt kê
số ứng viên trong đoạn liên quan, truy hồi đúng vùng công ty và năm
để đối chiếu thủ công.
Mẹo: tick Hiện toàn văn chunk trên Streamlit để đọc hết văn bản
thay vì đoạn liên quan 1200 ký tự.

## Dữ liệu mẫu và kiểm thử

- `app/sample_questions.jsonl`: 13 câu mẫu (7 trả lời được, 3 thiếu bằng chứng, 1 diễn đạt lại, 2 ViFinQA).
- `app/expected_outputs.md`: kết quả mẫu đã chạy ngày 2026-11-10.
- Kiểm thử đầu vào và đầu ra: `python app/check_demo.py`
(script chạy 4 ca: từ chối, sinh đáp án từ pipeline, đoạn trích dài, diễn đạt lại).
