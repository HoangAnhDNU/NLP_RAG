# Phân tích lỗi E0/E1/E2 (do script sinh, không chọn tay mẫu đẹp)

Nguồn số liệu: `evaluation/metrics_summary.csv` và các file `evaluation/test_predictions/test_predictions_E*.csv`, `evaluation/dev_predictions/dev_predictions_E*.csv` (do `src/evaluate/evaluate.py` sinh). Cùng test 160 câu, khớp `evaluation/split_freeze.json`, lưu tối đa 10 chunk (chấm @5 và `ctxP@5`/`ctxR@5` trên top-5, `@10` trên top-10).

Bảng chính (test n=160, 144 câu có evidence; dev n=44, 40 câu có evidence): E0 R@5=0.0764 R@10=0.125 MRR@5=0.0502 cite=0.0417 refusal P/R=0.0/0.0; E1 R@5=0.0417 R@10=0.0903 MRR@5=0.022 cite=0.0139 refusal P/R=0.0/0.0; E2 R@5=0.1389 R@10=0.2083 MRR@5=0.065 cite=0.0208 refusal P/R=1.0/1.0. E0-E2 không sinh đáp án số nên numeric match bằng 0,0 theo thiết kế.

Nhóm lỗi: OCR, sai năm, sai công ty, sai phiên bản báo cáo, nhiễu từ vựng, sai đơn vị, sai phép tính, thiếu từ chối, nhãn chưa đủ. Đánh giá retrieval và answer riêng: retrieval đúng (Recall@5 bằng 1 ở S_NEW_07) nhưng citation và answer vẫn sai.

## 1. S_NEW_01 - Nhiễu từ vựng: trang thuyết minh lấn át trang kết quả cùng báo cáo

- item_id và loại lỗi: `S_NEW_01`; Nhiễu từ vựng: trang thuyết minh lấn át trang kết quả cùng báo cáo.
- Đầu vào, nguồn và chứng cứ hợp lệ: Doanh thu thuần về bán hàng và cung cấp dịch vụ hợp nhất của HSG năm tài chính kết thúc 30/09/2024 là bao nhiêu nghìn tỷ đồng. Nguồn đúng: báo cáo hợp nhất HSG 2024, trang kết quả kinh doanh.
- Gold hoặc đáp án tham chiếu: Gold: `39.2719 nghìn tỷ đồng`, evidence: `HSG_2024_consolidated#p009`
- Prediction E0, E1, E2:
- E0 top-1 `HSG_2024_consolidated#p045` (điểm 35.3326), top-5 `HSG_2024_consolidated#p045;HSG_2024_separate#p044;HSG_2024_separate#p050;HSG_2024_consolidated#p053;NKG_2020_consolidated#p038`, answer: (để trống)
- E1 top-1 `HSG_2024_consolidated#p045` (điểm 0.8647), top-5 `HSG_2024_consolidated#p045;HSG_2024_separate#p044;HSG_2024_separate#p050;NKG_2024_separate#p042;NKG_2024_consolidated#p043`, answer: (để trống)
- E2 top-1 `HSG_2024_consolidated#p045` (điểm 1.1500), top-5 `HSG_2024_consolidated#p045;HSG_2024_separate#p044;HSG_2024_separate#p050;NKG_2024_separate#p042;NKG_2020_consolidated#p038`, answer: (để trống)
- Nguyên nhân khả dĩ (nhãn, OCR, số, mô hình, truy hồi, prompt): Truy hồi (retrieval): cụm doanh thu thuần về bán hàng xuất hiện ở cả trang p009 (bảng kết quả kinh doanh) và trang p045 (thuyết minh 26). BM25 và TF-IDF đều chấm điểm cao cho p045 vì đoạn thuyết minh lặp lại cụm từ nhiều lần. Cả 3 runs cùng sai top-1 về `HSG_2024_consolidated#p045`.
- Ảnh hưởng của lỗi đến người dùng: Người dùng nhận được trích dẫn đúng báo cáo, đúng năm, nhưng sai trang: trang thuyết minh không có con số tổng 39,2719 nghìn tỷ đồng. Nếu chỉ đọc top-1 sẽ không trả lời được.
- Đề xuất thay đổi và phép thử kế tiếp: Tăng trọng số cho chunk có bảng kết quả kinh doanh (Mẫu B 02-DN/HN) hoặc trừ điểm trang thuyết minh B 09 khi câu hỏi xin tổng chỉ tiêu. Phép thử: xếp lại top-20 theo hướng ưu tiên chunk có n_tables lớn hơn 0 và chứa mã số dòng 10.

## 2. S_NEW_02 - Sai công ty và sai năm ở E0, kèm nguy cơ sai đơn vị triệu đồng

- item_id và loại lỗi: `S_NEW_02`; Sai công ty và sai năm ở E0, kèm nguy cơ sai đơn vị triệu đồng.
- Đầu vào, nguồn và chứng cứ hợp lệ: Lợi nhuận sau thuế TNDN hợp nhất của NKG năm 2024 là bao nhiêu triệu đồng. Nguồn đúng: NKG hợp nhất 2024 trang 11.
- Gold hoặc đáp án tham chiếu: Gold: `453008.1444 triệu đồng`, evidence: `NKG_2024_consolidated#p011`
- Prediction E0, E1, E2:
- E0 top-1 `HSG_2020_consolidated#p060` (điểm 25.1327), top-5 `HSG_2020_consolidated#p060;NKG_2024_consolidated#p045;HSG_2020_separate#p060;NKG_2023_consolidated#p043;NKG_2022_consolidated#p044`, answer: (để trống)
- E1 top-1 `NKG_2024_consolidated#p045` (điểm 0.5818), top-5 `NKG_2024_consolidated#p045;HSG_2024_consolidated#p049;NKG_2023_consolidated#p043;HSG_2020_consolidated#p060;NKG_2023_consolidated#p002`, answer: (để trống)
- E2 top-1 `NKG_2024_consolidated#p045` (điểm 1.0944), top-5 `NKG_2024_consolidated#p045;HSG_2020_consolidated#p060;HSG_2020_separate#p060;NKG_2023_consolidated#p043;NKG_2024_consolidated#p011`, answer: (để trống)
- Nguyên nhân khả dĩ (nhãn, OCR, số, mô hình, truy hồi, prompt): Truy hồi: E0 trả `HSG_2020_consolidated#p060` (giải trình kết quả HSG 2019-2020) vì cụm lợi nhuận sau thuế hợp nhất xuất hiện dày đặc ở văn bản giải trình này. BM25 unigram không giữ được điều kiện NKG và 2024 khi chunk giải trình chứa nhiều từ khóa trùng lặp. Đơn vị triệu đồng cũng dễ nhầm sang tỷ đồng nếu hệ thống tự đổi đơn vị.
- Ảnh hưởng của lỗi đến người dùng: Nghiêm trọng: sai cả công ty và niên độ, dẫn tới con số hoàn toàn sai. Đây là lỗi nguy hiểm nhất với báo cáo tài chính, kèm rủi ro sai đơn vị tiền.
- Đề xuất thay đổi và phép thử kế tiếp: Lọc cứng metadata trước khi chấm điểm BM25: chỉ giữ chunk có company_id và fiscal_year khớp câu hỏi. Phép thử E3: lọc trước NKG và 2024 rồi mới hợp nhất điểm.

## 3. S_NEW_04 - Sai phiên bản báo cáo: consolidated thay cho separate

- item_id và loại lỗi: `S_NEW_04`; Sai phiên bản báo cáo: consolidated thay cho separate.
- Đầu vào, nguồn và chứng cứ hợp lệ: Tiền và các khoản tương đương tiền của công ty mẹ HPG (báo cáo riêng) tại 31/12/2024. Nguồn đúng: HPG separate trang 7.
- Gold hoặc đáp án tham chiếu: Gold: `319.2579 tỷ đồng`, evidence: `HPG_2024_separate#p007`
- Prediction E0, E1, E2:
- E0 top-1 `HPG_2024_consolidated#p037` (điểm 25.0293), top-5 `HPG_2024_consolidated#p037;HPG_2024_separate#p019;HSG_2020_separate#p060;HPG_2024_separate#p025;HPG_2023_consolidated#p038`, answer: (để trống)
- E1 top-1 `HPG_2024_consolidated#p037` (điểm 0.7465), top-5 `HPG_2024_consolidated#p037;HPG_2021_consolidated#p044;HPG_2020_consolidated#p040;HPG_2023_consolidated#p038;MSR_2022_consolidated#p041`, answer: (để trống)
- E2 top-1 `HPG_2024_consolidated#p037` (điểm 1.1500), top-5 `HPG_2024_consolidated#p037;HPG_2024_separate#p019;HPG_2023_consolidated#p038;HPG_2021_consolidated#p044;HPG_2020_consolidated#p040`, answer: (để trống)
- Nguyên nhân khả dĩ (nhãn, OCR, số, mô hình, truy hồi, prompt): Truy hồi và nhãn: cả 3 runs trả `HPG_2024_consolidated#p037` (thuyết minh tiền của báo cáo hợp nhất) thay vì `HPG_2024_separate#p007`. Cụm công ty mẹ trong câu hỏi không đủ mạnh để thắng cụm hợp nhất lặp lại nhiều lần trong corpus. Điểm cộng metadata của E2 chỉ xét công ty và năm, không phân biệt report_version.
- Ảnh hưởng của lỗi đến người dùng: Người dùng nhận số của tập đoàn hợp nhất thay vì công ty mẹ, sai đối tượng hợp nhất. Trình bày sai này khó phát hiện vì cùng HPG, cùng năm, cùng chỉ tiêu.
- Đề xuất thay đổi và phép thử kế tiếp: Thêm điều kiện report_version vào điểm cộng: câu hỏi có công ty mẹ, riêng hoặc separate thì cộng điểm cho chunk separate và trừ điểm consolidated. Phép thử: từ điển phát hiện mẹ và riêng trong query.

## 4. S_NEW_06 - Sai năm: dense LSA trôi 4 năm và top-1 rơi vào trang thuyết minh năm trước

- item_id và loại lỗi: `S_NEW_06`; Sai năm: dense LSA trôi 4 năm và top-1 rơi vào trang thuyết minh năm trước.
- Đầu vào, nguồn và chứng cứ hợp lệ: Lãi cơ bản trên cổ phiếu hợp nhất của NKG năm 2024 là bao nhiêu đồng. Nguồn đúng: NKG hợp nhất 2024 trang 11.
- Gold hoặc đáp án tham chiếu: Gold: `1434 đồng`, evidence: `NKG_2024_consolidated#p011`
- Prediction E0, E1, E2:
- E0 top-1 `NKG_2024_consolidated#p042` (điểm 23.0614), top-5 `NKG_2024_consolidated#p042;NKG_2024_consolidated#p041;NKG_2021_consolidated#p040;NKG_2022_consolidated#p041;NKG_2022_consolidated#p040`, answer: (để trống)
- E1 top-1 `NKG_2020_consolidated#p037` (điểm 0.7290), top-5 `NKG_2020_consolidated#p037;MSR_2024_consolidated#p073;NKG_2021_consolidated#p040;HPG_2020_consolidated#p068;HSG_2024_consolidated#p044`, answer: (để trống)
- E2 top-1 `NKG_2024_consolidated#p042` (điểm 1.0645), top-5 `NKG_2024_consolidated#p042;NKG_2021_consolidated#p040;NKG_2024_consolidated#p041;HSG_2024_consolidated#p044;HPG_2024_consolidated#p065`, answer: (để trống)
- Nguyên nhân khả dĩ (nhãn, OCR, số, mô hình, truy hồi, prompt): Mô hình: E1 trả `NKG_2020_consolidated#p037`, lệch 4 năm. SVD 128 chiều làm mờ từ khóa hiếm 2024 vì năm xuất hiện ở hầu hết chunk. E0 và E2 trả `NKG_2024_consolidated#p042`, đúng năm nhưng rơi vào thuyết minh lãi trên cổ phiếu năm 2023 được trình bày lại, không phải bảng kết quả 2024.
- Ảnh hưởng của lỗi đến người dùng: Người dùng nhận con số năm cũ hoặc số điều chỉnh hồi tố của năm trước. Với chỉ tiêu trên cổ phiếu, sai một năm là sai hoàn toàn quyết định.
- Đề xuất thay đổi và phép thử kế tiếp: Giảm số chiều SVD hoặc dùng trọng số riêng cho token năm ngoài cosine. Phép thử: nhân đôi trọng số token năm trong vector query trước khi tính cosine.

## 5. S_NEW_07 - Retrieval trúng nhưng citation top-1 sai, kèm sai phép tính biên lợi nhuận

- item_id và loại lỗi: `S_NEW_07`; Retrieval trúng nhưng citation top-1 sai, kèm sai phép tính biên lợi nhuận.
- Đầu vào, nguồn và chứng cứ hợp lệ: Biên lợi nhuận gộp hợp nhất của HSG năm tài chính kết thúc 30/09/2024 là bao nhiêu phần trăm. Cần tính từ doanh thu thuần và giá vốn. Nguồn đúng: HSG hợp nhất trang 9.
- Gold hoặc đáp án tham chiếu: Gold: `10.8568 %`, evidence: `HSG_2024_consolidated#p009`
- Prediction E0, E1, E2:
- E0 top-1 `HSG_2024_separate#p050` (điểm 36.2036), top-5 `HSG_2024_separate#p050;HSG_2024_consolidated#p052;HSG_2020_consolidated#p060;HSG_2024_consolidated#p009;HSG_2020_separate#p060`, answer: (để trống)
- E1 top-1 `HSG_2024_separate#p009` (điểm 0.7523), top-5 `HSG_2024_separate#p009;HSG_2024_consolidated#p045;HSG_2024_consolidated#p009;HSG_2024_separate#p050;HSG_2024_separate#p044`, answer: (để trống)
- E2 top-1 `HSG_2024_separate#p050` (điểm 1.1246), top-5 `HSG_2024_separate#p050;HSG_2024_consolidated#p009;HSG_2024_consolidated#p052;HSG_2024_separate#p009;NKG_2024_consolidated#p011`, answer: (để trống)
- Nguyên nhân khả dĩ (nhãn, OCR, số, mô hình, truy hồi, prompt): Trích dẫn và phép tính: cả 3 runs đều có chunk gold trong top-5 (E0 hạng 4, E1 hạng 3, E2 hạng 2) nên Recall@5 bằng 1, nhưng top-1 lại là bản separate thay vì consolidated nên citation correctness vẫn bằng 0.0. Đây là ví dụ điển hình retrieval đúng nhưng citation và đáp án vẫn sai. Ngoài ra cả 3 runs không sinh văn bản nên phép tính biên lợi nhuận gộp chưa từng được thực hiện, numeric match bằng 0.0 theo thiết kế.
- Ảnh hưởng của lỗi đến người dùng: Hệ thống báo trúng nhưng trích dẫn đầu tiên vẫn sai bản báo cáo. Người dùng kiểm chứng sẽ thấy số liệu bản riêng khác bản hợp nhất. Thiếu phép tính khiến đáp án phần trăm không bao giờ xuất hiện.
- Đề xuất thay đổi và phép thử kế tiếp: Xếp lại 5 chunk đầu bằng bộ lọc report_version: câu hỏi có hợp nhất thì đẩy consolidated lên trước khi chọn top-1 để trích dẫn. Phép thử: áp dụng trên toàn bộ tập test có evidence, sau đó bổ sung bước tính (lợi nhuận gộp chia doanh thu thuần nhân 100).

## 6. S_NEW_03 (dev) - Dense và hybrid thua BM25 trên câu dùng tên đầy đủ của MSR

- item_id và loại lỗi: `S_NEW_03 (dev)`; Dense và hybrid thua BM25 trên câu dùng tên đầy đủ của MSR.
- Đầu vào, nguồn và chứng cứ hợp lệ: Doanh thu thuần hợp nhất của MSR năm 2024. Nguồn đúng: MSR hợp nhất trang 11.
- Gold hoặc đáp án tham chiếu: Gold: `14336.3287 tỷ đồng`, evidence: `MSR_2024_consolidated#p011`
- Prediction E0, E1, E2:
- E0 top-1 `HSG_2024_consolidated#p045` (điểm 30.6682), top-5 `HSG_2024_consolidated#p045;NKG_2020_consolidated#p038;NKG_2021_consolidated#p041;HSG_2024_separate#p044;MSR_2024_consolidated#p011`, answer: (để trống)
- E1 top-1 `HSG_2024_consolidated#p045` (điểm 0.8163), top-5 `HSG_2024_consolidated#p045;HSG_2024_separate#p044;NKG_2024_separate#p042;NKG_2024_consolidated#p043;NKG_2020_consolidated#p038`, answer: (để trống)
- E2 top-1 `HSG_2024_consolidated#p045` (điểm 1.1500), top-5 `HSG_2024_consolidated#p045;HSG_2024_separate#p044;NKG_2020_consolidated#p038;NKG_2024_separate#p042;NKG_2024_consolidated#p043`, answer: (để trống)
- Nguyên nhân khả dĩ (nhãn, OCR, số, mô hình, truy hồi, prompt): Mô hình: nếu E0 không tách tên công ty tiếng Việt hoặc dense/hybrid bỏ sót alias, câu hỏi ghi tên đầy đủ 'CTCP Masan High-Tech Materials' thay vì mã MSR (MSR chiếm 10/40 báo cáo trong corpus) dễ bị nhiễu thực thể giữa HSG và MSR.
- Ảnh hưởng của lỗi đến người dùng: Chứng minh giả thuyết dense tốt hơn BM25 không đúng khi câu hỏi dùng tên đầy đủ thay vì mã CK. Nếu chọn mô hình bằng dev nhỏ sẽ kết luận sai.
- Đề xuất thay đổi và phép thử kế tiếp: Dùng `resolve_tickers()` ánh xạ tên tiếng Việt đầy đủ sang mã CK (MSR/HSG/HPG/NKG) trước khi cộng điểm metadata và tính trọng số query.

## 7. S_NEW_05 - Sai công ty và sai năm: E1 trôi sang HPG_2021

- item_id và loại lỗi: `S_NEW_05`; Sai công ty và sai năm: E1 trôi sang HPG_2021.
- Đầu vào, nguồn và chứng cứ hợp lệ: Tiền và các khoản tương đương tiền hợp nhất của HSG tại 30/09/2024. Nguồn đúng: HSG hợp nhất trang 7.
- Gold hoặc đáp án tham chiếu: Gold: `602.0718 tỷ đồng`, evidence: `HSG_2024_consolidated#p007`
- Prediction E0, E1, E2:
- E0 top-1 `HSG_2024_consolidated#p024` (điểm 20.5364), top-5 `HSG_2024_consolidated#p024;HSG_2020_consolidated#p060;HSG_2024_separate#p039;HSG_2022_separate#p021;HSG_2021_consolidated#p025`, answer: (để trống)
- E1 top-1 `HPG_2021_consolidated#p044` (điểm 0.6939), top-5 `HPG_2021_consolidated#p044;HSG_2021_consolidated#p025;HPG_2024_consolidated#p037;HPG_2020_consolidated#p040;HPG_2023_consolidated#p038`, answer: (để trống)
- E2 top-1 `HSG_2024_consolidated#p024` (điểm 0.9872), top-5 `HSG_2024_consolidated#p024;HPG_2024_consolidated#p037;HSG_2021_consolidated#p025;HSG_2022_separate#p021;HPG_2023_consolidated#p038`, answer: (để trống)
- Nguyên nhân khả dĩ (nhãn, OCR, số, mô hình, truy hồi, prompt): Truy hồi: E1 top-1 là `HPG_2021_consolidated#p044`, sai cả HSG thành HPG và 2024 thành 2021. Cụm tiền và các khoản tương đương tiền là tiêu đề bảng phổ biến ở mọi báo cáo nên cosine dense gần như chỉ đo độ dài vector, không giữ được điều kiện thực thể.
- Ảnh hưởng của lỗi đến người dùng: Top-1 hoàn toàn không liên quan, người dùng mất niềm tin ngay từ kết quả đầu tiên.
- Đề xuất thay đổi và phép thử kế tiếp: Bắt buộc lọc trước công ty và năm khi câu hỏi có mã CK và năm rõ ràng, rồi mới tính cosine dense. Phép thử: chỉ truy hồi trong 2 báo cáo HSG 2024 rồi mới xếp hạng.

## 8. S_NEW_08 - Thiếu cơ chế từ chối ở E0 và E1 (nhóm giá thị trường)

- item_id và loại lỗi: `S_NEW_08`; Thiếu cơ chế từ chối ở E0 và E1 (nhóm giá thị trường).
- Đầu vào, nguồn và chứng cứ hợp lệ: Giá đóng cửa cổ phiếu HPG ngày 31/12/2024 là bao nhiêu đồng? Corpus chỉ có báo cáo tài chính, không có dữ liệu giá thị trường.
- Gold hoặc đáp án tham chiếu: Gold: `Không đủ bằng chứng trong corpus để trả lời.`, evidence: (không có, needs_more_evidence=true)
- Prediction E0, E1, E2:
- E0 top-1 `MSR_2022_consolidated#p031` (điểm 16.8699), top-5 `MSR_2022_consolidated#p031;MSR_2023_consolidated#p032;MSR_2024_consolidated#p031;MSR_2020_consolidated#p028;MSR_2021_consolidated#p030`, answer: (để trống)
- E1 top-1 `MSR_2022_consolidated#p031` (điểm 0.7604), top-5 `MSR_2022_consolidated#p031;MSR_2024_consolidated#p031;MSR_2021_consolidated#p030;MSR_2020_consolidated#p028;MSR_2023_consolidated#p032`, answer: (để trống)
- E2 top-1 `MSR_2024_consolidated#p031` (điểm 1.0621), top-5 `MSR_2024_consolidated#p031;MSR_2022_consolidated#p031;MSR_2020_consolidated#p028;MSR_2021_consolidated#p030;MSR_2023_consolidated#p032`, answer: Không đủ bằng chứng trong corpus để trả lời.
- Nguyên nhân khả dĩ (nhãn, OCR, số, mô hình, truy hồi, prompt): Thiết kế: E0 và E1 để `predicted_answer` trống theo Mục 4.6.3 nên không thể đạt refusal_rate. E2 từ chối đúng nhờ 10 mẫu viết tay (giá đóng cửa, vốn hóa thị trường và các mẫu khác). Refusal 1.0 của E2 là luật, không phải năng lực mô hình.
- Ảnh hưởng của lỗi đến người dùng: E0 và E1 trả về top-5 chunk nhưng để trống câu trả lời: người dùng không biết là thiếu bằng chứng hay lỗi hệ thống. Nguy cơ suy diễn số gần đúng từ chunk sai.
- Đề xuất thay đổi và phép thử kế tiếp: Thêm ngưỡng từ chối độc lập với mẫu từ khóa: nếu điểm hợp nhất cao nhất thấp hơn ngưỡng hoặc top-5 không chứa mã CK và năm thì từ chối. Phép thử: học ngưỡng trên dev thay vì khớp chuỗi cứng.

## 9. S_NEW_10 - Thiếu cơ chế từ chối ở E0 và E1 (nhóm báo cáo quý và bán niên)

- item_id và loại lỗi: `S_NEW_10`; Thiếu cơ chế từ chối ở E0 và E1 (nhóm báo cáo quý và bán niên).
- Đầu vào, nguồn và chứng cứ hợp lệ: Doanh thu thuần quý 1 năm 2024 của CTCP Tập đoàn Hòa Phát là bao nhiêu tỷ đồng? Corpus chỉ có báo cáo năm, không có báo cáo quý.
- Gold hoặc đáp án tham chiếu: Gold: `Không đủ bằng chứng trong corpus để trả lời.`, evidence: (không có, needs_more_evidence=true)
- Prediction E0, E1, E2:
- E0 top-1 `HSG_2020_consolidated#p060` (điểm 17.9938), top-5 `HSG_2020_consolidated#p060;HSG_2020_separate#p060;HPG_2024_consolidated#p018;HPG_2023_consolidated#p018;MSR_2023_consolidated#p002`, answer: (để trống)
- E1 top-1 `HPG_2024_separate#p033` (điểm 0.5870), top-5 `HPG_2024_separate#p033;HPG_2024_consolidated#p059;NKG_2024_separate#p042;HPG_2022_separate#p036;NKG_2024_consolidated#p043`, answer: (để trống)
- E2 top-1 `HSG_2020_consolidated#p060` (điểm 0.8951), top-5 `HSG_2020_consolidated#p060;HSG_2020_separate#p060;HPG_2024_separate#p033;HPG_2024_consolidated#p032;HPG_2024_consolidated#p059`, answer: Không đủ bằng chứng trong corpus để trả lời.
- Nguyên nhân khả dĩ (nhãn, OCR, số, mô hình, truy hồi, prompt): Tương tự S_NEW_08: E0 và E1 không có quy tắc từ chối. Câu hỏi quý 1 năm 2024 vẫn được chấm BM25 và LSA như câu thường, trả về 5 chunk báo cáo năm gần âm thanh nhất.
- Ảnh hưởng của lỗi đến người dùng: Hệ thống có thể khiến người dùng tưởng số cả năm là số quý 1 nếu họ tự đọc chunk. Đây là lỗi hiểu lầm đơn vị kỳ báo cáo.
- Đề xuất thay đổi và phép thử kế tiếp: Bổ sung nhận diện kỳ báo cáo (quý, bán niên, 6 tháng) và đối chiếu với metadata corpus (chỉ có báo cáo năm) để từ chối có giải thích. Phép thử: mở rộng pattern kèm lý do thay vì một câu cứng.

## 10. ViFinQA-368 - Câu đa bước đa công ty: truy hồi một trang không gom đủ bằng chứng

- item_id và loại lỗi: `ViFinQA-368`; Câu đa bước đa công ty: truy hồi một trang không gom đủ bằng chứng.
- Đầu vào, nguồn và chứng cứ hợp lệ: Năm 2022, trong nhóm HPG, HSG, MSR và NKG, các công ty có hệ số thanh toán nhanh thấp hơn trung vị của nhóm có biên lợi nhuận ròng bình quân là bao nhiêu phần trăm?... (cần lọc nhóm theo trung vị rồi tính bình quân trên nhiều công ty và năm)
- Gold hoặc đáp án tham chiếu: Gold: `0.5909 %`, evidence: `HSG_2022_consolidated#p006; HSG_2022_consolidated#p008; HSG_2022_consolidated#p009; MSR_2022_consolidated#p009; MSR_2022_consolidated#p011; MSR_2022_consolidated#p012; HPG_2022_consolidated#p007; HPG_2022_consolidated#p009; NKG_2022_consolidated#p008; NKG_2022_consolidated#p010`, status: `reviewed-agree`, split: test
- Prediction E0, E1, E2:
- E0 top-1 `MSR_2023_consolidated#p035` (điểm 18.6332), top-5 `MSR_2023_consolidated#p035;HSG_2022_separate#p031;MSR_2021_consolidated#p034;MSR_2023_consolidated#p073;HSG_2021_consolidated#p022`, answer: (để trống)
- E1 top-1 `HSG_2023_consolidated#p055` (điểm 0.5480), top-5 `HSG_2023_consolidated#p055;HSG_2020_consolidated#p057;HPG_2023_consolidated#p064;HPG_2021_consolidated#p071;HSG_2021_consolidated#p059`, answer: (để trống)
- E2 top-1 `MSR_2023_consolidated#p035` (điểm 0.9444), top-5 `MSR_2023_consolidated#p035;HSG_2023_consolidated#p055;MSR_2021_consolidated#p034;HPG_2023_consolidated#p064;MSR_2022_consolidated#p069`, answer: (để trống)
- Nguyên nhân khả dĩ (nhãn, OCR, số, mô hình, truy hồi, prompt): Truy hồi đa bước (trạng thái gold hiện tại: `reviewed-agree`, còn 0 câu ViFinQA `pending-answer`): câu hỏi cần tổng hợp số liệu nhiều báo cáo (HPG, HSG, MSR, NKG) trong khi E0-E2 truy hồi một lượt trên top-5 chunk đơn lẻ, không tách truy vấn con theo từng công ty.
- Ảnh hưởng của lỗi đến người dùng: Metric retrieval hiện tính trên tập câu có evidence (test 144 câu, dev 40 câu). Với câu so sánh đa công ty, top-5 chunk một lượt thường bỏ sót ít nhất một thực thể.
- Đề xuất thay đổi và phép thử kế tiếp: Tách truy vấn đa bước theo từng cặp (công ty, năm) rồi tổng hợp trung vị/bình quân; kiểm tra phủ đủ thực thể qua `decide_status()` (`missing_multi_entity_evidence`).

## 11. ViFinQA-97 - Câu đơn chỉ tiêu tỷ lệ sở hữu: E0-E2 không trích xuất câu trả lời %

- item_id và loại lỗi: `ViFinQA-97`; Câu đơn chỉ tiêu tỷ lệ sở hữu: E0-E2 không trích xuất câu trả lời %.
- Đầu vào, nguồn và chứng cứ hợp lệ: Tỷ lệ sở hữu Công ty CP Gang thép Hòa Phát của HPG đến ngày 31/12/2023 là bao nhiêu %?
- Gold hoặc đáp án tham chiếu: Gold: `99.988 %`, evidence: `HPG_2023_separate#p027`, status: `reviewed-agree`, split: test
- Prediction E0, E1, E2:
- E0 top-1 `HPG_2023_separate#p027` (điểm 32.6302), top-5 `HPG_2023_separate#p027;HPG_2021_separate#p030;HPG_2022_separate#p027;HPG_2020_separate#p030;HPG_2023_consolidated#p017`, answer: (để trống)
- E1 top-1 `HPG_2021_separate#p030` (điểm 0.8317), top-5 `HPG_2021_separate#p030;HPG_2020_separate#p030;HPG_2022_separate#p027;HPG_2024_separate#p036;HPG_2023_separate#p037`, answer: (để trống)
- E2 top-1 `HPG_2023_separate#p027` (điểm 0.9951), top-5 `HPG_2023_separate#p027;HPG_2021_separate#p030;HPG_2020_separate#p030;HPG_2022_separate#p027;HPG_2023_consolidated#p017`, answer: (để trống)
- Nguyên nhân khả dĩ (nhãn, OCR, số, mô hình, truy hồi, prompt): Truy hồi & trích xuất đơn vị (trạng thái gold hiện tại: `reviewed-agree`): E0 và E2 tìm đúng vùng (`HPG_2023_separate#p027`), nhưng E0-E2 không sinh đáp án, còn pipeline lookup dễ nhầm cột vốn góp VND với cột tỷ lệ sở hữu `%` nếu thiếu lọc `target_unit`.
- Ảnh hưởng của lỗi đến người dùng: Nếu hệ thống không ưu tiên bản ghi khớp đơn vị `%`, người dùng có thể nhận giá trị VND thô thay cho tỷ lệ phần trăm sở hữu.
- Đề xuất thay đổi và phép thử kế tiếp: Ưu tiên lọc `target_unit` trong `table_lookup` (khớp `%` trước khi fallback) và kiểm tra đánh giá qua `evaluate.py`.

## 12. OCR và đơn vị: HSG_2024_consolidated#p009 và NKG_2024_consolidated#p011 - Lỗi OCR làm nhiễu tokenize và rủi ro sai đơn vị tiền

- item_id và loại lỗi: `OCR và đơn vị: HSG_2024_consolidated#p009 và NKG_2024_consolidated#p011`; Lỗi OCR làm nhiễu tokenize và rủi ro sai đơn vị tiền.
- Đầu vào, nguồn và chứng cứ hợp lệ: Hai trang gold quan trọng nhất: HSG p009 và NKG p011. Đơn vị gốc là VND thô trong bảng, gold đã đổi sang nghìn tỷ đồng, triệu đồng và phần trăm nên cần giữ đúng hệ số đổi.
- Gold hoặc đáp án tham chiếu: Gold S_NEW_01 chứa 39.271.893.738.448 VND đổi sang nghìn tỷ đồng; S_NEW_02 và S_NEW_06 nằm trên trang có nhiều ký tự rác.
- Prediction E0, E1, E2:
E0, E1, E2 vẫn index cả hai trang, nhưng token từ tiêu đề bảng có thể thừa hoặc mang dấu sai.
- Nguyên nhân khả dĩ (nhãn, OCR, số, mô hình, truy hồi, prompt): OCR: tiêu đề bảng HSG có dấu sắc đặt sai, trang NKG dính ký tự rác lặp lại hàng chục lần nên tạo token rác. Tokenizer giữ dấu nên từ sai dấu và từ đúng dấu có thể thành 2 token khác nhau, làm giảm điểm BM25 và TF-IDF của tiêu đề bảng. Đơn vị VND thô trong chunk cũng khác đơn vị đã đổi trong gold nên so khớp số nguyên văn sẽ trượt nếu không đổi đơn vị trước.
- Ảnh hưởng của lỗi đến người dùng: Làm giảm điểm chunk gold trong tập test (144 câu có evidence). Người dùng thấy trích dẫn vẫn đọc được số nhưng hệ thống dễ rơi sang trang thuyết minh, đồng thời nếu không chuẩn hóa đơn vị khi chấm sẽ sinh unsupported claim giả.
- Đề xuất thay đổi và phép thử kế tiếp: Tiền xử lý riêng tiêu đề bảng (chuẩn hóa dấu sai, xóa chuỗi rác dài) nhưng giữ bản gốc để trích dẫn; dùng quy đổi đơn vị chuẩn trong `table_lookup.py` và `numbers_in_context()`.

