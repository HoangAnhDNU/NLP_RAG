"""Tien ich dung chung cho pipeline hai tang E4-E7 (khong tai model ngoai).

Bao gom: tach metadata mo rong (cong ty, nam, ban, chi tieu),
RRF fusion, reranker nhe dang cross-encoder thay the minh bach,
table index rieng, contextual chunk tai thoi diem truy hoi.
"""

from __future__ import annotations

import re

TICKERS = ["HPG", "HSG", "NKG", "MSR"]
YEAR_RE = re.compile(r"\b(20[0-2]\d)\b")

METRIC_PATTERNS: list[tuple[str, str]] = [
    ("doanh thu thuan", r"doanh\s*thu\s*thua?n"),
    ("loi nhuan sau thue", r"lo?i\s*nhua?n\s*sau\s*thue?"),
    ("tien va tuong duong tien", r"tie?n.*tuong\s*duong.*tie?n"),
    ("lai co ban tren co phieu", r"la~i\s*co\s*ba?n|la?i\s*co\s*ba?n.*co?\s*phie?u"),
    ("bien loi nhuan gop", r"bie?n.*go?p"),
    ("von chu so huu", r"vo?n.*chu?\s*so?\s*hu?u"),
    ("vay va trai phieu", r"vay.*trai\s*phie?u|du\s*no?\s*vay"),
    ("ty le so huu", r"ty?\s*le?\s*so?\s*hu?u"),
    ("thu nhap thuan", r"thu\s*nha?p.*thua?n"),
    ("chi phi lai vay", r"chi\s*phi?\s*la~i\s*vay|chi\s*phi?\s*la?i\s*vay"),
    ("tien thu lao", r"thu?\s*lao"),
    ("hang ton kho", r"to?n\s*kho"),
    ("tai san ngan han", r"ta?i\s*sa?n\s*nga?n\s*ha?n"),
]

METRIC_SYNONYMS: dict[str, list[str]] = {
    "doanh thu thuan": ["doanh thu ban hang", "doanh thu cung cap dich vu", "doanh thu thuan"],
    "loi nhuan sau thue": ["loi nhuan sau thue tndn", "loi nhuan sau thue", "lnst"],
    "tien va tuong duong tien": ["tien va tuong duong tien", "tien mat", "tien gui"],
    "von chu so huu": ["von chu so huu", "von chu", "equity"],
}


from src.retrieval.table_lookup import detect_report_version, resolve_tickers

def detect_meta_extended(question: str, use_aliases: bool = False) -> dict:
    up = question.upper()
    tickers = (
        resolve_tickers(question)
        if use_aliases
        else [t for t in TICKERS if re.search(rf"(?<![A-Z]){t}(?![A-Z])", up)]
    )
    years = YEAR_RE.findall(question)
    low = question.lower()
    version = detect_report_version(question)
    metric = ""
    for name, pat in METRIC_PATTERNS:
        if re.search(pat, low):
            metric = name
            break
    return {"tickers": tickers, "years": years, "version": version, "metric": metric}


def minmax(scores: list[float]) -> list[float]:
    lo, hi = min(scores), max(scores)
    if hi <= lo:
        return [0.0 for _ in scores]
    return [(s - lo) / (hi - lo) for s in scores]


def rrf_fuse(rank_lists: list[list[int]], k_rrf: int = 60) -> dict[int, float]:
    fused: dict[int, float] = {}
    for ranks in rank_lists:
        for rank, idx in enumerate(ranks, start=1):
            fused[idx] = fused.get(idx, 0.0) + 1.0 / (k_rrf + rank)
    return fused


def query_variants(question: str, meta: dict) -> list[str]:
    base = question.strip()
    out = [base]
    extras: list[str] = []
    extras.extend(meta.get("tickers", []))
    extras.extend(meta.get("years", []))
    if meta.get("version"):
        extras.append(meta["version"])
    if extras:
        out.append(base + " " + " ".join(extras))
    metric = meta.get("metric", "")
    if metric and metric in METRIC_SYNONYMS:
        out.append(" ".join(METRIC_SYNONYMS[metric]) + " " + " ".join(extras))
    seen: list[str] = []
    for q in out:
        if q not in seen:
            seen.append(q)
    return seen


def contextual_text(chunk: dict) -> str:
    header = (
        f"[CTY {chunk.get('company_id', '')} | Nam {chunk.get('fiscal_year', '')} "
        f"| Ban {chunk.get('report_version', '')} | Trang {chunk.get('page', '')} "
        f"| Don vi: {chunk.get('unit', '')} | Bang: {chunk.get('n_tables', '')}] "
    )
    return header + (chunk.get("text", "") or "")


def table_only_text(chunk: dict) -> str:
    text = chunk.get("text", "") or ""
    parts = re.findall(r"\[Bang \d+\][^\[]*", text)
    if parts:
        return " ".join(parts)
    return ""


def rerank_score(
    fused_norm: float,
    q_toks: set[str],
    chunk_toks: set[str],
    metric_hit: bool,
    meta_hit: bool,
    n_tables: int,
    w_fused: float = 0.5,
    w_cover: float = 0.3,
    w_metric: float = 0.1,
    w_meta: float = 0.1,
) -> float:
    if not q_toks:
        cover = 0.0
    else:
        cover = len(q_toks & chunk_toks) / max(1, len(q_toks))
    table_bonus = 0.05 if int(n_tables or 0) > 0 else 0.0
    return (
        w_fused * fused_norm
        + w_cover * cover
        + w_metric * (1.0 if metric_hit else 0.0)
        + w_meta * (1.0 if meta_hit else 0.0)
        + table_bonus
    )
