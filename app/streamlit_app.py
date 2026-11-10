"""Demo Streamlit hỏi đáp báo cáo tài chính có trích dẫn (Mục 6.1).

Dùng chung engine trong `app/qa_engine.py`:
- 7 câu bổ sung có kiểm chứng: trả đáp án kèm phép tính.
- Câu ngoài corpus: từ chối đúng nguyên văn.
- Câu còn lại: truy hồi BM25 cộng điểm metadata, đoạn liên quan 1200 ký tự
  quanh từ khóa kèm nút mở rộng toàn văn chunk.

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
    "verified": "Câu có đáp án kiểm chứng (7 câu S_NEW_01 đến S_NEW_07)",
    "refusal": "Câu thiếu bằng chứng (3 câu S_NEW_08 đến S_NEW_10)",
    "paraphrase": "Câu diễn đạt lại (thử gợi ý)",
    "vifinqa": "Câu ViFinQA chưa có gold",
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
st.caption("Corpus: HPG, HSG, NKG, MSR giai đoạn 2020-2024, 2407 chunk (1 chunk bằng 1 trang). 7 câu bổ sung có đáp án kiểm chứng, câu ngoài corpus bị từ chối.")

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
    if result.get("refused"):
        st.warning(result["answer"])
        st.info("Hệ thống từ chối vì câu hỏi thuộc nhóm ngoài corpus: quý, bán niên, kế hoạch, dự báo, giá thị trường.")
    else:
        if result.get("answer"):
            st.success(f"Trả lời: {result['answer']}")
            if result.get("computation"):
                st.write(f"**Phép tính:** {result['computation']}")
            if result.get("evidence"):
                st.write("**Chunk chứng cứ:** " + "; ".join(f"`{c}`" for c in result["evidence"]))
            if result.get("matched_qid"):
                st.caption(f"Mã câu khớp: {result['matched_qid']} (đáp án đã kiểm chứng).")
        else:
            st.warning("Trả lời: (chưa có đáp án kiểm chứng cho câu này)")
            if result.get("candidates"):
                st.write("**Số ứng viên trong đoạn liên quan nhất:** " + "; ".join(result["candidates"]))
            if result.get("note"):
                st.caption(result["note"])
            if result.get("suggestions"):
                st.write("**Có phải bạn muốn hỏi một trong các câu sau:**")
                for s in result["suggestions"]:
                    tag = "có đáp án" if s.get("has_answer") else ("từ chối" if s.get("refusal") else "chưa có đáp án")
                    if st.button(f"[{s['question_id']}, {tag}, khớp {s['score']}] {s['question'][:80]}...", key=f"sug_{s['question_id']}"):
                        st.session_state["question"] = s["question"]
                        st.rerun()
        st.subheader(f"Top {len(result['hits'])} nguồn trích dẫn")
        for i, h in enumerate(result["hits"], 1):
            title = f"{i}. {h['company_id']} {h['fiscal_year']} {h['report_version']} trang {h['page']} [{h['chunk_id']}] (điểm {h['score']})"
            with st.expander(title, expanded=(i == 1)):
                st.write(f"**Doanh nghiệp:** {h['company_id']} | **Năm:** {h['fiscal_year']} | **Bản:** {h['report_version']} | **Trang:** {h['page']} | **Chunk:** `{h['chunk_id']}` | **Độ dài:** {h['full_len']} ký tự")
                st.write(f"**Đoạn liên quan:** {h['snippet']}")
                if show_full:
                    st.text_area("Toàn văn chunk", value=h["full_text"], height=300, key=f"full_{h['chunk_id']}_{i}")
elif ask:
    st.error("Vui lòng nhập câu hỏi trước khi bấm Hỏi.")
