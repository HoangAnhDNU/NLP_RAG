"""Engine dùng chung cho demo CLI và Streamlit (Mục 6.1).

Trả lời gồm 3 tầng:
1. Khớp nguyên văn câu hỏi bổ sung (S_NEW_01 đến S_NEW_07): trả gold_answer
   kèm phép tính và chunk evidence đã kiểm chứng.
2. Quy tắc từ chối: 10 mẫu ngoài corpus trong `config/e2_hybrid.yaml`.
3. Còn lại: truy hồi BM25 cộng điểm metadata, trích đoạn liên quan quanh
   từ khóa câu hỏi, liệt kê số ứng viên và gợi ý câu hỏi gần nhất để tránh
   cứng nhắc khi người dùng diễn đạt lại.

Đoạn trích không cắt cụt 300 ký tự như bản cũ: lấy cửa sổ 1200 ký tự quanh
vị trí khớp nhiều từ khóa nhất, đồng thời giữ toàn văn chunk để mở rộng.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.preprocess.normalize import normalize_query, tokenize_vi  # noqa: E402
from src.retrieval.bm25 import BM25Retriever  # noqa: E402

TICKERS = ["HPG", "HSG", "NKG", "MSR"]
YEAR_RE = re.compile(r"\b(20[0-2]\d)\b")
NUMBER_RE = re.compile(r"\(?[\d.]{4,}\)?|\d[\d.,]*\s*(?:VND|đồng|%|tỷ|triệu|nghìn)?", re.IGNORECASE)

_engine_cache: dict = {}


def detect_meta(question: str) -> tuple[list[str], list[str]]:
    up = question.upper()
    tickers = [t for t in TICKERS if re.search(rf"(?<![A-Z]){t}(?![A-Z])", up)]
    years = YEAR_RE.findall(question)
    return tickers, years


def load_engine():
    if _engine_cache:
        return (_engine_cache["chunks"], _engine_cache["tokenize"],
                _engine_cache["retriever"], _engine_cache["patterns"],
                _engine_cache["gold_by_q"], _engine_cache["gold_list"])
    e0_cfg = yaml.safe_load(open(ROOT / "config" / "e0_bm25.yaml", encoding="utf-8"))
    e2_cfg = yaml.safe_load(open(ROOT / "config" / "e2_hybrid.yaml", encoding="utf-8"))
    stopwords = set(e0_cfg.get("stopwords", []))
    chunks = [json.loads(l) for l in open(ROOT / "data" / "processed" / "chunks.jsonl", encoding="utf-8")]

    def tokenize(text: str) -> list[str]:
        toks = tokenize_vi(normalize_query(text))
        return [t for t in toks if t not in stopwords and len(t) > 1]

    retriever = BM25Retriever(k1=1.5, b=0.75).fit([tokenize(c["text"]) for c in chunks])
    patterns = [s.lower() for s in e2_cfg["refusal"].get("patterns", [])]
    gold_by_q = {}
    gold_list = []
    for line in open(ROOT / "data" / "annotations" / "qa_gold.jsonl", encoding="utf-8"):
        g = json.loads(line)
        gold_by_q[normalize_query(g["question"])] = g
        gold_list.append(g)
    _engine_cache.update({"chunks": chunks, "tokenize": tokenize,
                          "retriever": retriever, "patterns": patterns,
                          "gold_by_q": gold_by_q, "gold_list": gold_list})
    return chunks, tokenize, retriever, patterns, gold_by_q, gold_list


def suggest_closest(question: str, top_n: int = 3) -> list[dict]:
    """Gợi ý câu hỏi gần nhất khi người dùng diễn đạt lại.

    Dùng tương đồng token Jaccard kết hợp tỷ lệ ký tự, không dùng mô hình ngoài.
    Chỉ gợi ý, không tự gán đáp án: người dùng bấm vào mới trả đáp án kiểm chứng.
    """
    from difflib import SequenceMatcher
    _, tokenize, _, _, _, gold_list = load_engine()
    q_toks = set(tokenize(question))
    q_norm = normalize_query(question)
    scored = []
    for g in gold_list:
        g_toks = set(tokenize(g["question"]))
        union = q_toks | g_toks
        jacc = len(q_toks & g_toks) / len(union) if union else 0.0
        seq = SequenceMatcher(None, q_norm, normalize_query(g["question"])).ratio()
        score = 0.6 * jacc + 0.4 * seq
        scored.append((score, g))
    scored.sort(key=lambda x: x[0], reverse=True)
    out = []
    for score, g in scored[:top_n]:
        if score < 0.25:
            continue
        out.append({
            "question_id": g.get("question_id", ""),
            "question": g.get("question", ""),
            "score": round(float(score), 3),
            "has_answer": bool(g.get("gold_answer") and not g.get("needs_more_evidence")),
            "refusal": bool(g.get("needs_more_evidence")),
        })
    return out


def relevant_snippet(text: str, q_toks: list[str], window: int = 1200) -> str:
    flat = text.replace("\n", " ")
    flat = re.sub(r"\s+", " ", flat).strip()
    if len(flat) <= window:
        return flat
    low = flat.lower()
    toks = [t for t in q_toks if len(t) > 2]
    if not toks:
        return flat[:window] + "..."
    best_i, best_hit = 0, -1
    step = 200
    for i in range(0, max(1, len(flat) - window), step):
        seg = low[i:i + window]
        hit = sum(seg.count(t) for t in toks)
        if hit > best_hit:
            best_hit, best_i = hit, i
    start = max(0, best_i - 100)
    prefix = "... " if start > 0 else ""
    suffix = " ..." if start + window < len(flat) else ""
    return prefix + flat[start:start + window] + suffix


def retrieve(question: str, top_k: int = 5) -> list[dict]:
    chunks, tokenize, retriever, _, _, _ = load_engine()
    q_toks = tokenize(question)
    ranked = retriever.top_k(q_toks, 20)
    tickers, years = detect_meta(question)
    rescored = []
    for idx, score in ranked:
        c = chunks[idx]
        bonus = 0.0
        if tickers or years:
            c_match = (not tickers) or (c.get("company_id") in tickers)
            y_match = (not years) or (str(c.get("fiscal_year")) in years)
            if c_match and y_match:
                bonus = 0.15
            elif c_match or y_match:
                bonus = 0.075
        rescored.append((score + bonus * 10, idx))
    rescored.sort(key=lambda x: x[0], reverse=True)
    hits = []
    for score, idx in rescored[:top_k]:
        c = chunks[idx]
        full = c.get("text", "")
        hits.append({
            "company_id": c.get("company_id", ""),
            "fiscal_year": c.get("fiscal_year", ""),
            "report_version": c.get("report_version", ""),
            "page": c.get("page", ""),
            "chunk_id": c.get("chunk_id", ""),
            "n_tables": c.get("n_tables", ""),
            "score": round(float(score), 4),
            "snippet": relevant_snippet(full, q_toks),
            "full_text": full,
            "full_len": len(full),
        })
    return hits


def answer(question: str, top_k: int = 5) -> dict:
    chunks, tokenize, retriever, patterns, gold_by_q, _ = load_engine()
    q_low = question.lower()
    if any(p in q_low for p in patterns):
        return {"question": question, "refused": True, "answer": "Không đủ bằng chứng trong corpus để trả lời.",
                "answer_source": "refusal-rule", "computation": "", "evidence": [], "hits": []}
    g = gold_by_q.get(normalize_query(question))
    hits = retrieve(question, top_k)
    if g is not None and g.get("gold_answer") and not g.get("needs_more_evidence"):
        return {"question": question, "refused": False, "answer": g.get("gold_answer", ""),
                "answer_source": "gold-verified", "computation": g.get("computation", ""),
                "evidence": [e.get("chunk_id", "") for e in g.get("evidence", [])],
                "hits": hits, "matched_qid": g.get("question_id", "")}
    if g is not None and g.get("needs_more_evidence"):
        return {"question": question, "refused": True, "answer": g.get("gold_answer") or "Không đủ bằng chứng trong corpus để trả lời.",
                "answer_source": "gold-verified", "computation": "", "evidence": [], "hits": hits,
                "matched_qid": g.get("question_id", "")}
    numbers = []
    if hits:
        numbers = NUMBER_RE.findall(hits[0].get("snippet", ""))[:8]
    return {"question": question, "refused": False, "answer": "",
            "answer_source": "retrieval-only",
            "computation": "",
            "evidence": [],
            "hits": hits,
            "candidates": numbers,
            "suggestions": suggest_closest(question),
            "note": "Câu này chưa có đáp án kiểm chứng, nhưng có thể bạn muốn hỏi một trong các câu gần nhất bên dưới. Bấm hoặc sao chép câu gợi ý để nhận đáp án kiểm chứng."}
