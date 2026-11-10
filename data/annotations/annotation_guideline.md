# Hướng dẫn gắn nhãn gold cho bộ câu hỏi RAG báo cáo tài chính (Đề tài 6)

Phiên bản: v0.1. Ngày ban hành: 2026-11-10. Người ban hành: member-1.

Tài liệu này là quy tắc duy nhất để xác định đáp án. Mọi nhãn gold đều phải
tuân thủ, mọi bất đồng đều phân xử theo thứ tự ưu tiên trong Mục 7.

## 1. Phạm vi và định mức

- Bộ gold tối thiểu 50 câu trên corpus thực dùng: HPG, HSG, NKG, MSR, giai đoạn
  2020-2024, hai bản hợp nhất và riêng.
- Chia 10 dev + 40 test. Trong test: ít nhất 08 câu không đủ bằng chứng,
  ít nhất 10 câu liên quan số liệu hoặc đơn vị.
- 35 câu lấy từ ViFinQA (khớp corpus bằng `src/filter_questions.py`), 15 câu tự
  tạo bằng `src/build_supplement_gold.py` (7 trả lời được, 8 thiếu bằng chứng).

## 2. Quy tắc xác định đáp án

1. Đáp án số chỉ lấy từ đúng ô bảng trong đúng báo cáo, đúng năm, đúng bản
   (hợp nhất hoặc riêng). Không dùng số ở cột năm khác, không dùng số của
   doanh nghiệp khác, không dùng số ở bản báo cáo khác.
2. Phạm vi "công ty mẹ" chỉ dùng bản `separate`. Phạm vi không ghi rõ hoặc chỉ
   tiêu hợp nhất dùng bản `consolidated`.
3. Chuỗi bằng chứng (`quote`) phải là nguyên văn dòng trong chunk, đủ để người
   thứ hai tìm lại đúng trang và đúng bảng.
4. Mỗi câu trả lời được phải có ít nhất một dòng bằng chứng chứa số đáp án và
   một dòng chứa đơn vị hoặc header năm.

## 3. Đơn vị

1. Đơn vị của câu hỏi ViFinQA gốc giữ nguyên như trong câu hỏi
   (triệu đồng, tỷ đồng, nghìn tỷ đồng, trăm tỷ đồng, %, lần).
2. Đơn vị trong báo cáo: `VND` nghĩa là đồng tuyệt đối, `Nghìn VND` nghĩa là
   nghìn đồng. Luôn quy đổi về đơn vị câu hỏi trước khi ghi `value`.
3. Không bao giờ đoán đơn vị của chunk để trống. Nếu không xác định được đơn vị
   trong trang, ghi chú vào `review_log.csv` và chuyển câu sang diện kiểm chứng.

## 4. Số và làm tròn

1. Số có dấu chấm phân cách nghìn trong OCR (ví dụ `91.279.041.771.826`) giữ
   nguyên khi trích, bỏ dấu chấm khi tính toán.
2. Số thập phân dấu phẩy (ví dụ `3,2`) chuyển thành `3.2`. Không nhân với 100.
3. Số âm trong ngoặc (ví dụ `(983.237)`) chuyển thành `-983237`.
4. Ký hiệu `%` giữ nguyên kèm dấu phần trăm.
5. Kết quả quy đổi đơn vị và tỷ lệ phần trăm làm tròn 4 chữ số thập phân.
6. Lãi cơ bản trên cổ phiếu ghi theo quy ước dấu chấm phân cách nghìn:
   ô `1.434` nghĩa là 1434 đồng.

## 5. Câu không đủ bằng chứng

1. Chỉ gắn `needs_more_evidence = true` khi chủ đề câu hỏi vắng mặt hoàn toàn
   trong toàn bộ corpus. Kiểm chứng bằng tìm kiếm toàn văn trong `chunks.jsonl`,
   không kiểm chứng bằng trí nhớ.
2. `gold_answer` của câu thiếu bằng chứng luôn là
   `Không đủ bằng chứng trong corpus để trả lời.`
3. Cấm dùng kiến thức ngoài corpus để trả lời câu thiếu bằng chứng.
4. Lý do thiếu bằng chứng ghi vào `unanswerable_reason`, nêu rõ chủ đề nào vắng
   mặt và đã kiểm tra bằng cụm từ nào.

## 6. Câu cần phép tính và câu đa doanh nghiệp

1. Câu cần phép tính phải ghi đầy đủ `computation`: công thức, số đầu vào và
   kết quả từng bước.
2. Câu đa doanh nghiệp phải có bằng chứng cho từng doanh nghiệp được nhắc tới,
   hoặc ghi rõ doanh nghiệp nào thiếu bằng chứng và xử lý theo Mục 5.
3. Câu so sánh nhiều năm phải lấy số cùng chỉ tiêu, cùng bản báo cáo cho mọi năm.

## 7. Xử lý bất đồng

1. Hậu kiểm chéo tối thiểu 20% số câu bởi người thứ hai.
2. Bất đồng về số hoặc đơn vị: người kiểm chứng tra lại chunk gốc, bên nào sai
   chuỗi bằng chứng thì sửa theo chunk.
3. Bất đồng về quy tắc (ví dụ đơn vị mơ hồ): ghi vào `review_log.csv`, quyết
   định cuối cùng thuộc về người ban hành guideline, và cập nhật guideline lên
   phiên bản mới thay vì sửa lẻ từng nhãn.
4. Không dùng nhãn do LLM tự tạo làm gold nếu chưa có người kiểm chứng.
   Nếu có LLM hỗ trợ, ghi rõ trong `review_log.csv` và nhật ký sử dụng AI.
