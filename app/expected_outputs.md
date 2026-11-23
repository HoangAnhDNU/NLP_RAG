# Kết quả mẫu đã kiểm chứng trên `app/qa_engine.py` (v4, ngày 2026-11-15)

Chạy tương tác bằng Streamlit (`.venv\Scripts\streamlit.exe run app/streamlit_app.py`) hoặc kiểm thử tự động:

```bash
.venv\Scripts\python.exe app/check_demo.py
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Pipeline dùng chung `src/retrieval/table_lookup.py` + BM25 + `src/retrieval/answer_policy.py` (không đọc thuộc gold):
nhận câu hỏi -> trích metadata (`companies`, `years`, `report_version`, `target_unit`) -> BM25 cộng điểm metadata (`[0.0, 1.0]`) -> lookup/tổng hợp bảng (`table_records.jsonl`) -> ghép CONTEXT -> kiểm tra refusal & status.

Giao diện **Financial Intelligence** hiển thị: Verdict Card (pill trạng thái, đáp án, hộp phép tính, thẻ chunk), lưới 4 KPI thực thể trích xuất, và 2 tab (`Chứng cứ Top-K & Bảng số liệu gốc` và `CONTEXT gửi bộ sinh & Nhật ký truy hồi`).

## 1. Câu hỏi số liệu đầy đủ (`S_NEW_07`)

- **Câu hỏi:** Biên lợi nhuận gộp về bán hàng và cung cấp dịch vụ hợp nhất của CTCP Tập đoàn Hoa Sen trong năm tài chính kết thúc ngày 30/09/2024 là bao nhiêu phần trăm?
- **Trạng thái:** `answered` (`refused=False`)
- **Đáp án từ pipeline:** `10.8568 %`
- **Phép tính:** `(4263666396467 / 39271893738448) × 100% = 10.8568 %`
- **Top-5 nguồn trích dẫn (điểm chuẩn hóa `[0.0, 1.0]`):**
  1. `HSG_2024_consolidated#p009` (trang 9, điểm `1.0`)
  2. `HSG_2024_consolidated#p052` (trang 52, điểm `1.0`)
  3. `HSG_2024_consolidated#p045` (trang 45, điểm `0.693`)
  4. `HSG_2024_consolidated#p021` (trang 21, điểm `0.6168`)
  5. `HSG_2024_consolidated#p053` (trang 53, điểm `0.6113`)

## 2. Câu thiếu bằng chứng (`S_NEW_08`)

- **Câu hỏi:** Giá đóng cửa cổ phiếu HPG ngày 31/12/2024 là bao nhiêu đồng?
- **Trạng thái:** `refused` (`refused=True`)
- **Trả lời đúng nguyên văn:** `Không đủ bằng chứng trong corpus để trả lời.`
- **Chứng cứ:** 0 chunk (`check_refusal` từ chối an toàn trước khi sinh số liệu).

## 3. Câu diễn đạt lại (`PARA_01`)

- **Câu hỏi:** Biên lợi nhuận gộp của Hoa Sen năm 2024 bao nhiêu phần trăm?
- **Trạng thái:** `answered` (`refused=False`)
- **Đáp án từ pipeline:** `10.8568 %`
- **Phép tính:** `(4263666396467 / 39271893738448) × 100% = 10.8568 %`
- **Top-1 nguồn trích dẫn:** `HSG_2024_consolidated#p009` (trang 9, điểm `1.0`)

## 4. Câu ViFinQA đơn vị `%` (`ViFinQA-97`)

- **Câu hỏi:** Tỷ lệ sở hữu Công ty CP Gang thép Hòa Phát của HPG đến ngày 31/12/2023 là bao nhiêu %?
- **Trạng thái:** `answered` (`refused=False`)
- **Đáp án từ pipeline:** `99.988 %`
- **Phép tính / nguồn bảng:** `Công ty CP Gang thép Hòa Phát (i): 99.988 %`
- **Top-1 nguồn trích dẫn:** `HPG_2023_separate#p027` (trang 27, điểm `0.8808`), ưu tiên ô bảng đơn vị `%` thay vì giá gốc `VND`.

## 5. Câu so sánh / chênh lệch hai năm (`T2/T3` qua `table_lookup`)

- **Câu hỏi:** Nợ ngắn hạn hợp nhất của CTCP Tập đoàn Hoa Sen năm 2024 tăng hay giảm bao nhiêu so với năm 2023 (cùng đơn vị báo cáo)?
- **Trạng thái:** `answered` (`refused=False`)
- **Đáp án từ pipeline:** `2.0635 nghìn tỷ đồng`
- **Phép tính:** `2024: 8.6324 nghìn tỷ đồng - 2023: 6.5689 nghìn tỷ đồng = 2.0635 nghìn tỷ đồng`
- **Top-1 nguồn trích dẫn:** `HSG_2024_consolidated#p008` (trang 8, điểm `1.0`).
