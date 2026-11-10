"""Demo Streamlit hỏi đáp báo cáo tài chính có trích dẫn (Mục 6.1).

Pipeline RAG thuần, không đọc thuộc gold: nhận câu hỏi -> trích metadata
-> BM25 cộng điểm metadata trên 40 báo cáo -> lookup có cấu trúc trên
`table_records.jsonl` -> ghép top-k chunks thành CONTEXT có citation
-> bộ sinh đáp án offline chỉ dùng CONTEXT theo `config/answer_policy.yaml`
-> hiển thị đáp án kèm nguồn. Gold chỉ dùng offline để chấm điểm.

Chạy:
    conda activate NLP
    pip install streamlit pyyaml
    streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app"))

try:
    import streamlit as st
except ModuleNotFoundError:  # pragma: no cover
    raise SystemExit("Chưa cài streamlit. Chạy: pip install streamlit pyyaml")

from qa_engine import load_engine, answer  # noqa: E402

GROUP_TITLES = {
    "verified": "Câu sinh đáp án từ pipeline RAG (7 câu S_NEW_01 đến S_NEW_07)",
    "refusal": "Câu thiếu bằng chứng (3 câu S_NEW_08 đến S_NEW_10)",
    "paraphrase": "Câu diễn đạt lại (sinh trực tiếp từ pipeline)",
    "vifinqa": "Câu ViFinQA (sinh từ bảng nếu khớp)",
}


def load_samples() -> list[dict]:
    path = ROOT / "app" / "sample_questions.jsonl"
    rows = [json.loads(line) for line in open(path, encoding="utf-8")]
    for r in rows:
        qid = r.get("qid", "")
        if qid in ("S_NEW_01", "S_NEW_02", "S_NEW_03", "S_NEW_04", "S_NEW_05", "S_NEW_06", "S_NEW_07"):
            r["group"] = "verified"
        elif qid in ("S_NEW_08", "S_NEW_09", "S_NEW_10"):
            r["group"] = "refusal"
        elif qid.startswith("PARA"):
            r["group"] = "paraphrase"
        else:
            r["group"] = "vifinqa"
    order = {"verified": 0, "refusal": 1, "paraphrase": 2, "vifinqa": 3}
    rows.sort(key=lambda r: (order.get(r["group"], 9), r.get("qid", "")))
    return rows


st.set_page_config(page_title="RAG báo cáo tài chính HPG HSG NKG MSR", layout="wide")
st.title("Hỏi đáp báo cáo tài chính có trích dẫn")
st.caption("Corpus: HPG, HSG, NKG, MSR giai đoạn 2020-2024, 2407 chunk (1 chunk bằng 1 trang). Đáp án sinh từ pipeline RAG (không đọc thuộc gold), câu ngoài corpus bị từ chối.")

chunks, _, _, _, _, _ = load_engine()
with st.sidebar:
    st.header("Thiết lập")
    top_k = st.slider("Số nguồn hiển thị (top-k)", 1, 10, 5)
    show_full = st.checkbox("Hiện toàn văn chunk", value=False)
    st.write(f"Đã nạp {len(chunks)} chunk.")
    st.write("Config: `config/e0_bm25.yaml` và `config/e2_hybrid.yaml`.")
    st.divider()
    st.header("Câu mẫu (13 câu)")
    samples = load_samples()
    current_group = None
    for s in samples:
        if s["group"] != current_group:
            current_group = s["group"]
            st.subheader(GROUP_TITLES[current_group])
        label = s.get("label", s.get("qid", ""))
        if st.button(label, key=f"sample_{s.get('qid', label)}"):
            st.session_state["question"] = s["question"]

question = st.text_area(
    "Nhập câu hỏi",
    value=st.session_state.get("question", samples[0]["question"]),
    height=90,
)
ask = st.button("Hỏi", type="primary")

if ask and question.strip():
    with st.spinner("Đang truy hồi..."):
        result = answer(question.strip(), top_k)
    status = result.get("answer_status", "refused" if result.get("refused") else "answered")
    cite_ok = result.get("citation_complete", False)
    entities = result.get("entities", {})

    st.subheader("1. Câu hỏi người dùng")
    st.write(result.get("question", question.strip()))

    st.subheader("2. Thực thể đã trích")
    ent_cols = st.columns(4)
    ent_cols[0].metric("Công ty", ", ".join(entities.get("companies", [])) or "chưa rõ")
    ent_cols[1].metric("Năm", ", ".join(entities.get("years", [])) or "chưa rõ")
    ent_cols[2].metric("Bản báo cáo", entities.get("report_version", "") or "chưa rõ")
    ent_cols[3].metric("Đơn vị hỏi", entities.get("target_unit", "") or "chưa rõ")
    if entities.get("company_names"):
        st.caption("Tên đầy đủ: " + "; ".join(entities.get("company_names", [])))
    if entities.get("indicator_guess"):
        st.caption(f"Chỉ tiêu đoán từ bảng: `{entities.get('indicator_guess', '')}`")

    st.subheader("3. Trạng thái refusal và quyết định")
    st.caption(f"Trạng thái: `{status}` (lý do: {result.get('status_reason', '')}) | Trích dẫn đầy đủ: {cite_ok} | Nguồn đáp án: `{result.get('answer_source', '')}`")
    st.caption("Pipeline: câu hỏi -> trích metadata -> BM25 + điểm metadata -> lookup bảng -> ghép CONTEXT -> sinh đáp án chỉ từ CONTEXT theo `config/answer_policy.yaml` (không đọc thuộc gold).")
    if result.get("context"):
        with st.expander("Xem CONTEXT đã ghép (citation gửi cho bộ sinh đáp án)", expanded=False):
            st.code(result.get("context", ""), language="text")
    if result.get("refused") or status == "refused":
        st.warning(result["answer"])
        st.info("Hệ thống từ chối vì câu hỏi thuộc nhóm ngoài corpus: quý, bán niên, kế hoạch, dự báo, giá thị trường.")
    elif status == "ambiguous":
        st.warning("Trạng thái ambiguous: có nhiều giá trị mâu thuẫn, cần làm rõ kỳ, công ty hoặc đơn vị.")
        if result.get("answer"):
            st.success(f"Trả lời: {result['answer']}")
    else:
        if result.get("answer"):
            st.success(f"Trả lời: {result['answer']}")
            if result.get("computation"):
                st.write(f"**Phép tính:** {result['computation']}")
            if result.get("evidence"):
                st.write("**Chunk chứng cứ:** " + "; ".join(f"`{c}`" for c in result["evidence"]))
        else:
            st.warning("Trả lời: (pipeline chưa sinh được đáp án chắc chắn)")
            if result.get("candidates"):
                st.write("**Số ứng viên trong đoạn liên quan nhất:** " + "; ".join(result["candidates"]))
            if result.get("note"):
                st.caption(result["note"])
            if result.get("suggestions"):
                st.write("**Có phải bạn muốn hỏi một trong các câu sau (bấm để chạy lại pipeline):**")
                for s in result["suggestions"]:
                    if st.button(f"[{s['question_id']}, khớp {s['score']}] {s['question'][:80]}...", key=f"sug_{s['question_id']}"):
                        st.session_state["question"] = s["question"]
                        st.rerun()

    if result.get("conflict_warning"):
        st.subheader("6. Cảnh báo mâu thuẫn")
        st.warning(result["conflict_warning"])

    st.subheader(f"4. Top {len(result['hits'])} evidence chunks (kiểm chứng số liệu)")
    st.caption("Số liệu và từ khóa câu hỏi được in đậm. Đối chiếu con số trong đáp án với đoạn highlight bên dưới.")
    for i, h in enumerate(result["hits"], 1):
        title = f"{i}. {h['company_id']} {h['fiscal_year']} {h['report_version']} trang {h['page']} [{h['chunk_id']}] (điểm {h['score']})"
        with st.expander(title, expanded=(i == 1)):
            st.write(f"**5. Đường dẫn tài liệu gốc:** `{h.get('source_path', h.get('chunk_id', ''))}`")
            st.write(f"**Doanh nghiệp:** {h['company_id']} | **Năm:** {h['fiscal_year']} | **Bản:** {h['report_version']} | **Trang:** {h['page']} | **Chunk:** `{h['chunk_id']}` | **Đơn vị trang:** `{h.get('unit', '')}` | **Số bảng:** {h.get('n_tables', '')} | **Độ dài:** {h['full_len']} ký tự")
            st.markdown(f"**Đoạn liên quan (highlight):** {h.get('snippet_highlight', h.get('snippet', ''))}")
            rows = h.get("table_rows", [])
            if rows:
                st.write("**7. Bảng gốc của chunk này (từ `table_records.jsonl`):**")
                st.dataframe(
                    [
                        {
                            "metric": r.get("metric", ""),
                            "mã": r.get("metric_code", ""),
                            "kỳ": r.get("period_label", ""),
                            "năm": r.get("year", ""),
                            "giá trị thô": r.get("value_raw", ""),
                            "đơn vị": r.get("unit", ""),
                            "trang": r.get("page", ""),
                        }
                        for r in rows[:5]
                    ]
                )
                if st.button("Xem bảng gốc đầy đủ", key=f"tbl_{h['chunk_id']}_{i}"):
                    st.session_state[f"show_tbl_{h['chunk_id']}_{i}"] = not st.session_state.get(f"show_tbl_{h['chunk_id']}_{i}", False)
                if st.session_state.get(f"show_tbl_{h['chunk_id']}_{i}", False):
                    st.dataframe(
                        [
                            {
                                "metric": r.get("metric", ""),
                                "mã": r.get("metric_code", ""),
                                "kỳ": r.get("period_label", ""),
                                "năm": r.get("year", ""),
                                "value": r.get("value", ""),
                                "giá trị thô": r.get("value_raw", ""),
                                "đơn vị": r.get("unit", ""),
                                "bảng": r.get("table_index", ""),
                                "trang": r.get("page", ""),
                                "chunk": r.get("source_chunk_id", ""),
                            }
                            for r in rows
                        ]
                    )
            if show_full:
                st.text_area("Toàn văn chunk", value=h["full_text"], height=300, key=f"full_{h['chunk_id']}_{i}")
elif ask:
    st.error("Vui lòng nhập câu hỏi trước khi bấm Hỏi.")
