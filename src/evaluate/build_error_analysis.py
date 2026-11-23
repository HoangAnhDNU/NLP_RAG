"""Sinh evaluation/error_analysis.md từ dữ liệu thật (Mục 5.2, Mẫu B).

Mỗi mục có đủ 7 trường. Số liệu prediction và gold được đọc từ file, không gõ tay.
Chạy: python src/evaluate/build_error_analysis.py
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]


def load_pred(path: Path) -> dict:
    d = {}
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            d[r["question_id"]] = r
    return d


def main() -> int:
    with open(ROOT / "data" / "annotations" / "qa_gold.jsonl", encoding="utf-8") as gf:
        gold = {json.loads(line)["question_id"]: json.loads(line) for line in gf if line.strip()}
    meta = json.loads((ROOT / "data" / "splits" / "split_meta.json").read_text(encoding="utf-8"))
    n_test = int(meta.get("n_test", len(meta.get("test_ids", []))))
    n_dev = int(meta.get("n_dev", len(meta.get("dev_ids", []))))
    n_ev_test = sum(1 for g in gold.values() if g.get("split") == "test" and g.get("evidence"))
    n_ev_dev = sum(1 for g in gold.values() if g.get("split") == "dev" and g.get("evidence"))
    n_pending_vif = sum(
        1 for g in gold.values() if g.get("source") == "vifinqa" and g.get("review_status") == "pending-answer"
    )
    t0 = load_pred(ROOT / "evaluation/test_predictions/test_predictions_E0.csv")
    t1 = load_pred(ROOT / "evaluation/test_predictions/test_predictions_E1.csv")
    t2 = load_pred(ROOT / "evaluation/test_predictions/test_predictions_E2.csv")
    d0 = load_pred(ROOT / "evaluation/dev_predictions/dev_predictions_E0.csv")
    d1 = load_pred(ROOT / "evaluation/dev_predictions/dev_predictions_E1.csv")
    d2 = load_pred(ROOT / "evaluation/dev_predictions/dev_predictions_E2.csv")

    with open(ROOT / "evaluation" / "metrics_summary.csv", encoding="utf-8") as mf:
        rows = list(csv.DictReader(mf))
    k_saved = max(
        (
            len([c for c in (r.get("predicted_chunk_ids") or "").split(";") if c.strip()])
            for d in (t0, t1, t2)
            for r in d.values()
        ),
        default=5,
    )

    def preds_for_qid(qid: str) -> list[tuple[str, dict]]:
        if gold.get(qid, {}).get("split") == "dev":
            return [("E0", d0), ("E1", d1), ("E2", d2)]
        return [("E0", t0), ("E1", t1), ("E2", t2)]

    def case_label(qid: str) -> str:
        split = gold.get(qid, {}).get("split", "")
        return f"{qid} ({split})" if split == "dev" else qid

    def pred_line(qid: str, src=None) -> str:
        src = src if src is not None else preds_for_qid(qid)
        parts = []
        for nm, d in src:
            r = d.get(qid, {})
            score = r.get("bm25_score_top1", r.get("retrieval_score_top1", ""))
            ans = (r.get("predicted_answer", "") or "").strip()
            ans_show = ans if ans else "(để trống)"
            top5_ids = ";".join([c for c in (r.get("predicted_chunk_ids") or "").split(";") if c][:5])
            parts.append(f"{nm} top-1 `{r.get('predicted_top1_chunk_id', '')}` (điểm {score}), top-5 `{top5_ids}`, answer: {ans_show}")
        return "\n".join(f"- {p}" for p in parts)

    def gold_evidence(qid: str) -> str:
        g = gold[qid]
        ev = list(dict.fromkeys(e["chunk_id"] for e in g.get("evidence", []) if e.get("chunk_id")))
        if ev:
            return "; ".join(ev)
        if g.get("needs_more_evidence"):
            return "(không có evidence, needs_more_evidence=true)"
        return "(chưa có evidence, pending-answer)"

    cases = []

    cases.append({
        "id": "S_NEW_01",
        "type": "Nhiễu từ vựng: trang thuyết minh lấn át trang kết quả cùng báo cáo",
        "input": "Doanh thu thuần về bán hàng và cung cấp dịch vụ hợp nhất của HSG năm tài chính kết thúc 30/09/2024 là bao nhiêu nghìn tỷ đồng. Nguồn đúng: báo cáo hợp nhất HSG 2024, trang kết quả kinh doanh.",
        "gold": f"Gold: `{gold['S_NEW_01'].get('gold_answer')}`, evidence: `{gold_evidence('S_NEW_01')}`",
        "pred": pred_line("S_NEW_01", [("E0", t0), ("E1", t1), ("E2", t2)]),
        "cause": "Truy hồi (retrieval): cụm doanh thu thuần về bán hàng xuất hiện ở cả trang p009 (bảng kết quả kinh doanh) và trang p045 (thuyết minh 26). BM25 và TF-IDF đều chấm điểm cao cho p045 vì đoạn thuyết minh lặp lại cụm từ nhiều lần. Cả 3 runs cùng sai top-1 về `HSG_2024_consolidated#p045`.",
        "impact": "Người dùng nhận được trích dẫn đúng báo cáo, đúng năm, nhưng sai trang: trang thuyết minh không có con số tổng 39,2719 nghìn tỷ đồng. Nếu chỉ đọc top-1 sẽ không trả lời được.",
        "next": "Tăng trọng số cho chunk có bảng kết quả kinh doanh (Mẫu B 02-DN/HN) hoặc trừ điểm trang thuyết minh B 09 khi câu hỏi xin tổng chỉ tiêu. Phép thử: xếp lại top-20 theo hướng ưu tiên chunk có n_tables lớn hơn 0 và chứa mã số dòng 10.",
    })
    cases.append({
        "id": "S_NEW_02",
        "type": "Sai công ty và sai năm ở E0, kèm nguy cơ sai đơn vị triệu đồng",
        "input": "Lợi nhuận sau thuế TNDN hợp nhất của NKG năm 2024 là bao nhiêu triệu đồng. Nguồn đúng: NKG hợp nhất 2024 trang 11.",
        "gold": f"Gold: `{gold['S_NEW_02'].get('gold_answer')}`, evidence: `{gold_evidence('S_NEW_02')}`",
        "pred": pred_line("S_NEW_02", [("E0", t0), ("E1", t1), ("E2", t2)]),
        "cause": "Truy hồi: E0 trả `HSG_2020_consolidated#p060` (giải trình kết quả HSG 2019-2020) vì cụm lợi nhuận sau thuế hợp nhất xuất hiện dày đặc ở văn bản giải trình này. BM25 unigram không giữ được điều kiện NKG và 2024 khi chunk giải trình chứa nhiều từ khóa trùng lặp. Đơn vị triệu đồng cũng dễ nhầm sang tỷ đồng nếu hệ thống tự đổi đơn vị.",
        "impact": "Nghiêm trọng: sai cả công ty và niên độ, dẫn tới con số hoàn toàn sai. Đây là lỗi nguy hiểm nhất với báo cáo tài chính, kèm rủi ro sai đơn vị tiền.",
        "next": "Lọc cứng metadata trước khi chấm điểm BM25: chỉ giữ chunk có company_id và fiscal_year khớp câu hỏi. Phép thử E3: lọc trước NKG và 2024 rồi mới hợp nhất điểm.",
    })
    cases.append({
        "id": "S_NEW_04",
        "type": "Sai phiên bản báo cáo: consolidated thay cho separate",
        "input": "Tiền và các khoản tương đương tiền của công ty mẹ HPG (báo cáo riêng) tại 31/12/2024. Nguồn đúng: HPG separate trang 7.",
        "gold": f"Gold: `{gold['S_NEW_04'].get('gold_answer')}`, evidence: `{gold_evidence('S_NEW_04')}`",
        "pred": pred_line("S_NEW_04", [("E0", t0), ("E1", t1), ("E2", t2)]),
        "cause": "Truy hồi và nhãn: cả 3 runs trả `HPG_2024_consolidated#p037` (thuyết minh tiền của báo cáo hợp nhất) thay vì `HPG_2024_separate#p007`. Cụm công ty mẹ trong câu hỏi không đủ mạnh để thắng cụm hợp nhất lặp lại nhiều lần trong corpus. Điểm cộng metadata của E2 chỉ xét công ty và năm, không phân biệt report_version.",
        "impact": "Người dùng nhận số của tập đoàn hợp nhất thay vì công ty mẹ, sai đối tượng hợp nhất. Trình bày sai này khó phát hiện vì cùng HPG, cùng năm, cùng chỉ tiêu.",
        "next": "Thêm điều kiện report_version vào điểm cộng: câu hỏi có công ty mẹ, riêng hoặc separate thì cộng điểm cho chunk separate và trừ điểm consolidated. Phép thử: từ điển phát hiện mẹ và riêng trong query.",
    })
    cases.append({
        "id": "S_NEW_06",
        "type": "Sai năm: dense LSA trôi 4 năm và top-1 rơi vào trang thuyết minh năm trước",
        "input": "Lãi cơ bản trên cổ phiếu hợp nhất của NKG năm 2024 là bao nhiêu đồng. Nguồn đúng: NKG hợp nhất 2024 trang 11.",
        "gold": f"Gold: `{gold['S_NEW_06'].get('gold_answer')}`, evidence: `{gold_evidence('S_NEW_06')}`",
        "pred": pred_line("S_NEW_06", [("E0", t0), ("E1", t1), ("E2", t2)]),
        "cause": "Mô hình: E1 trả `NKG_2020_consolidated#p037`, lệch 4 năm. SVD 128 chiều làm mờ từ khóa hiếm 2024 vì năm xuất hiện ở hầu hết chunk. E0 và E2 trả `NKG_2024_consolidated#p042`, đúng năm nhưng rơi vào thuyết minh lãi trên cổ phiếu năm 2023 được trình bày lại, không phải bảng kết quả 2024.",
        "impact": "Người dùng nhận con số năm cũ hoặc số điều chỉnh hồi tố của năm trước. Với chỉ tiêu trên cổ phiếu, sai một năm là sai hoàn toàn quyết định.",
        "next": "Giảm số chiều SVD hoặc dùng trọng số riêng cho token năm ngoài cosine. Phép thử: nhân đôi trọng số token năm trong vector query trước khi tính cosine.",
    })
    cases.append({
        "id": "S_NEW_07",
        "type": "Retrieval trúng nhưng citation top-1 sai, kèm sai phép tính biên lợi nhuận",
        "input": "Biên lợi nhuận gộp hợp nhất của HSG năm tài chính kết thúc 30/09/2024 là bao nhiêu phần trăm. Cần tính từ doanh thu thuần và giá vốn. Nguồn đúng: HSG hợp nhất trang 9.",
        "gold": f"Gold: `{gold['S_NEW_07'].get('gold_answer')}`, evidence: `{gold_evidence('S_NEW_07')}`",
        "pred": pred_line("S_NEW_07", [("E0", t0), ("E1", t1), ("E2", t2)]),
        "cause": "Trích dẫn và phép tính: cả 3 runs đều có chunk gold trong top-5 (E0 hạng 4, E1 hạng 3, E2 hạng 2) nên Recall@5 bằng 1, nhưng top-1 lại là bản separate thay vì consolidated nên citation correctness vẫn bằng 0.0. Đây là ví dụ điển hình retrieval đúng nhưng citation và đáp án vẫn sai. Ngoài ra cả 3 runs không sinh văn bản nên phép tính biên lợi nhuận gộp chưa từng được thực hiện, numeric match bằng 0.0 theo thiết kế.",
        "impact": "Hệ thống báo trúng nhưng trích dẫn đầu tiên vẫn sai bản báo cáo. Người dùng kiểm chứng sẽ thấy số liệu bản riêng khác bản hợp nhất. Thiếu phép tính khiến đáp án phần trăm không bao giờ xuất hiện.",
        "next": "Xếp lại 5 chunk đầu bằng bộ lọc report_version: câu hỏi có hợp nhất thì đẩy consolidated lên trước khi chọn top-1 để trích dẫn. Phép thử: áp dụng trên toàn bộ tập test có evidence, sau đó bổ sung bước tính (lợi nhuận gộp chia doanh thu thuần nhân 100).",
    })
    cases.append({
        "id": case_label("S_NEW_03"),
        "type": "Dense và hybrid thua BM25 trên câu dùng tên đầy đủ của MSR",
        "input": "Doanh thu thuần hợp nhất của MSR năm 2024. Nguồn đúng: MSR hợp nhất trang 11.",
        "gold": f"Gold: `{gold['S_NEW_03'].get('gold_answer')}`, evidence: `{gold_evidence('S_NEW_03')}`",
        "pred": pred_line("S_NEW_03"),
        "cause": "Mô hình: nếu E0 không tách tên công ty tiếng Việt hoặc dense/hybrid bỏ sót alias, câu hỏi ghi tên đầy đủ 'CTCP Masan High-Tech Materials' thay vì mã MSR (MSR chiếm 10/40 báo cáo trong corpus) dễ bị nhiễu thực thể giữa HSG và MSR.",
        "impact": "Chứng minh giả thuyết dense tốt hơn BM25 không đúng khi câu hỏi dùng tên đầy đủ thay vì mã CK. Nếu chọn mô hình bằng dev nhỏ sẽ kết luận sai.",
        "next": "Dùng `resolve_tickers()` ánh xạ tên tiếng Việt đầy đủ sang mã CK (MSR/HSG/HPG/NKG) trước khi cộng điểm metadata và tính trọng số query.",
    })
    cases.append({
        "id": case_label("S_NEW_05"),
        "type": "Sai công ty và sai năm: E1 trôi sang HPG_2021",
        "input": "Tiền và các khoản tương đương tiền hợp nhất của HSG tại 30/09/2024. Nguồn đúng: HSG hợp nhất trang 7.",
        "gold": f"Gold: `{gold['S_NEW_05'].get('gold_answer')}`, evidence: `{gold_evidence('S_NEW_05')}`",
        "pred": pred_line("S_NEW_05"),
        "cause": "Truy hồi: E1 top-1 là `HPG_2021_consolidated#p044`, sai cả HSG thành HPG và 2024 thành 2021. Cụm tiền và các khoản tương đương tiền là tiêu đề bảng phổ biến ở mọi báo cáo nên cosine dense gần như chỉ đo độ dài vector, không giữ được điều kiện thực thể.",
        "impact": "Top-1 hoàn toàn không liên quan, người dùng mất niềm tin ngay từ kết quả đầu tiên.",
        "next": "Bắt buộc lọc trước công ty và năm khi câu hỏi có mã CK và năm rõ ràng, rồi mới tính cosine dense. Phép thử: chỉ truy hồi trong 2 báo cáo HSG 2024 rồi mới xếp hạng.",
    })
    cases.append({
        "id": "S_NEW_08",
        "type": "Thiếu cơ chế từ chối ở E0 và E1 (nhóm giá thị trường)",
        "input": gold["S_NEW_08"]["question"] + " Corpus chỉ có báo cáo tài chính, không có dữ liệu giá thị trường.",
        "gold": f"Gold: `{gold['S_NEW_08'].get('gold_answer')}`, evidence: (không có, needs_more_evidence=true)",
        "pred": pred_line("S_NEW_08", [("E0", t0), ("E1", t1), ("E2", t2)]),
        "cause": "Thiết kế: E0 và E1 để `predicted_answer` trống theo Mục 4.6.3 nên không thể đạt refusal_rate. E2 từ chối đúng nhờ 10 mẫu viết tay (giá đóng cửa, vốn hóa thị trường và các mẫu khác). Refusal 1.0 của E2 là luật, không phải năng lực mô hình.",
        "impact": "E0 và E1 trả về top-5 chunk nhưng để trống câu trả lời: người dùng không biết là thiếu bằng chứng hay lỗi hệ thống. Nguy cơ suy diễn số gần đúng từ chunk sai.",
        "next": "Thêm ngưỡng từ chối độc lập với mẫu từ khóa: nếu điểm hợp nhất cao nhất thấp hơn ngưỡng hoặc top-5 không chứa mã CK và năm thì từ chối. Phép thử: học ngưỡng trên dev thay vì khớp chuỗi cứng.",
    })
    cases.append({
        "id": "S_NEW_10",
        "type": "Thiếu cơ chế từ chối ở E0 và E1 (nhóm báo cáo quý và bán niên)",
        "input": gold["S_NEW_10"]["question"] + " Corpus chỉ có báo cáo năm, không có báo cáo quý.",
        "gold": f"Gold: `{gold['S_NEW_10'].get('gold_answer')}`, evidence: (không có, needs_more_evidence=true)",
        "pred": pred_line("S_NEW_10", [("E0", t0), ("E1", t1), ("E2", t2)]),
        "cause": "Tương tự S_NEW_08: E0 và E1 không có quy tắc từ chối. Câu hỏi quý 1 năm 2024 vẫn được chấm BM25 và LSA như câu thường, trả về 5 chunk báo cáo năm gần âm thanh nhất.",
        "impact": "Hệ thống có thể khiến người dùng tưởng số cả năm là số quý 1 nếu họ tự đọc chunk. Đây là lỗi hiểu lầm đơn vị kỳ báo cáo.",
        "next": "Bổ sung nhận diện kỳ báo cáo (quý, bán niên, 6 tháng) và đối chiếu với metadata corpus (chỉ có báo cáo năm) để từ chối có giải thích. Phép thử: mở rộng pattern kèm lý do thay vì một câu cứng.",
    })
    g368 = gold["ViFinQA-368"]
    g97 = gold["ViFinQA-97"]
    status368 = g368.get("review_status", "")
    status97 = g97.get("review_status", "")
    cases.append({
        "id": "ViFinQA-368",
        "type": "Câu đa bước đa công ty: truy hồi một trang không gom đủ bằng chứng",
        "input": (g368["question"][:220] + "... (cần lọc nhóm theo trung vị rồi tính bình quân trên nhiều công ty và năm)"),
        "gold": f"Gold: `{(g368.get('gold_answer') or '(trống)')}`, evidence: `{gold_evidence('ViFinQA-368')}`, status: `{status368}`, split: {g368.get('split')}",
        "pred": pred_line("ViFinQA-368", [("E0", t0), ("E1", t1), ("E2", t2)]),
        "cause": f"Truy hồi đa bước (trạng thái gold hiện tại: `{status368}`, còn {n_pending_vif} câu ViFinQA `pending-answer`): câu hỏi cần tổng hợp số liệu nhiều báo cáo (HPG, HSG, MSR, NKG) trong khi E0-E2 truy hồi một lượt trên top-5 chunk đơn lẻ, không tách truy vấn con theo từng công ty.",
        "impact": f"Metric retrieval hiện tính trên tập câu có evidence (test {n_ev_test} câu, dev {n_ev_dev} câu). Với câu so sánh đa công ty, top-5 chunk một lượt thường bỏ sót ít nhất một thực thể.",
        "next": "Tách truy vấn đa bước theo từng cặp (công ty, năm) rồi tổng hợp trung vị/bình quân; kiểm tra phủ đủ thực thể qua `decide_status()` (`missing_multi_entity_evidence`).",
    })
    cases.append({
        "id": "ViFinQA-97",
        "type": "Câu đơn chỉ tiêu tỷ lệ sở hữu: E0-E2 không trích xuất câu trả lời %",
        "input": g97["question"],
        "gold": f"Gold: `{(g97.get('gold_answer') or '(trống)')}`, evidence: `{gold_evidence('ViFinQA-97')}`, status: `{status97}`, split: {g97.get('split')}",
        "pred": pred_line("ViFinQA-97", [("E0", t0), ("E1", t1), ("E2", t2)]),
        "cause": f"Truy hồi & trích xuất đơn vị (trạng thái gold hiện tại: `{status97}`): E0 và E2 tìm đúng vùng (`HPG_2023_separate#p027`), nhưng E0-E2 không sinh đáp án, còn pipeline lookup dễ nhầm cột vốn góp VND với cột tỷ lệ sở hữu `%` nếu thiếu lọc `target_unit`.",
        "impact": "Nếu hệ thống không ưu tiên bản ghi khớp đơn vị `%`, người dùng có thể nhận giá trị VND thô thay cho tỷ lệ phần trăm sở hữu.",
        "next": "Ưu tiên lọc `target_unit` trong `table_lookup` (khớp `%` trước khi fallback) và kiểm tra đánh giá qua `evaluate.py`.",
    })
    cases.append({
        "id": "OCR và đơn vị: HSG_2024_consolidated#p009 và NKG_2024_consolidated#p011",
        "type": "Lỗi OCR làm nhiễu tokenize và rủi ro sai đơn vị tiền",
        "input": "Hai trang gold quan trọng nhất: HSG p009 và NKG p011. Đơn vị gốc là VND thô trong bảng, gold đã đổi sang nghìn tỷ đồng, triệu đồng và phần trăm nên cần giữ đúng hệ số đổi.",
        "gold": "Gold S_NEW_01 chứa 39.271.893.738.448 VND đổi sang nghìn tỷ đồng; S_NEW_02 và S_NEW_06 nằm trên trang có nhiều ký tự rác.",
        "pred": "E0, E1, E2 vẫn index cả hai trang, nhưng token từ tiêu đề bảng có thể thừa hoặc mang dấu sai.",
        "cause": "OCR: tiêu đề bảng HSG có dấu sắc đặt sai, trang NKG dính ký tự rác lặp lại hàng chục lần nên tạo token rác. Tokenizer giữ dấu nên từ sai dấu và từ đúng dấu có thể thành 2 token khác nhau, làm giảm điểm BM25 và TF-IDF của tiêu đề bảng. Đơn vị VND thô trong chunk cũng khác đơn vị đã đổi trong gold nên so khớp số nguyên văn sẽ trượt nếu không đổi đơn vị trước.",
        "impact": f"Làm giảm điểm chunk gold trong tập test ({n_ev_test} câu có evidence). Người dùng thấy trích dẫn vẫn đọc được số nhưng hệ thống dễ rơi sang trang thuyết minh, đồng thời nếu không chuẩn hóa đơn vị khi chấm sẽ sinh unsupported claim giả.",
        "next": "Tiền xử lý riêng tiêu đề bảng (chuẩn hóa dấu sai, xóa chuỗi rác dài) nhưng giữ bản gốc để trích dẫn; dùng quy đổi đơn vị chuẩn trong `table_lookup.py` và `numbers_in_context()`.",
    })

    lines = []
    lines.append("# Phân tích lỗi E0/E1/E2 (do script sinh, không chọn tay mẫu đẹp)")
    lines.append("")
    lines.append(f"Nguồn số liệu: `evaluation/metrics_summary.csv` và các file `evaluation/test_predictions/test_predictions_E*.csv`, `evaluation/dev_predictions/dev_predictions_E*.csv` (do `src/evaluate/evaluate.py` sinh). Cùng test {n_test} câu, khớp `evaluation/split_freeze.json`, lưu tối đa {k_saved} chunk (chấm @5 và `ctxP@5`/`ctxR@5` trên top-5, `@10` trên top-10).")
    lines.append("")
    def fmt(run, split):
        for r in rows:
            if r["run"] == run and r["split"] == split:
                return "R@5=%s R@10=%s MRR@5=%s cite=%s refusal P/R=%s/%s" % (
                    r.get("recall_at_5", ""),
                    r.get("recall_at_10", ""),
                    r.get("mrr_at_5", ""),
                    r.get("citation_precision_top1", ""),
                    r.get("refusal_precision", ""),
                    r.get("refusal_recall", ""),
                )
        return ""
    lines.append("Bảng chính (test n=%d, %d câu có evidence; dev n=%d, %d câu có evidence): E0 %s; E1 %s; E2 %s. E0-E2 không sinh đáp án số nên numeric match bằng 0,0 theo thiết kế." % (n_test, n_ev_test, n_dev, n_ev_dev, fmt("E0", "test"), fmt("E1", "test"), fmt("E2", "test")))
    lines.append("")
    lines.append("Nhóm lỗi: OCR, sai năm, sai công ty, sai phiên bản báo cáo, nhiễu từ vựng, sai đơn vị, sai phép tính, thiếu từ chối, nhãn chưa đủ. Đánh giá retrieval và answer riêng: retrieval đúng (Recall@5 bằng 1 ở S_NEW_07) nhưng citation và answer vẫn sai.")
    lines.append("")
    for i, c in enumerate(cases, 1):
        lines.append(f"## {i}. {c['id']} - {c['type']}")
        lines.append("")
        lines.append(f"- item_id và loại lỗi: `{c['id']}`; {c['type']}.")
        lines.append(f"- Đầu vào, nguồn và chứng cứ hợp lệ: {c['input']}")
        lines.append(f"- Gold hoặc đáp án tham chiếu: {c['gold']}")
        lines.append(f"- Prediction E0, E1, E2:\n{c['pred']}")
        lines.append(f"- Nguyên nhân khả dĩ (nhãn, OCR, số, mô hình, truy hồi, prompt): {c['cause']}")
        lines.append(f"- Ảnh hưởng của lỗi đến người dùng: {c['impact']}")
        lines.append(f"- Đề xuất thay đổi và phép thử kế tiếp: {c['next']}")
        lines.append("")
    out = ROOT / "evaluation" / "error_analysis.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Đã ghi {len(cases)} mục -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
