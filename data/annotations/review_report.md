# Biên bản hậu kiểm chéo gold tự tạo (Mục 2.2)

- Phạm vi: 15 câu tự tạo trong `qa_gold_supplement.jsonl` (guideline v0.1).
- Mẫu hậu kiểm: 5/15 câu (33%, vượt định mức 20%): S_NEW_01, S_NEW_03, S_NEW_06, S_NEW_07, S_NEW_08.
- Người gắn nhãn: member-1. Người hậu kiểm: member-2.
- Phương pháp: member-2 tra lại chunk gốc, kiểm tra quote nguyên văn, tính lại giá trị, tìm toàn văn cụm vắng mặt với câu thiếu bằng chứng.
- Kết quả:
  - S_NEW_01: member-2 tra chunk HSG_2024_consolidated#p009 p9, tính lại khớp value=39.2719.
  - S_NEW_03: member-2 tra chunk MSR_2024_consolidated#p011 p11, tính lại khớp value=14336.3287.
  - S_NEW_06: member-2 tra chunk NKG_2024_consolidated#p011 p11, tính lại khớp value=1434.
  - S_NEW_07: member-2 tra chunk HSG_2024_consolidated#p009 p9, tính lại khớp value=10.8568.
  - S_NEW_08: member-2 tìm toàn văn 'giá đóng cửa', 0 hit, đồng ý thiếu bằng chứng.
- Bất đồng: 0/5 mẫu. Không phải phân xử.
- Quy tắc phân xử khi có bất đồng (guideline Mục 7): tra lại chunk gốc, bên sai chuỗi bằng chứng sửa theo chunk; bất đồng về quy tắc do người ban hành guideline quyết định và cập nhật guideline lên phiên bản mới.
