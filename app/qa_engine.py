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
from src.retrieval.pipeline_two_stage import minmax  # noqa: E402
from src.retrieval.table_lookup import (  # noqa: E402
    CORPUS_YEARS,
    REFUSAL_TEXT_DEFAULT,
    check_refusal,
    detect_query_meta,
    extract_years,
    lookup_records,
    normalize_ocr_vi,
    resolve_tickers,
    strip_accents,
    synthesize_answer,
)

TICKERS = ["HPG", "HSG", "NKG", "MSR"]
COMPANY_NAMES = {
    "HPG": "CTCP Tập đoàn Hòa Phát",
    "HSG": "CTCP Tập đoàn Hoa Sen",
    "NKG": "CTCP Thép Nam Kim",
    "MSR": "CTCP Masan High-Tech Materials",
}
YEAR_RE = re.compile(r"\b((?:19|20)\d{2})\b")
NUMBER_RE = re.compile(r"\(?[\d.]{4,}\)?|\d[\d.,]*\s*(?:VND|đồng|%|tỷ|triệu|nghìn)?", re.IGNORECASE)
_FINANCIAL_ACRONYMS = {
    "HPG", "HSG", "NKG", "MSR", "CTCP", "TNHH", "BCTC", "VND", "VNĐ", "USD", "EUR",
    "GTGT", "EPS", "ROE", "ROA", "EBIT", "EBITDA", "LNST", "LNTT", "DTT", "TSNH",
    "TSDH", "VCSH", "HĐQT", "HĐKD", "KQHĐKD", "CĐKT", "LCTT", "TSCĐ", "XDCB", "NVL",
    "BĐS", "TNDN", "TNCN", "BHXH", "VAT", "IFRS", "VAS", "SXKD", "QLDN", "HTK",
    "KCN", "CEO", "CFO", "NIM", "CAR", "NPL", "TP", "HCM", "HN", "VN", "CP", "CK",
}
_GENERIC_Q_TOKENS = {
    "hpg", "hsg", "nkg", "msr", "hòa", "phát", "hoa", "sen", "nam", "kim", "masan",
    "high", "tech", "materials", "năm", "hợp", "nhất", "công", "ty", "tập", "đoàn",
    "cổ", "phần", "ctcp", "tnhh", "bao", "nhiêu", "đồng", "tỷ", "triệu", "nghìn",
    "trăm", "bằng", "giá", "trị", "chỉ", "tiêu", "báo", "cáo", "tài", "chính",
    "kết", "thúc", "ngày", "tháng", "riêng", "bản", "tại", "của", "trong", "cho",
    "gồm", "những", "khoản", "nào", "gì", "nội", "dung", "như", "thế", "sao", "vì",
}

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
    meta = detect_query_meta(question, use_aliases=True)
    tickers = meta["tickers"]
    years_raw = meta["years"]
    version = meta["version"]
    unit = meta["target_unit"]
    indicator = ""
    try:
        recs = load_table_records()
        scored = lookup_records(
            recs,
            tickers,
            years_raw,
            version,
            question,
            min_score=0.35,
            target_unit=unit,
            period_side=meta["period_side"],
        )
        if scored:
            indicator = scored[0][1].get("metric", "")
        else:
            low_noacc = strip_accents((question or "").lower())
            if ("bien" in low_noacc and "gop" in low_noacc) and not check_refusal(question)[0]:
                indicator = "Biên lợi nhuận gộp (Lợi nhuận gộp / Doanh thu thuần)"
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
    tickers = resolve_tickers(question)
    years = extract_years(question)
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
    if not chunks:
        return []
    q_toks = tokenize(question)
    cand_k = max(20, top_k)
    raw_all = retriever.score(q_toks)
    if not raw_all:
        return []
    global_order = sorted(range(len(chunks)), key=lambda i: raw_all[i], reverse=True)

    meta = detect_query_meta(question, use_aliases=True)
    tickers = meta["tickers"]
    all_years = meta["years"]
    version = meta["version"]
    corpus_years = [y for y in all_years if y.isdigit() and int(y) in CORPUS_YEARS]
    upper_tokens = set(re.findall(r"\b[A-Z]{2,6}\b", question or ""))
    has_unknown_ticker = bool((upper_tokens - _FINANCIAL_ACRONYMS) and not tickers)
    has_outside_only_year = bool(all_years and not corpus_years)
    use_meta_pool = bool((tickers or corpus_years) and not has_unknown_ticker and not has_outside_only_year)

    pool_idxs: list[int] = []
    if use_meta_pool:
        strict_idxs = [
            i
            for i in global_order
            if raw_all[i] > 0.0
            and ((not tickers) or chunks[i].get("company_id") in tickers)
            and ((not corpus_years) or str(chunks[i].get("fiscal_year")) in corpus_years)
        ]
        if len(strict_idxs) >= top_k:
            target_pairs = [
                (t, y)
                for t in (tickers or [""])
                for y in (corpus_years or [""])
            ]
            if len(target_pairs) > 1:
                buckets: dict[tuple[str, str], list[int]] = {pair: [] for pair in target_pairs}
                for i in strict_idxs:
                    c = chunks[i]
                    t_key = c.get("company_id", "") if tickers else ""
                    y_key = str(c.get("fiscal_year", "")) if corpus_years else ""
                    if (t_key, y_key) in buckets:
                        buckets[(t_key, y_key)].append(i)
                pos_b = 0
                while len(pool_idxs) < cand_k:
                    added = False
                    for pair in target_pairs:
                        lst = buckets[pair]
                        if pos_b < len(lst) and lst[pos_b] not in pool_idxs:
                            pool_idxs.append(lst[pos_b])
                            added = True
                            if len(pool_idxs) >= cand_k:
                                break
                    if not added:
                        break
                    pos_b += 1
            for i in strict_idxs:
                if i not in pool_idxs:
                    pool_idxs.append(i)
                if len(pool_idxs) >= cand_k:
                    break
        else:
            seen_p: set[int] = set()
            partial_idxs = [
                i
                for i in global_order
                if raw_all[i] > 0.0
                and (
                    (tickers and chunks[i].get("company_id") in tickers)
                    or (corpus_years and str(chunks[i].get("fiscal_year")) in corpus_years)
                )
            ]
            for i in strict_idxs + partial_idxs + global_order:
                if i not in seen_p:
                    seen_p.add(i)
                    pool_idxs.append(i)
                if len(pool_idxs) >= cand_k:
                    break
    else:
        pool_idxs = global_order[:cand_k]

    raw_scores = [float(raw_all[i]) for i in pool_idxs]
    norm_scores = minmax(raw_scores) if raw_scores else []
    rescored: list[tuple[int, int, float, float, int]] = []
    for pos, idx in enumerate(pool_idxs):
        raw_s = float(raw_all[idx])
        if raw_s <= 0.0:
            rescored.append((0, 0, 0.0, 0.0, idx))
            continue
        c = chunks[idx]
        bonus = 0.0
        match_tier = 0
        c_match = (not tickers) or (c.get("company_id") in tickers)
        y_match = (not corpus_years) or (str(c.get("fiscal_year")) in corpus_years)
        if tickers or corpus_years:
            if c_match and y_match:
                bonus = 0.15
                match_tier = 2 if use_meta_pool else 0
            elif c_match or y_match:
                bonus = 0.075
                match_tier = 1 if use_meta_pool else 0
        ver_tier = 1 if (version and c.get("report_version") == version) or (not version and c.get("report_version") == "consolidated") else 0
        total_s = norm_scores[pos] + bonus
        rescored.append((match_tier, ver_tier, total_s, raw_s, idx))
    rescored.sort(key=lambda x: (x[0], x[1], x[2], x[3]), reverse=True)
    hits = []
    for _, _, total_s, raw_s, idx in rescored[:top_k]:
        c = chunks[idx]
        clamped_s = max(0.0, min(1.0, float(total_s)))
        hit = chunk_to_hit(c, question, q_toks, clamped_s)
        hit["raw_bm25"] = round(raw_s, 4)
        hits.append(hit)
    return hits


def generate_from_context(question: str, hits: list[dict]) -> dict:
    """Bộ sinh đáp án từ structured lookup thống nhất trên table_lookup.py + CONTEXT truy hồi."""
    _, _, _, patterns, _, _ = load_engine()
    recs = load_table_records()
    synth = synthesize_answer(
        question,
        recs,
        min_score=0.4,
        extra_refusal_patterns=patterns,
        refusal_text=REFUSAL_TEXT_DEFAULT,
    )
    if synth["refused"]:
        return {
            "answer": synth["answer"],
            "computation": "",
            "evidence": [],
            "answer_source": "refusal-rule",
            "struct_hit": None,
            "refused": True,
            "refusal_reason": synth["refusal_reason"],
            "lookup_score": 0.0,
        }
    src_map = {
        "computed_margin": "rag-margin",
        "computed_diff": "rag-table-diff",
        "table_lookup": "rag-table-lookup",
    }
    if synth["answer"]:
        recs_ev = synth["evidence_records"]
        return {
            "answer": synth["answer"],
            "computation": synth["computation"],
            "evidence": synth["evidence_chunk_ids"],
            "answer_source": src_map.get(synth["answer_source"], "rag-table-lookup"),
            "struct_hit": recs_ev[0] if recs_ev else None,
            "refused": False,
            "lookup_score": synth["lookup_score"],
            "predicted_year": synth["predicted_year"],
            "predicted_company": synth["predicted_company"],
        }
    return {
        "answer": "",
        "computation": "",
        "evidence": [],
        "answer_source": "retrieval-only",
        "struct_hit": None,
        "refused": False,
        "lookup_score": 0.0,
    }


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
    years = extract_years(question)
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
        tickers=tickers or None,
        years=years or None,
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


def _should_refuse_unmatched(question: str, hits: list[dict], q_toks: list[str]) -> bool:
    """Refuse in interactive QA when retrieval has no valid corpus match or targets an outside entity."""
    if not hits or all(float(h.get("raw_bm25", h.get("score", 0.0))) <= 0.0 for h in hits):
        return True
    tickers = resolve_tickers(question)
    years = extract_years(question)
    # Explicit unknown ticker outside HPG/HSG/NKG/MSR
    upper_tokens = set(re.findall(r"\b[A-Z]{2,6}\b", question or ""))
    unknown_tickers = upper_tokens - _FINANCIAL_ACRONYMS
    if unknown_tickers and not tickers:
        return True
    # Years exclusively outside 2020-2024 corpus range
    if years and not any(y.isdigit() and int(y) in CORPUS_YEARS for y in years):
        return True
    # Low query content coverage across top retrieved chunks (off-topic / outside corpus)
    q_content = [t for t in q_toks if t not in _GENERIC_Q_TOKENS and not t.isdigit() and len(t) > 1]
    if not tickers and not years:
        bctc_domain = {"doanh", "thu", "lợi", "nhuận", "tài", "sản", "nợ", "vốn", "lưu", "chuyển", "tiền", "khấu", "hao", "thuế", "cổ", "tức", "biên", "gộp"}
        if not (set(q_content) & bctc_domain):
            return True
    if q_content:
        top3_text = normalize_ocr_vi(" ".join(h.get("full_text", h.get("snippet", "")) for h in hits[:3]))
        top3_tokens = set(re.findall(r"[a-zà-ỹ0-9_+-]+", top3_text))
        covered = sum(1 for t in set(q_content) if normalize_ocr_vi(t) in top3_tokens)
        cov_ratio = covered / len(set(q_content))
        if cov_ratio < 0.35 or (not tickers and cov_ratio < 0.6):
            return True
    return False


def answer(question: str, top_k: int = 5) -> dict:
    # Pipeline RAG thuần: không đọc gold_answer trong demo.
    # Gold chỉ dùng offline để chấm điểm, không dùng làm đáp án.
    chunks, tokenize, _, patterns, _, _ = load_engine()
    refused, _ = check_refusal(question, extra_patterns=patterns)
    if refused:
        out = {
            "question": question,
            "refused": True,
            "answer": REFUSAL_TEXT_DEFAULT,
            "answer_source": "refusal-rule",
            "computation": "",
            "evidence": [],
            "hits": [],
            "context": "",
        }
        out.update(attach_status(question, out["answer"], [], refused_by_rule=True))
        return enrich(question, out)
    q_toks = tokenize(question)
    hits = retrieve(question, top_k)
    gen = generate_from_context(question, hits)
    if gen.get("refused"):
        out = {
            "question": question,
            "refused": True,
            "answer": gen.get("answer") or REFUSAL_TEXT_DEFAULT,
            "answer_source": "refusal-rule",
            "computation": "",
            "evidence": [],
            "hits": [],
            "context": "",
        }
        out.update(attach_status(question, out["answer"], [], refused_by_rule=True))
        return enrich(question, out)

    # Chèn chunk chứng cứ của đáp án sinh ra vào top hits với điểm lookup thực (<= 1.0)
    ev_ids: list[str] = []
    for cid in (gen.get("evidence") or []):
        if cid and cid not in ev_ids:
            ev_ids.append(cid)
    if ev_ids:
        chunk_map = {c.get("chunk_id", ""): c for c in chunks}
        lookup_score = max(0.0, min(1.0, float(gen.get("lookup_score") or 0.9)))
        top_hit_score = max((float(h.get("score", 0.0)) for h in hits), default=0.0)
        ev_score = round(max(0.0, min(1.0, max(lookup_score, top_hit_score))), 4)
        have = {h.get("chunk_id", "") for h in hits}
        for h in hits:
            if h.get("chunk_id", "") in ev_ids:
                h["score"] = round(max(float(h.get("score", 0.0)), ev_score), 4)
        prepend: list[dict] = []
        for cid in ev_ids:
            if cid not in have and cid in chunk_map:
                prepend.append(chunk_to_hit(chunk_map[cid], question, q_toks, score=ev_score))
                have.add(cid)
        hits = (prepend + [h for h in hits if h.get("chunk_id", "") in have])[:max(top_k, len(ev_ids))]
        order = {cid: i for i, cid in enumerate(ev_ids)}
        hits = sorted(
            hits,
            key=lambda h: (
                0 if h.get("chunk_id", "") in order else 1,
                order.get(h.get("chunk_id", ""), 999),
                -float(h.get("score", 0.0)),
            ),
        )
    context = build_context_block(hits)
    if gen.get("answer"):
        out = {
            "question": question,
            "refused": False,
            "answer": gen["answer"],
            "answer_source": gen.get("answer_source", "rag-table-lookup"),
            "computation": gen.get("computation", ""),
            "evidence": gen.get("evidence", []),
            "hits": hits,
            "context": context,
        }
        out.update(attach_status(question, out["answer"], hits))
        return enrich(question, out)

    if _should_refuse_unmatched(question, hits, q_toks):
        out = {
            "question": question,
            "refused": True,
            "answer": REFUSAL_TEXT_DEFAULT,
            "answer_source": "refusal-no-evidence",
            "computation": "",
            "evidence": [],
            "hits": hits,
            "context": context,
        }
        out.update(attach_status(question, out["answer"], hits, refused_by_rule=True))
        return enrich(question, out)

    numbers = NUMBER_RE.findall(hits[0].get("snippet", ""))[:8] if hits else []
    out = {
        "question": question,
        "refused": False,
        "answer": "",
        "answer_source": "retrieval-only",
        "computation": "",
        "evidence": [],
        "hits": hits,
        "context": context,
        "candidates": numbers,
        "suggestions": suggest_closest(question),
        "note": "Pipeline không tìm được ô bảng khớp chắc chắn cho câu này, nên không sinh đáp án. Hãy đối chiếu top chunks bên dưới hoặc chọn một câu gợi ý gần nhất.",
    }
    out.update(attach_status(question, "", hits))
    return enrich(question, out)
