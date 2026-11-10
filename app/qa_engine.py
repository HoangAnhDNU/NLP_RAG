"""Engine dùng chung cho demo CLI và Streamlit (Mục 6.1).

Pipeline sinh đáp án từ truy hồi, không đọc thuộc gold_answer:
1. Từ chối theo mẫu ngoài corpus trong `config/e2_hybrid.yaml`.
2. Trích metadata công ty/năm/bản/đơn vị/chỉ tiêu.
3. Truy hồi BM25 cộng điểm metadata trên 40 báo cáo (2407 chunk).
4. Lookup có cấu trúc trên `table_records.jsonl` trước, hybrid RAG sau.
5. Ghép top-k chunk thành CONTEXT có citation, bộ sinh đáp án chỉ dùng
   CONTEXT theo `config/answer_policy.yaml`, không dùng kiến thức ngoài.
6. Hiển thị đáp án kèm phép tính, chunk chứng cứ, đường dẫn gốc và số trang.

Gold trong `data/annotations/qa_gold.jsonl` chỉ dùng offline để chấm điểm,
không dùng làm đáp án trong demo.
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
from src.retrieval.answer_policy import (  # noqa: E402
    citation_complete,
    decide_status,
    detect_retrieval_conflict,
)
from src.retrieval.bm25 import BM25Retriever  # noqa: E402
from src.retrieval.table_lookup import (  # noqa: E402
    convert_value,
    find_by_code,
    format_number,
    lookup_records,
    parse_target_unit,
    resolve_tickers,
)

TICKERS = ["HPG", "HSG", "NKG", "MSR"]
COMPANY_NAMES = {
    "HPG": "CTCP Tập đoàn Hòa Phát",
    "HSG": "CTCP Tập đoàn Hoa Sen",
    "NKG": "CTCP Thép Nam Kim",
    "MSR": "CTCP Masan High-Tech Materials",
}
YEAR_RE = re.compile(r"\b(20[0-2]\d)\b")
NUMBER_RE = re.compile(r"\(?[\d.]{4,}\)?|\d[\d.,]*\s*(?:VND|đồng|%|tỷ|triệu|nghìn)?", re.IGNORECASE)

_table_cache: dict = {}
_engine_cache: dict = {}


def load_table_records() -> list[dict]:
    if _table_cache.get("records") is not None:
        return _table_cache["records"]
    path = ROOT / "data" / "processed" / "table_records.jsonl"
    recs: list[dict] = []
    if path.exists():
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line:
                try:
                    recs.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    _table_cache["records"] = recs
    return recs


def extract_entities(question: str) -> dict:
    tickers = resolve_tickers(question)
    _, years_raw = detect_meta(question)
    low = (question or "").lower()
    version = ""
    if any(k in low for k in ["công ty mẹ", "báo cáo riêng", "bản riêng", "riêng"]):
        version = "separate"
    elif any(k in low for k in ["hợp nhất", "hop nhat", "consolidated"]):
        version = "consolidated"
    unit = parse_target_unit(question)
    # Đoán chỉ tiêu bằng bản ghi bảng khớp nhất
    indicator = ""
    try:
        recs = load_table_records()
        scored = lookup_records(recs, tickers, years_raw, version, question, min_score=0.2)
        if scored:
            indicator = scored[0][1].get("metric", "")
    except Exception:
        indicator = ""
    return {
        "companies": tickers,
        "company_names": [COMPANY_NAMES.get(t, t) for t in tickers],
        "years": years_raw,
        "report_version": version,
        "target_unit": unit,
        "indicator_guess": indicator,
    }


def highlight_text(snippet: str, question: str) -> str:
    # Only bold meaningful numbers: thousand groups, decimals, percents.
    # Skip small ordinal numbers.
    marked = snippet or ""
    num_pat = r"\(?\d{1,3}(?:[.\s]\d{3})+(?:,\d+)?\)?(?:\s?%)?|\b\d+,\d+\b|\b\d+\.\d+\b|\b\d+\s?%"
    marked = re.sub(f"({num_pat})", r"**\1**", marked)
    _, tokenize, _, _, _, _ = load_engine()
    try:
        qtoks = [t for t in tokenize(question) if len(t) > 3][:12]
        for tok in sorted(set(qtoks), key=len, reverse=True):
            marked = re.sub(rf"(?i)\b({re.escape(tok)})\b", r"**\1**", marked)
    except Exception:
        pass
    # Tranh in dam chong nhau qua da
    marked = marked.replace("****", "")
    marked = re.sub(r"\*{3,}", "**", marked)
    return marked


def get_chunk_tables(chunk_id: str, limit: int = 10) -> list[dict]:
    recs = load_table_records()
    rows = [r for r in recs if r.get("source_chunk_id") == chunk_id]
    rows.sort(key=lambda r: (r.get("table_index", 0), str(r.get("metric_code", ""))))
    return rows[:limit]


def detect_conflict_warning(question: str, hits: list[dict], entities: dict) -> str:
    if not hits:
        return ""
    tickers = entities.get("companies", [])
    years = entities.get("years", [])
    version = entities.get("report_version", "")
    top1 = hits[0] if hits else {}
    # Chi canh bao khi top-1 lech thuc the duoc hoi: sai cong ty, sai nam,
    # sai ban bao cao, hoac top nguon lan lon nhieu thuc the khac nhau.
    if len(tickers) == 1 and len(set(years)) == 1:
        asked_c = tickers[0]
        asked_y = str(years[0])
        top_c = str(top1.get("company_id", ""))
        top_y = str(top1.get("fiscal_year", ""))
        top_v = str(top1.get("report_version", ""))
        mismatch = []
        if top_c and top_c != asked_c:
            mismatch.append(f"công ty top-1 là {top_c}, câu hỏi hỏi {asked_c}")
        if top_y and top_y != asked_y:
            mismatch.append(f"năm top-1 là {top_y}, câu hỏi hỏi {asked_y}")
        if version and top_v and top_v != version:
            mismatch.append(f"bản top-1 là {top_v}, câu hỏi hỏi {version}")
        if mismatch:
            return ("Cảnh báo mâu thuẫn: " + "; ".join(mismatch) + ". "
                    "Con số trả lời chỉ tin được khi trích đúng công ty, năm và bản được hỏi.")
        comps = {h.get("company_id", "") for h in hits[:5] if h.get("company_id")}
        yrs = {str(h.get("fiscal_year", "")) for h in hits[:5] if h.get("fiscal_year")}
        if len(comps) > 2 or len(yrs) > 2:
            return ("Lưu ý: top nguồn lẫn nhiều công ty/năm khác nhau "
                    f"({', '.join(sorted(comps))}; "
                    f"{', '.join(sorted(yrs))}). "
                    "Hãy đối chiếu chunk có đúng công ty và năm được hỏi trước khi tin con số.")
    return ""


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
    """Gợi ý câu hỏi gần nhất khi pipeline không sinh được đáp án chắc chắn.

    Chỉ gợi ý câu hỏi (không kèm đáp án): người dùng bấm vào sẽ chạy lại
    toàn bộ pipeline RAG để sinh đáp án từ CONTEXT, không đọc thuộc gold.
    Danh sách câu hỏi lấy từ tập đánh giá offline, không dùng gold_answer.
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


def chunk_to_hit(c: dict, question: str, q_toks: list[str], score: float = 0.0) -> dict:
    full = c.get("text", "")
    snip = relevant_snippet(full, q_toks)
    return {
        "company_id": c.get("company_id", ""),
        "fiscal_year": c.get("fiscal_year", ""),
        "report_version": c.get("report_version", ""),
        "page": c.get("page", ""),
        "chunk_id": c.get("chunk_id", ""),
        "document_id": c.get("document_id", ""),
        "local_path": c.get("local_path", ""),
        "source_path": f"{c.get('local_path', '')} :: {c.get('document_id', '')} trang {c.get('page', '')}",
        "unit": c.get("unit", ""),
        "n_tables": c.get("n_tables", ""),
        "score": round(float(score), 4),
        "snippet": snip,
        "snippet_highlight": highlight_text(snip, question),
        "table_rows": get_chunk_tables(c.get("chunk_id", ""), limit=5),
        "full_text": full,
        "full_len": len(full),
    }


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
        hits.append(chunk_to_hit(c, question, q_toks, score))
    return hits


def generate_from_context(question: str, hits: list[dict]) -> dict:
    """Bộ sinh đáp án offline thay cho LLM: chỉ dùng CONTEXT truy hồi.

    Hợp đồng giống LLM trong `config/answer_policy.yaml`:
    chỉ dùng chunk/table được cấp, mỗi số kèm citation, thiếu thì rỗng
    để tầng trên đánh refused/partial_answer. Không đọc `qa_gold.jsonl`.
    """
    tickers = resolve_tickers(question)
    years = YEAR_RE.findall(question or "")
    low = (question or "").lower()
    version = ""
    if any(k in low for k in ["công ty mẹ", "báo cáo riêng", "bản riêng", "riêng"]):
        version = "separate"
    elif any(k in low for k in ["hợp nhất", "hop nhat", "consolidated"]):
        version = "consolidated"
    target_unit = parse_target_unit(question)
    recs = load_table_records()
    is_margin = ("biên" in low or "bien" in low) and ("gộp" in low or "gop" in low)
    if is_margin:
        gross = find_by_code(recs, tickers, years, version, ["20"], ["lợi nhuận gộp", "loi nhuan gop"])
        rev = find_by_code(recs, tickers, years, version, ["10"], ["doanh thu thuần", "doanh thu thuan"])
        if gross and rev and rev.get("value"):
            try:
                margin = float(gross["value"]) / float(rev["value"]) * 100.0
                unit = target_unit or "%"
                ans = f"{format_number(margin)} {unit}".strip()
                comp = (f"Biên gộp = {gross.get('value_raw', '')} {gross.get('unit', '')} / "
                        f"{rev.get('value_raw', '')} {rev.get('unit', '')} x 100 = {ans}.")
                ev = [gross.get("source_chunk_id", ""), rev.get("source_chunk_id", "")]
                return {"answer": ans, "computation": comp, "evidence": [e for e in ev if e],
                        "answer_source": "rag-margin", "struct_hit": gross}
            except (ValueError, ZeroDivisionError):
                pass
    cands = lookup_records(recs, tickers, years, version, question, min_score=0.3)
    if cands:
        # Uu tien ban ghi cung don vi voi cau hoi (VD hoi % thi lay cot %,
        # khong lay cot VND). Tranh truong hop convert sai don vi.
        pool = cands
        if target_unit:
            same = [c for c in cands if (c[1].get("unit", "") or "") == target_unit]
            if same:
                pool = same
        top = pool[0][1]
        conv = convert_value(float(top["value"]), top.get("unit", ""), target_unit or top.get("unit", ""))
        if conv is None:
            conv = float(top["value"])
            unit = top.get("unit", "")
        else:
            unit = target_unit or top.get("unit", "")
        ans = f"{format_number(conv)} {unit}".strip()
        if (top.get("unit", "") or "") == "%" or (target_unit or "") == "%":
            comp = (f"{top.get('value_raw', '')} (ô bảng, đơn vị %) = {ans}. "
                    f"Nguồn {top.get('source_chunk_id', '')} trang {top.get('page', '')}.")
        else:
            comp = (f"{top.get('value_raw', '')} {top.get('unit', '')} = "
                    f"{float(top['value']):,.0f} VND = {ans}.")
        return {"answer": ans, "computation": comp,
                "evidence": [top.get("source_chunk_id", "")],
                "answer_source": "rag-table-lookup", "struct_hit": top}
    return {"answer": "", "computation": "", "evidence": [],
            "answer_source": "retrieval-only", "struct_hit": None}


def build_context_block(hits: list[dict], max_chars: int = 1200) -> str:
    lines: list[str] = []
    for h in hits:
        text = (h.get("snippet", h.get("full_text", "")) or "").replace("\n", " ")
        text = re.sub(r"\s+", " ", text).strip()[:max_chars]
        lines.append(
            f"- chunk_id={h.get('chunk_id', '')} | page={h.get('page', '')} | "
            f"company={h.get('company_id', '')} | year={h.get('fiscal_year', '')} | "
            f"report={h.get('report_version', '')} | text={text}"
        )
    return "\n".join(lines)


def attach_status(question: str, predicted_answer: str, hits: list[dict], refused_by_rule: bool = False) -> dict:
    tickers = resolve_tickers(question)
    years = YEAR_RE.findall(question or "")
    top_for_status = [
        {
            "chunk_id": h.get("chunk_id", ""),
            "page": h.get("page", ""),
            "company_id": h.get("company_id", ""),
            "fiscal_year": h.get("fiscal_year", ""),
        }
        for h in (hits or [])[:5]
    ]
    conflict = detect_retrieval_conflict(tickers, years, top_for_status)
    decided = decide_status(
        question,
        predicted_answer,
        top_for_status,
        tickers=tickers if len(tickers) == 1 else None,
        years=years if len(set(years)) == 1 else None,
        conflict=conflict,
        refused_by_rule=refused_by_rule,
    )
    return {
        "answer_status": decided["status"],
        "status_reason": decided.get("reason", ""),
        "citation_complete": bool(top_for_status and citation_complete(top_for_status)),
    }


def enrich(question: str, out: dict) -> dict:
    entities = extract_entities(question)
    hits = out.get("hits", [])
    out["entities"] = entities
    out["conflict_warning"] = detect_conflict_warning(question, hits, entities)
    # Highlight san cho tung hit khi goi truc tiep qua retrieve
    for h in hits:
        if "snippet_highlight" not in h:
            h["snippet_highlight"] = highlight_text(h.get("snippet", ""), question)
        if "table_rows" not in h:
            h["table_rows"] = get_chunk_tables(h.get("chunk_id", ""), limit=5)
        if "source_path" not in h:
            h["source_path"] = f"{h.get('local_path', '')} :: {h.get('document_id', '')} trang {h.get('page', '')}"
    return out


def answer(question: str, top_k: int = 5) -> dict:
    # Pipeline RAG thuần: không đọc gold_answer trong demo.
    # Gold chỉ dùng offline để chấm điểm, không dùng làm đáp án.
    _, _, _, patterns, _, _ = load_engine()
    q_low = question.lower()
    if any(p in q_low for p in patterns):
        out = {"question": question, "refused": True, "answer": "Không đủ bằng chứng trong corpus để trả lời.",
                "answer_source": "refusal-rule", "computation": "", "evidence": [], "hits": [], "context": ""}
        out.update(attach_status(question, out["answer"], [], refused_by_rule=True))
        return enrich(question, out)
    chunks, tokenize, _, _, _, _ = load_engine()
    q_toks = tokenize(question)
    hits = retrieve(question, top_k)
    gen = generate_from_context(question, hits)
    # Chen chunk chung cu cua dap an sinh ra vao top hits: dam bao CONTEXT
    # hien thi dung nguon da dung, tranh truong hop BM25 day chunk khac len.
    ev_ids: list[str] = []
    for cid in (gen.get("evidence") or []):
        if cid and cid not in ev_ids:
            ev_ids.append(cid)
    if ev_ids:
        chunk_map = {c.get("chunk_id", ""): c for c in chunks}
        have = {h.get("chunk_id", "") for h in hits}
        prepend: list[dict] = []
        for cid in ev_ids:
            if cid not in have and cid in chunk_map:
                prepend.append(chunk_to_hit(chunk_map[cid], question, q_toks, score=999.0))
                have.add(cid)
        hits = (prepend + [h for h in hits if h.get("chunk_id", "") in have])[:max(top_k, len(prepend))]
        # Sap xep de chunk chung cu dung top-1 theo dung thu tu evidence.
        order = {cid: i for i, cid in enumerate(ev_ids)}
        hits = sorted(hits, key=lambda h: order.get(h.get("chunk_id", ""), 999))
    context = build_context_block(hits)
    if gen.get("answer"):
        out = {"question": question, "refused": False, "answer": gen["answer"],
                "answer_source": gen.get("answer_source", "rag-table-lookup"),
                "computation": gen.get("computation", ""),
                "evidence": gen.get("evidence", []),
                "hits": hits, "context": context}
        out.update(attach_status(question, out["answer"], hits))
        return enrich(question, out)
    numbers = []
    if hits:
        numbers = NUMBER_RE.findall(hits[0].get("snippet", ""))[:8]
    out = {"question": question, "refused": False, "answer": "",
            "answer_source": "retrieval-only",
            "computation": "",
            "evidence": [],
            "hits": hits,
            "context": context,
            "candidates": numbers,
            "suggestions": suggest_closest(question),
            "note": "Pipeline không tìm được ô bảng khớp chắc chắn cho câu này, nên không sinh đáp án. Hãy đối chiếu top chunks bên dưới hoặc chọn một câu gợi ý gần nhất."}
    out.update(attach_status(question, "", hits))
    return enrich(question, out)
