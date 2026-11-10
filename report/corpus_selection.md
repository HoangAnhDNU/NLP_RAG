# Lựa chọn corpus báo cáo tài chính

Tài liệu này ghi lại mã CK, năm và loại bản (hợp nhất / riêng) **thực tế dùng**,  
kèm lý do chọn.

## 1. Tóm tắt

| thông tin | giá trị |
|---|---|
| Nguồn | `https://huggingface.co/datasets/AIGuruTinix/ViFinQA` |
| Revision | `0450088ab22ec946f04f097586967ca405955b3b` |
| Ngày truy xuất | 2026-11-10 |
| Số doanh nghiệp | 4 |
| Số năm | 5 (2020, 2021, 2022, 2023, 2024) |
| Số bản mỗi cặp công ty - năm | 2 (hợp nhất + riêng) |
| Số báo cáo theo cặp công ty - năm | 20 |
| Số file OCR thực tế | 40 |
| Tổng số trang | 2437 |
| Tổng số bảng OCR | 2585 |
| Chunk sinh ra (1 chunk = 1 trang) | 2407 |

| mã CK | tên công ty | ngành | năm | loại bản |
|---|---|---|---|---|
| HPG | CTCP Tập đoàn Hòa Phát | Thép | 2020-2024 | consolidated, separate |
| HSG | CTCP Tập đoàn Hoa Sen | Vật liệu xây dựng | 2020-2024 | consolidated, separate |
| NKG | CTCP Thép Nam Kim | Thép | 2020-2024 | consolidated, separate |
| MSR | CTCP Masan High-Tech Materials | Vật liệu hóa chất | 2020-2024 | consolidated, separate |

Cấu hình này nằm đúng định mức của hướng dẫn BTL: **10-20 báo cáo của 02-04 doanh nghiệp
qua một số năm**.

## 2. Vì sao chọn 4 doanh nghiệp này

Tiêu chí xếp hạng, lần lượt:

1. **Mật độ câu hỏi ViFinQA.** Trong 1012 câu hỏi gốc, đây là 4 doanh nghiệp có tổng

   số câu hỏi nhắc tới cao nhất trong giai đoạn 2020-2024 (35 câu khớp corpus
    sau khi lọc, gồm 10 câu một doanh nghiệp và 25 câu so sánh nhiều doanh nghiệp).
2. **Cùng ngành, cùng cấu trúc báo cáo.** HPG và NKG cùng ngành thép, HSG là vật liệu

   xây dựng, MSR là vật liệu hoá chất. Bốn doanh nghiệp này dùng cùng bộ mẫu báo cáo
    (Thông tư 202/2014/TT-BTC) với cùng bộ chỉ tiêu, nên bảng và chỉ tiêu tương ứng
    được giữa các doanh nghiệp. Việc này giúp câu hỏi so sánh nhiều doanh nghiệp
    trả lời được, thay vì phải học bộ chỉ tiêu khác nhau cho từng công ty.
3. **Chất lượng OCR.** Tất cả 4 doanh nghiệp có bảng HTML parse được, không có hàng

   lệch cột, dấu tiếng Việt được giữ nguyên. Chi tiết ở `report/ocr_audit.md`.
4. **Không phải ngân hàng.** Câu hỏi về báo cáo ngân hàng có hệ thống chỉ tiêu khác

   hẳn (dự phòng rủi ro tín dụng, tài sản tài chính phái sinh). Giữ nhóm ngành
    phi tài chính giúp bộ chỉ tiêu thống nhất, giảm tải cho nhóm khi gắn nhãn.

### Các lựa chọn đã cân nhắc và bị loại

| cấu hình | số câu hỏi khớp | lý do loại |
|---|---|---|
| HPG, HSG, NKG, MSR 2020-2025 | 41 | 24 báo cáo, vượt định mức 10-20 |
| HPG, HSG, NKG, MSR + DCM 2020-2024 | 40 | 25 báo cáo, vượt định mức |
| DCM, VRE, STB, MBB 2017-2022 | 32 | chỉ 32 câu, tệ hơn |
| VCB, ACB (ngân hàng) 2020-2024 | 9 | quá ít câu hỏi khớp |
| HPG, VCB, ACB 2020-2024 | 9 | quá ít câu hỏi khớp |

## 3. Bản hợp nhất và bản riêng: dùng cả hai

Mỗi cặp công ty - năm có hai bản:

- **consolidated (hợp nhất)**: gộp công ty mẹ và các công ty con.
- **separate (riêng)**: chỉ công ty mẹ.

Nhóm giữ **cả hai** vì câu hỏi ViFinQA phân biệt rõ hai phạm vi này. Trong 35 câu
khớp corpus có câu hỏi ghi rõ "công ty mẹ", và câu hỏi về chỉ tiêu hợp nhất không
trả lời được bằng bản riêng.

Quy ước đặt tên:

| trường | giá trị | ví dụ |
|---|---|---|
| `document_id` | `<TICKER>_<YEAR>_<consolidated\|separate>` | `HPG_2022_consolidated` |
| `chunk_id` | `<document_id>#p<page 3 chữ số>` | `HPG_2020_consolidated#p011` |

Danh sách đầy đủ kèm `sha256`, đường dẫn nguồn, số trang nằm ở
`data/processed/corpus_manifest.csv`.

## 4. Lọc tập câu hỏi

```bash
python src/filter_questions.py --tickers HPG HSG NKG MSR --years 2020 2021 2022 2023 2024
```

Cơ chế nhận diện doanh nghiệp, theo thứ tự ưu tiên:

1. Mã CK trong ngoặc, ví dụ `CTCP Tập đoàn Hòa Phát (HPG)`.
2. Mã CK viết tắt đứng riêng, ví dụ `công ty mẹ SCR năm 2017`.
3. Tên công ty trong câu hỏi, so khớp theo chuỗi từ liên tiếp.

Cách so khớp theo chuỗi liên tiếp tránh nhầm lẫn giữa các tên gần giống, ví dụ
"Ngân hàng TMCP Sài Gòn Tài Lộc" với "Ngân hàng TMCP Sài Gòn - Hà Nội".

### Kết quả

| kết quả | số câu |
|---|---|
| Tập gốc | 1012 |
| Giữ lại (khớp corpus) | 35 |
| Loại bỏ | 977 |

Lý do loại bỏ:

| lý do | số câu |
|---|---|
| doanh nghiệp ngoài corpus | 951 |
| năm ngoài corpus | 21 |
| không xác định được doanh nghiệp | 4 |
| không có năm trong câu hỏi | 1 |

Danh sách từng câu kèm lý do nằm ở `data/processed/questions_dropped.csv`.

### Phân bố 35 câu được giữ

| đặc trưng | phân bố |
|---|---|
| theo doanh nghiệp | HPG 28, HSG 27, NKG 27, MSR 25 (câu hỏi nhiều doanh nghiệp được tính cho từng DN) |
| theo năm | 2020: 5, 2021: 14, 2022: 21, 2023: 14, 2024: 10 |
| theo dạng | numeric 29, computation 6 |
| theo đơn vị được hỏi | (không rõ) 16, lần 7, nghìn tỷ đồng 6, triệu đồng 2, tỷ đồng 1, trăm tỷ đồng 1, % 2 |
| nhiều doanh nghiệp | 25 câu |
| cần phép tính | 20 câu |
| về công ty mẹ | 4 câu |

## 5. Khoảng cách với định mức 50 câu gold - đã bù đủ (200 câu)

ViFinQA công khai **không có gold answer, không có evidence, không có split**. Nhóm
đã tự xây bộ gold và hiện vượt định mức: **200 câu** trong
`data/annotations/qa_gold.jsonl` (dev 40, test 160).

| nguồn | số câu | ghi chú |
|---|---|---|
| vifinqa (35 câu khớp corpus) | 35 | câu gốc ViFinQA đã lọc, giữ nguyên id `ViFinQA-*` |
| table-clean | 150 | câu hỏi tra cứu chỉ tiêu trực tiếp trong bảng |
| supplement (`S_NEW_01` đến `S_NEW_15`) | 15 | câu bù có trích dẫn trang, gồm 7 câu số liệu pipeline RAG sinh được và 8 câu thiếu bằng chứng để kiểm tra refusal |

Ba cách từng cân nhắc ở bản trước (mở rộng sang 2025, thêm DCM, tự tạo câu mới):
nhóm đã chốt **cách 3** và giữ nguyên định mức 10-20 báo cáo (40 file OCR thực tế),
không mở rộng corpus. 25/35 câu ViFinQA là câu so sánh nhiều doanh nghiệp nên vẫn
giữ được độ khó so sánh mà không cần thêm báo cáo.

## 6. Lệnh chạy lại toàn bộ

```bash
python src/download_vifinqa.py --mode questions
python src/download_vifinqa.py --mode corpus --tickers HPG HSG NKG MSR --years 2020 2021 2022 2023 2024
python src/select_corpus.py --tickers HPG HSG NKG MSR --years 2020 2021 2022 2023 2024 --versions consolidated separate
python src/filter_questions.py --tickers HPG HSG NKG MSR --years 2020 2021 2022 2023 2024
python src/build_chunks.py
python src/audit_ocr.py
python src/data_quality_report.py
```
