# Demo hỏi đáp báo cáo tài chính có trích dẫn (Mục 6.1)

Demo Streamlit dùng truy hồi BM25 kết hợp điểm cộng metadata công ty và năm
(bản nhẹ của E2 để chạy nhanh mọi máy, không cần scikit-learn).
Quy tắc từ chối dùng đúng 10 mẫu trong `config/e2_hybrid.yaml`.

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
Nhập câu hỏi, chỉnh top-k ở thanh bên, bấm Hỏi để xem đáp án,
phép tính (nếu có), top nguồn gồm doanh nghiệp, năm, phiên bản báo cáo,
trang, `chunk_id` và đoạn trích 1200 ký tự.
Tick chọn Hiện toàn văn chunk để đọc hết văn bản.
Thanh bên có 13 câu mẫu chia 4 nhóm: 7 câu có đáp án kiểm chứng,
3 câu thiếu bằng chứng, 1 câu diễn đạt lại, 2 câu ViFinQA.
Bấm nút câu mẫu để nạp nguyên văn vào ô hỏi đáp.

## Kịch bản demo

1. Câu có đáp án kiểm chứng (`S_NEW_01` đến `S_NEW_07`): hệ thống trả đáp án
kèm phép tính và chunk chứng cứ, cùng top-k nguồn gồm doanh nghiệp, năm,
phiên bản báo cáo, trang và `chunk_id` kèm điểm số.
Ví dụ `S_NEW_07` trả 10.8568 % kèm phép tính biên gộp.
2. Câu thiếu bằng chứng (`S_NEW_08` đến `S_NEW_10`): hệ thống trả đúng nguyên văn
`Không đủ bằng chứng trong corpus để trả lời.`
3. Câu diễn đạt lại (ví dụ `Biên lợi nhuận gộp của Hoa Sen năm 2024 bao nhiêu phần trăm?`):
hệ thống chưa trả đáp án ngay mà gợi ý `S_NEW_07` kèm điểm khớp.
Bấm nút gợi ý để nạp nguyên văn câu hỏi và nhận đáp án kiểm chứng.
4. Câu ViFinQA (`ViFinQA-97`, `ViFinQA-99`): chưa có gold nên hệ thống liệt kê
số ứng viên trong đoạn liên quan, truy hồi đúng vùng công ty và năm
để đối chiếu thủ công.
Mẹo: tick Hiện toàn văn chunk trên Streamlit để đọc hết văn bản
thay vì đoạn liên quan 1200 ký tự.

## Dữ liệu mẫu và kiểm thử

- `app/sample_questions.jsonl`: 13 câu mẫu (7 trả lời được, 3 thiếu bằng chứng, 1 diễn đạt lại, 2 ViFinQA).
- `app/expected_outputs.md`: kết quả mẫu đã chạy ngày 2026-11-10.
- Kiểm thử đầu vào và đầu ra: `python app/check_demo.py`
(script chạy 4 ca: từ chối, trả lời kiểm chứng, đoạn trích dài, gợi ý câu gần nhất).
