# Kết quả mẫu đã chạy ngày 2026-11-10 (bản engine có trả lời)

Chạy bằng Streamlit (`streamlit run app/streamlit_app.py`) hoặc kiểm thử
`python app/check_demo.py` (môi trường NLP, không cần mô hình ngoài).
Thanh bên Streamlit có 13 câu mẫu; 3 ví dụ dưới đây minh họa 3 nhóm chính.

## 1. Câu có đáp án kiểm chứng (S_NEW_07)

Câu hỏi: Biên lợi nhuận gộp về bán hàng và cung cấp dịch vụ hợp nhất của CTCP Tập đoàn Hoa Sen trong năm tài chính kết thúc ngày 30/09/2024 là bao nhiêu phần trăm?

Trả lời: 10.8568 % (đáp án đã kiểm chứng)

Phép tính: Biên gộp = 4263666396467 / 39271893738448 x 100 = 10.8568% (làm tròn 4 chữ số thập phân).

Chunk chứng cứ: HSG_2024_consolidated#p009; HSG_2024_consolidated#p009

Top nguồn trích dẫn (top-5):

1. HSG 2024 separate trang 50 [HSG_2024_separate#p050] (điểm 37.7036)
2. HSG 2024 consolidated trang 52 [HSG_2024_consolidated#p052] (điểm 36.1945)
3. HSG 2020 consolidated trang 60 [HSG_2020_consolidated#p060] (điểm 34.7898)
4. HSG 2024 consolidated trang 9 [HSG_2024_consolidated#p009] (điểm 33.7794, trang gold)
5. HSG 2020 separate trang 60 [HSG_2020_separate#p060] (điểm 32.9347)

Nhận xét: chunk gold có mặt ở hạng 4, đúng công ty HSG. Top-1 sai phiên bản báo cáo (separate thay cho consolidated), khớp phân tích lỗi mục 5. Đoạn trích hiện là cửa sổ 1200 ký tự quanh từ khóa, kèm nút xem toàn văn trên Streamlit.

## 2. Câu thiếu bằng chứng (S_NEW_08)

Câu hỏi: Giá đóng cửa cổ phiếu HPG ngày 31/12/2024 là bao nhiêu đồng?

Trả lời đúng nguyên văn: `Không đủ bằng chứng trong corpus để trả lời.`

## 3. Câu diễn đạt lại (PARA_01)

Câu hỏi: Biên lợi nhuận gộp của Hoa Sen năm 2024 bao nhiêu phần trăm?

Hệ thống chưa trả đáp án ngay mà gợi ý `S_NEW_07` kèm điểm khớp khoảng 0.407.
Bấm nút gợi ý trên Streamlit để nạp nguyên văn câu hỏi và nhận đáp án kiểm chứng 10.8568 %.

## 4. Câu ViFinQA chưa có gold (ViFinQA-97)

Câu hỏi: Tỷ lệ sở hữu Công ty CP Gang thép Hòa Phát của HPG đến ngày 31/12/2023 là bao nhiêu %?

Trả lời: (chưa có đáp án kiểm chứng cho câu này)

Số ứng viên trong đoạn liên quan nhất và top-5 nguồn đúng vùng HPG 2023:

1. HPG 2023 separate trang 27 [HPG_2023_separate#p027] (điểm 34.1302)
2. HPG 2021 separate trang 30 [HPG_2021_separate#p030] (điểm 27.9924)
3. HPG 2023 consolidated trang 17 [HPG_2023_consolidated#p017] (điểm 27.3255)
4. HPG 2022 separate trang 27 [HPG_2022_separate#p027] (điểm 27.1939)
5. HPG 2020 separate trang 30 [HPG_2020_separate#p030] (điểm 26.6571)

Nhận xét: gold còn `pending-answer` nên demo chỉ liệt kê số ứng viên, người dùng đối chiếu thủ công.
