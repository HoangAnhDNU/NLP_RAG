# Kết quả mẫu đã chạy ngày 2026-11-10 (bản engine RAG thuần)

Chạy bằng Streamlit (`streamlit run app/streamlit_app.py`) hoặc kiểm thử
`python app/check_demo.py` (môi trường NLP, không cần mô hình ngoài).
Thanh bên Streamlit có 13 câu mẫu; 4 ví dụ dưới đây minh họa pipeline mới.
Pipeline: câu hỏi -> trích metadata -> BM25 + điểm metadata ->
lookup bảng -> ghép CONTEXT -> bộ sinh offline chỉ dùng CONTEXT theo
`config/answer_policy.yaml` (không đọc thuộc gold).
Màn hình kết quả giữ đúng 7 mục: 1. câu hỏi, 2. thực thể trích,
3. trạng thái refusal, 4. top evidence highlight, 5. đường dẫn gốc và số trang,
6. cảnh báo mâu thuẫn, 7. nút xem bảng gốc từ `table_records.jsonl`
(kèm khung xem CONTEXT đã ghép).

## 1. Câu hỏi số liệu đầy đủ (S_NEW_07)

Câu hỏi: Biên lợi nhuận gộp về bán hàng và cung cấp dịch vụ hợp nhất của CTCP Tập đoàn Hoa Sen trong năm tài chính kết thúc ngày 30/09/2024 là bao nhiêu phần trăm?

Trả lời sinh từ pipeline (không đọc thuộc gold): 10.8568 %

Phép tính: Biên gộp = 4.263.666.396.467 đồng / 39.271.893.738.448 đồng x 100 = 10.8568 %.

Chunk chứng cứ: HSG_2024_consolidated#p009; HSG_2024_consolidated#p009

Top nguồn trích dẫn (chunk chứng cứ được chèn lên top-1 để CONTEXT hiển thị đúng nguồn đã dùng):

1. HSG 2024 consolidated trang 9 [HSG_2024_consolidated#p009] (điểm 999.0, chunk chứng cứ)
2. HSG 2024 consolidated trang 12 [HSG_2024_consolidated#p012]
3. HSG 2024 separate trang 44 [HSG_2024_separate#p044]
4. HSG 2024 consolidated trang 45 [HSG_2024_consolidated#p045]
5. HSG 2024 separate trang 39 [HSG_2024_separate#p039]

Nhận xét: đáp án sinh trực tiếp từ lookup bảng + BM25, không đọc thuộc gold. CONTEXT gồm 5 chunks có citation được ghép trước khi sinh. Đoạn trích là cửa sổ 1200 ký tự quanh từ khóa, kèm nút xem toàn văn trên Streamlit.

## 2. Câu thiếu bằng chứng (S_NEW_08)

Câu hỏi: Giá đóng cửa cổ phiếu HPG ngày 31/12/2024 là bao nhiêu đồng?

Trả lời đúng nguyên văn: `Không đủ bằng chứng trong corpus để trả lời.`

## 3. Câu diễn đạt lại (PARA_01)

Câu hỏi: Biên lợi nhuận gộp của Hoa Sen năm 2024 bao nhiêu phần trăm?

Trả lời sinh từ pipeline (không đi tắt qua gold): 10.8568 %.

Phép tính: Biên gộp = 4.263.666.396.467 đồng / 39.271.893.738.448 đồng x 100 = 10.8568 %.

Nhận xét: câu ngắn gọn vẫn trích đúng HSG 2024 consolidated và sinh cùng đáp án với câu đầy đủ, chứng tỏ pipeline dùng bảng chứ không khớp nguyên văn gold. Khi pipeline không chắc chắn mới hiện gợi ý câu gần nhất để chạy lại.

## 4. Câu ViFinQA (ViFinQA-97)

Câu hỏi: Tỷ lệ sở hữu Công ty CP Gang thép Hòa Phát của HPG đến ngày 31/12/2023 là bao nhiêu %?

Trả lời sinh từ pipeline: 99.988 %.

Phép tính: 99,988% (ô bảng, đơn vị %) = 99.988 %. Nguồn HPG_2023_separate#p027 trang 27.

Nhận xét: pipeline ưu tiên ô bảng cùng đơn vị % nên không còn nhầm sang giá gốc VND. CONTEXT gồm 5 chunks đúng vùng HPG, top-1 là chunk chứng cứ. Câu ViFinQA còn lại (ViFinQA-99) sinh 948.3035 tỷ đồng từ NKG_2022_consolidated#p008 theo cùng đường lookup.
