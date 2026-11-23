"""Chấm metric E0-E8, tách retrieval, citation, answer và refusal (Mục 4.6.5, RAGAS).

Đọc prediction CSV của một run và `qa_gold.jsonl`, tính trên dev và test:
- Retrieval (chỉ trên câu có evidence): recall@3, recall@5, recall@10,
  mrr@3, mrr@5, mrr@10, context_precision@5, context_recall@5.
  `recall@10` và `mrr@10` được tính trực tiếp qua `recall_mrr_at(..., 10)` trên
  toàn bộ danh sách `predicted_chunk_ids` (tới 10 chunk khi có >5 chunk), trong
  khi `recall@5`, `mrr@5`, `context_precision@5`, `context_recall@5` luôn tính
  chặt trên top-5 (`[:5]`).
- Citation: citation_precision_top1 (top-1 nằm trong evidence),
  citation_recall@5, citation_complete_rate (top-1 đủ chunk_id/page/company/year).
- Answer số (chỉ trên câu có gold_answer và không thiếu bằng chứng):
  numeric_match sau chuẩn hóa đơn vị, exact_match sau chuẩn hóa chuỗi.
- Answer status: answered / partial_answer / refused / ambiguous theo
  `src/retrieval/answer_policy.py` và `config/answer_policy.yaml` (hỗ trợ kiểm
  tra phủ đủ công ty/năm trên top-5 cho câu hỏi đa thực thể/đa năm).
- Period (nghiệp vụ tài chính): company_accuracy, year_accuracy (hỗ trợ so khớp
  tập năm dạng `2020|2021` trên cả gold và prediction), version_accuracy,
  period_accuracy (cả 3 đúng), page_accuracy (chỉ trên câu có source_page).
- Refusal: refusal_precision, refusal_recall, refusal_rate, false_answer_rate
  = 1 - (numeric đúng + từ chối đúng) / tổng số câu, kèm nhãn
  true_refusal / missed_refusal / false_refusal / true_answer.
- Unsupported_claim_rate: tỷ lệ câu trả lời có khẳng định số không xác minh được
  trong top-5 chunk qua `numbers_in_context(pred_answer, context)`. Mỗi chunk
  top-5 được phân tách ranh giới (`CHUNK_SEP`) và kiểm tra độc lập (không ghép
  cặp xuyên chunk). Mỗi con số trong `pred_answer` được chấp nhận nếu:
  (a) xuất hiện trực tiếp trong một chunk với đúng ngữ nghĩa (tách năm tiêu đề
  bảng kiểu `2022 VND | 2021 VND`, giữ tách bạch số tiền vs `%`), hoặc
  (b) khớp số trong chunk theo đúng tỷ lệ quy đổi đơn vị `(claimed_factor /
  chunk_base_factor)` (từ `đồng` `1.0`, `nghìn` `1e3`, `triệu` `1e6`, `tỷ` `1e9`,
  `trăm tỷ` `1e11`, `nghìn tỷ` `1e12`, sai số tương đối `1e-3`, từ chối lệch 100x/
  1000x đơn vị), hoặc (c) suy ra trong cùng chunk qua phép tính cơ bản (`a - b`
  trên cùng dòng hoặc chunk nhỏ `<= 8` số, `a + b` trên chunk nhỏ, `a / b * 100`
  trên cùng dòng / cùng cột lân cận `<= 3` dòng của bảng hoặc chunk nhỏ, `a / b`
  cho tỷ số không phải `%`, sai số tương đối `1e-3`); mọi số không thỏa đều bị
  gắn cờ là unsupported claim.
- Faithfulness và answer_relevancy dùng hai cột heuristic minh bạch
  (`faithfulness_heuristic = 1 - unsupported_claim_rate`,
  `answer_relevancy_heuristic = (numeric đúng + từ chối đúng) / tổng số câu`)
  vì pipeline không gọi LLM judge API.

Ví dụ:
    python src/evaluate/evaluate.py --run E0
    python src/evaluate/evaluate.py --run E3 --pred evaluation/test_predictions/test_predictions_E3.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import NamedTuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.retrieval.answer_policy import (  # noqa: E402
    citation_complete,
    decide_status,
    detect_retrieval_conflict,
    is_refusal,
    refusal_label,
)
from src.retrieval.table_lookup import resolve_tickers  # noqa: E402

REFUSAL_TEXT = "Không đủ bằng chứng trong corpus để trả lời."
CHUNK_SEP = "\n===CHUNK===\n"
NUM_RE = re.compile(r"(?:\(\s*-?\d+(?:[.,]\d+)*\s*\)|(?:(?<!\d)-)?\d+(?:[.,]\d+)*)%?")
YEAR_RE = re.compile(r"\b(20[0-2]\d)\b")
UNIT_SCALES = (1.0, 1e3, 1e6, 1e9, 1e11, 1e12)
REL_TOL = 1e-3

_UNIT_PHRASE_FACTORS: tuple[tuple[str, float], ...] = (
    (r"(?:nghìn\s*tỷ|nghin\s*ty)(?:\s*(?:vnd|vnđ|đồng))?", 1e12),
    (r"(?:trăm\s*tỷ|tram\s*ty)(?:\s*(?:vnd|vnđ|đồng))?", 1e11),
    (r"(?:tỷ|ty)\s*(?:vnd|vnđ|đồng)", 1e9),
    (r"(?:triệu|trieu)\s*(?:vnd|vnđ|đồng)", 1e6),
    (r"(?:nghìn|nghin|ngàn)\s*(?:vnd|vnđ|đồng)", 1e3),
)


class _ContextEntry(NamedTuple):
    val: float
    line_idx: int
    col_from_right: int
    unit_factors: frozenset[float]
    inline_factor: float | None
    is_pct: bool


def norm_answer(text: str) -> str:
    text = (text or "").strip().lower()
    return " ".join(text.split())


def parse_pipe_set(raw: object, upper: bool = False) -> set[str]:
    """Chuan hoa chuoi gia tri ngan cach bang `|` thanh tap hop (ho tro don/da nam, da cong ty)."""
    text = str(raw or "").strip()
    if not text:
        return set()
    return {
        part.strip().upper() if upper else part.strip()
        for part in text.split("|")
        if part.strip()
    }


def norm_num_token(raw: str) -> str:
    """Chuan hoa token so trong dap an/text thanh chuoi so hoc hop le (giu dau am va %)."""
    value = (raw or "").strip().lower().replace("\xa0", "").replace(" ", "")
    if not value:
        return ""
    negative = False
    if value.startswith("(") and value.endswith(")"):
        negative = True
        value = value[1:-1]
    is_pct = value.endswith("%")
    if is_pct:
        value = value[:-1]
    if value.startswith("-"):
        negative = not negative
        value = value[1:]
    if not value:
        return ""
    if "." in value and "," in value:
        if value.rfind(",") > value.rfind("."):
            value = value.replace(".", "").replace(",", ".")
        else:
            value = value.replace(",", "")
    elif "," in value:
        parts = value.split(",")
        if len(parts) > 2 and all(len(p) == 3 for p in parts[1:]):
            value = "".join(parts)
        else:
            value = value.replace(",", ".")
    elif "." in value:
        parts = value.split(".")
        if len(parts) > 2:
            if all(len(p) == 3 for p in parts[1:]) and len(parts[0]) <= 3:
                value = "".join(parts)
            else:
                value = "".join(parts[:-1]) + "." + parts[-1]
    value = re.sub(r"[^0-9.]", "", value)
    if not value or value == ".":
        return ""
    if negative:
        value = "-" + value
    if is_pct:
        value = value + "%"
    return value


def parse_float(token: str) -> float | None:
    token = (token or "").strip()
    if not token:
        return None
    if token.endswith("%"):
        token = token[:-1]
    try:
        return float(token)
    except ValueError:
        return None


def _parse_context_number(raw: str) -> float | None:
    """Phan tich so trong context bang/van ban VN (vd `39.271.893.738.448`, `7.166`, `99,988%`)."""
    value = (raw or "").strip().replace("\xa0", "").replace(" ", "")
    if not value:
        return None
    negative = False
    if value.startswith("(") and value.endswith(")"):
        negative = True
        value = value[1:-1]
    is_pct = value.endswith("%")
    if is_pct:
        value = value[:-1]
    if value.startswith("-"):
        negative = not negative
        value = value[1:]
    if not value:
        return None
    if "." in value and "," in value:
        if value.rfind(",") > value.rfind("."):
            value = value.replace(".", "").replace(",", ".")
        else:
            value = value.replace(",", "")
    elif "," in value:
        parts = value.split(",")
        if is_pct:
            value = value.replace(",", ".")
        elif len(parts) > 1 and all(len(p) == 3 for p in parts[1:]) and len(parts[0]) <= 3:
            value = "".join(parts)
        else:
            value = value.replace(",", ".")
    elif "." in value:
        parts = value.split(".")
        if not is_pct and len(parts) >= 2 and all(len(p) == 3 for p in parts[1:]) and len(parts[0]) <= 3:
            value = "".join(parts)
        elif len(parts) > 2:
            return None
    value = re.sub(r"[^0-9.]", "", value)
    if not value or value == ".":
        return None
    try:
        num = float(value)
    except ValueError:
        return None
    return -num if negative else num


def _rel_close(a: float, b: float, rel_tol: float = REL_TOL) -> bool:
    return abs(a - b) <= rel_tol * max(abs(a), abs(b), 1e-9)


def _clean_context_for_calc(context: str) -> str:
    """Loai bo ngay thang, nam tieu de bang, mau bieu, so trang khoi pool tinh toan."""
    s = context or ""
    s = re.sub(r"\b\d{1,2}\s*[/.]\s*\d{1,2}\s*[/.]\s*(?:19|20)\d{2}(?![0-9])", " ", s)
    s = re.sub(r"\b\d{1,2}\s*/\s*(?:19|20)\d{2}(?![0-9])", " ", s)
    # Giu lai tu don vi (VND/Nghin VND) khi xoa nam o tieu de cot bang (vd `2022 VND | 2021 VND`)
    s = re.sub(
        r"(?i)(?<!\d)(?:19|20)\d{2}(?=\s*(?:nghìn|triệu|trăm\s*tỷ|tỷ)?\s*(?:vnd|vnđ|đồng)\b)",
        " ",
        s,
    )
    s = re.sub(r"(?i)\b(?:ngày|tháng)\s+\d{1,2}\b", " ", s)
    s = re.sub(r"(?i)\bnăm\s+(?:19|20)\d{2}\b", " ", s)
    s = re.sub(r"(?i)\[Bang\s*\d+\]", " ", s)
    s = re.sub(r"(?i)\b(?:trang|thuyết minh)\s+\d+(?:\.\d+)?(?:\([a-z]\))?", " ", s)
    s = re.sub(
        r"(?i)(?:mẫu(?:\s+số)?|thông\s+tư(?:\s+số)?|quyết\s+định(?:\s+số)?)\s+[^\n|]{0,40}",
        " ",
        s,
    )
    s = re.sub(r"\(\s*\d+\s*=\s*[^)]+\)", " ", s)
    return s


def _claim_unit_factor(pred_answer: str, match: re.Match[str]) -> float | None:
    """Xac dinh he so don vi tien te sau so duoc khang dinh trong pred_answer."""
    after = pred_answer[match.end() : match.end() + 24].lower()
    if re.match(r"\s*(?:nghìn\s*tỷ|nghin\s*ty)", after):
        return 1e12
    if re.match(r"\s*(?:trăm\s*tỷ|tram\s*ty)", after):
        return 1e11
    if re.match(r"\s*(?:tỷ|ty)(?:\s*(?:đồng|vnd|vnđ))?\b", after):
        return 1e9
    if re.match(r"\s*(?:triệu|trieu)(?:\s*(?:đồng|vnd|vnđ))?\b", after):
        return 1e6
    if re.match(r"\s*(?:nghìn|nghin|ngàn)\s*(?:đồng|vnd|vnđ)\b", after):
        return 1e3
    if re.match(r"\s*(?:đồng|vnd|vnđ)(?![a-zà-ỹ])", after):
        return 1.0
    return None


def _inline_unit_factor(after_text: str) -> float | None:
    """Xac dinh don vi tien te gan truc tiep ngay sau mot so trong context."""
    low = (after_text or "").lower()
    for pat, fac in (
        (r"^\s*(?:nghìn\s*tỷ|nghin\s*ty)(?:\s*(?:vnd|vnđ|đồng))?", 1e12),
        (r"^\s*(?:trăm\s*tỷ|tram\s*ty)(?:\s*(?:vnd|vnđ|đồng))?", 1e11),
        (r"^\s*(?:tỷ|ty)(?:\s*(?:đồng|vnd|vnđ))?(?![a-zà-ỹ])", 1e9),
        (r"^\s*(?:triệu|trieu)(?:\s*(?:đồng|vnd|vnđ))?(?![a-zà-ỹ])", 1e6),
        (r"^\s*(?:nghìn|nghin|ngàn)\s*(?:đồng|vnd|vnđ)(?![a-zà-ỹ])", 1e3),
        (r"^\s*(?:đồng|vnd|vnđ)(?![a-zà-ỹ])", 1.0),
    ):
        if re.match(pat, low):
            return fac
    return None


def _infer_units_in_header(text: str) -> set[float]:
    """Trich xuat he so don vi tien te tu dong tieu de bang hoac dong khai bao don vi."""
    found: set[float] = set()
    masked = (text or "").lower()
    for pat, fac in _UNIT_PHRASE_FACTORS:
        if re.search(pat, masked):
            found.add(fac)
            masked = re.sub(pat, " ", masked)
    if re.search(
        r"(?<![a-zà-ỹ])(?:vnd|vnđ)(?![a-zà-ỹ])|đơn\s*vị(?:\s*tính)?\s*[:\-]\s*đồng\b|\bđồng(?![a-zà-ỹ])",
        masked,
    ):
        found.add(1.0)
    return found


def _claim_kind(pred_answer: str, match: re.Match[str]) -> str:
    rt = match.group(0)
    after = pred_answer[match.end() : match.end() + 24].lower()
    before = pred_answer[max(0, match.start() - 12) : match.start()].lower()
    if rt.endswith("%") or re.match(r"\s*(?:%|(?:phần\s*trăm|phan\s*tram)\b)", after):
        return "pct"
    if _claim_unit_factor(pred_answer, match) is not None:
        return "currency"
    core = rt.strip().lstrip("(").rstrip(")%")
    if re.search(r"\b(?:năm|kỳ|giai\s*đoạn)\s*$", before) and re.fullmatch(r"(?:19|20)\d{2}", core):
        return "year"
    return "generic"


def numeric_match_pred(pred_answer: str, gold_value: object, gold_answer: str) -> bool:
    if not pred_answer or not pred_answer.strip():
        return False
    if is_refusal(pred_answer) or norm_answer(pred_answer) == norm_answer(REFUSAL_TEXT):
        return False
    try:
        gv = float(gold_value)
    except (TypeError, ValueError):
        return norm_answer(pred_answer) == norm_answer(gold_answer)
    cands = [parse_float(norm_num_token(t)) for t in NUM_RE.findall(pred_answer)]
    cands = [c for c in cands if c is not None]
    if not cands:
        return False
    return any(abs(c - gv) <= max(1e-4, abs(gv) * 1e-6) for c in cands)


def load_chunks() -> dict:
    path = ROOT / "data" / "processed" / "chunks.jsonl"
    idx: dict = {}
    if not path.exists():
        return idx
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            idx[r.get("chunk_id", "")] = r.get("text", "")
    return idx


def load_chunks_full() -> dict:
    path = ROOT / "data" / "processed" / "chunks.jsonl"
    idx: dict = {}
    if not path.exists():
        return idx
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            idx[r.get("chunk_id", "")] = r
    return idx


def _extract_chunk_pool(
    chunk_text: str,
) -> tuple[set[str], set[str], list[_ContextEntry], frozenset[float]]:
    raw_tokens = {
        m.group(0).strip().lstrip("(").rstrip(")%")
        for m in NUM_RE.finditer(chunk_text or "")
    }
    header_factors: set[float] = set()
    for line in (chunk_text or "").splitlines():
        st = line.strip()
        if not st:
            continue
        low = st.lower()
        is_header = (
            "|" in st
            or "đơn vị" in low
            or "đvt" in low
            or (
                len(st) <= 60
                and bool(re.search(r"(?:vnd|vnđ|triệu\s*đồng|tỷ\s*đồng|nghìn\s*đồng)", low))
            )
        )
        if is_header:
            header_factors |= _infer_units_in_header(st)
    hfacs = frozenset(header_factors)

    cleaned = _clean_context_for_calc(chunk_text or "")
    raw_items: list[tuple[float, bool, str, int, int, float | None, bool]] = []
    for line_idx, line in enumerate(cleaned.splitlines()):
        has_pipe = "|" in line
        cells = line.split("|") if has_pipe else [line]
        n_cells = len(cells)
        for ci, cell in enumerate(cells):
            col_r = (n_cells - ci) if has_pipe else -1
            for m in NUM_RE.finditer(cell):
                rt = m.group(0)
                core = rt.strip().lstrip("(").rstrip(")%")
                if re.fullmatch(r"0\d+", core):
                    continue
                after = cell[m.end() : m.end() + 24]
                ifac = _inline_unit_factor(after)
                is_pct = rt.endswith("%") or bool(
                    re.match(r"\s*(?:%|phần\s*trăm|phan\s*tram)\b", after.lower())
                )
                is_ratio = bool(re.match(r"\s*lần\b", after.lower()))
                has_unit = is_pct or is_ratio or (ifac is not None)
                if re.fullmatch(r"(?:19|20)\d{2}", core) and not has_unit:
                    continue
                val = _parse_context_number(rt)
                if val is None:
                    continue
                bare_small = (
                    "." not in core and "," not in core and abs(val) < 1000 and not has_unit
                )
                raw_items.append((val, bare_small, rt, line_idx, col_r, ifac, is_pct))

    max_abs = max((abs(item[0]) for item in raw_items), default=0.0)
    entries: list[_ContextEntry] = []
    clean_strs: set[str] = set()
    for val, bare_small, rt, line_idx, col_r, ifac, is_pct in raw_items:
        if max_abs >= 1e5 and bare_small:
            continue
        clean_strs.add(rt.strip().lstrip("(").rstrip(")%"))
        ufacs = frozenset((ifac,)) if ifac is not None else hfacs
        entries.append(_ContextEntry(val, line_idx, col_r, ufacs, ifac, is_pct))

    if max_abs < 1e5:
        seen_vals = {(e.val, e.line_idx) for e in entries}
        for val, _, rt, line_idx, col_r, ifac, is_pct in raw_items:
            pv = parse_float(norm_num_token(rt))
            if pv is not None and (pv, line_idx) not in seen_vals:
                ufacs = frozenset((ifac,)) if ifac is not None else hfacs
                entries.append(_ContextEntry(pv, line_idx, col_r, ufacs, ifac, is_pct))
                seen_vals.add((pv, line_idx))
    return raw_tokens, clean_strs, entries, hfacs


def _pct_supported_in_chunk(
    target: float,
    entries: list[_ContextEntry],
    hfacs: frozenset[float],
) -> bool:
    if any(
        _rel_close(target, e.val) and (e.is_pct or (e.inline_factor is None and not hfacs))
        for e in entries
    ):
        return True
    by_line: dict[int, list[_ContextEntry]] = {}
    for e in entries:
        by_line.setdefault(e.line_idx, []).append(e)
    for grp in by_line.values():
        for i in range(len(grp)):
            for j in range(len(grp)):
                if i != j and grp[j].val != 0 and _rel_close(target, grp[i].val / grp[j].val * 100.0):
                    return True
    if len(entries) <= 8:
        for i in range(len(entries)):
            for j in range(len(entries)):
                if i != j and entries[j].val != 0 and _rel_close(target, entries[i].val / entries[j].val * 100.0):
                    return True
        return False
    # Bang lon: chi chap nhan ty le cung cot tren cac dong lan can (vd bien loi nhuan gop)
    for i, ea in enumerate(entries):
        if ea.col_from_right < 0:
            continue
        for j, eb in enumerate(entries):
            if (
                i != j
                and ea.col_from_right == eb.col_from_right
                and 0 < abs(ea.line_idx - eb.line_idx) <= 3
                and eb.val > 0
                and 0 < abs(ea.val) <= eb.val
                and _rel_close(target, ea.val / eb.val * 100.0)
            ):
                return True
    return False


def _currency_supported_in_chunk(
    target: float,
    claimed_factor: float | None,
    entries: list[_ContextEntry],
) -> bool:
    for e in entries:
        if claimed_factor is not None:
            scales = [claimed_factor / uf for uf in e.unit_factors] if e.unit_factors else [1.0, claimed_factor]
        else:
            scales = list(UNIT_SCALES)
        if any(_rel_close(target, e.val / s) for s in scales):
            return True

    by_line: dict[int, list[_ContextEntry]] = {}
    for e in entries:
        by_line.setdefault(e.line_idx, []).append(e)
    is_small = len(entries) <= 8
    groups = [entries] if is_small else list(by_line.values())
    for grp in groups:
        for i, ea in enumerate(grp):
            ua_eff = ea.unit_factors or (frozenset((1.0,)) if not claimed_factor else frozenset((1.0, claimed_factor)))
            for j, eb in enumerate(grp):
                if i == j:
                    continue
                ub_eff = eb.unit_factors or (frozenset((1.0,)) if not claimed_factor else frozenset((1.0, claimed_factor)))
                for ufa in ua_eff:
                    for ufb in ub_eff:
                        if not is_small and ea.unit_factors and eb.unit_factors and ufa != ufb:
                            continue
                        denom = claimed_factor if claimed_factor else ufa
                        if _rel_close(target, (ea.val * ufa - eb.val * ufb) / denom):
                            return True
                        if is_small and _rel_close(target, (ea.val * ufa + eb.val * ufb) / denom):
                            return True
    return False


def _claim_supported_in_chunk(
    target: float,
    rcore: str,
    kind: str,
    claimed_factor: float | None,
    raw_tokens: set[str],
    clean_strs: set[str],
    entries: list[_ContextEntry],
    hfacs: frozenset[float],
) -> bool:
    if kind == "year":
        return rcore in raw_tokens
    if kind == "pct":
        return _pct_supported_in_chunk(target, entries, hfacs)
    if kind == "currency":
        return _currency_supported_in_chunk(target, claimed_factor, entries)
    if rcore in clean_strs or any(_rel_close(target, e.val) for e in entries):
        return True
    by_line: dict[int, list[_ContextEntry]] = {}
    for e in entries:
        by_line.setdefault(e.line_idx, []).append(e)
    groups = [entries] if len(entries) <= 8 else list(by_line.values())
    for grp in groups:
        for i, ea in enumerate(grp):
            for j, eb in enumerate(grp):
                if i != j and eb.val != 0 and _rel_close(target, ea.val / eb.val):
                    return True
    return False


def numbers_in_context(pred_answer: str, context: str) -> bool:
    """Kiem tra moi khang dinh so trong pred_answer co duoc ho tro boi context khong.

    Khi `context` gom nhieu chunk ngan cach boi `CHUNK_SEP`, tung chunk duoc
    kiem tra doc lap (khong ghep phep tinh xuyen chunk) theo dung ty le don vi
    `(claimed_factor / chunk_base_factor)` va sai so tuong doi `1e-3`.
    """
    matches = list(NUM_RE.finditer(pred_answer or ""))
    if not matches:
        return True
    if not (context or "").strip():
        return False
    segments = [s for s in context.split(CHUNK_SEP) if s.strip()] if CHUNK_SEP in context else [context]
    pools = [_extract_chunk_pool(seg) for seg in segments]
    for m in matches:
        rp = m.group(0)
        rcore = rp.strip().lstrip("(").rstrip(")%")
        kind = _claim_kind(pred_answer, m)
        claimed_factor = _claim_unit_factor(pred_answer, m)
        target = parse_float(norm_num_token(rp))
        if target is None:
            continue
        if not any(
            _claim_supported_in_chunk(target, rcore, kind, claimed_factor, raw_t, clean_s, ents, hfacs)
            for raw_t, clean_s, ents, hfacs in pools
        ):
            return False
    return True


def _gold_chunks_for_row(r: dict, g: dict) -> list[str]:
    raw_gold = r.get("gold_chunk_ids") or ";".join(
        e.get("chunk_id", "") for e in (g.get("evidence") or []) if e.get("chunk_id")
    )
    return [c for c in raw_gold.split(";") if c]


def recall_mrr_at(pred_chunks: list, gold_unique: list, k: int) -> tuple[float, float]:
    top = pred_chunks[:k]
    hit = any(c in top for c in gold_unique)
    rank = next((i + 1 for i, c in enumerate(top) if c in gold_unique), None)
    return (1.0 if hit else 0.0, 1.0 / rank if rank else 0.0)


def evaluate_split(
    items: list[dict],
    gold: dict[str, dict],
    chunks: dict[str, str],
    chunks_full: dict[str, dict],
    run_name: str,
    split: str,
    pred_filename: str = "",
) -> tuple[dict, list[dict]]:
    """Cham toan bo metric cho mot split (`dev` hoac `test`)."""
    n = len(items)
    r3, r5, r10, m3, m5, m10 = [], [], [], [], [], []
    ctx_p, ctx_r = [], []
    cit_p_hit, cit_p_den = 0, 0
    cit_complete_hit, cit_complete_den = 0, 0
    ans_num_hit, ans_num_den = 0, 0
    ans_em_hit, ans_em_den = 0, 0
    comp_hit, comp_den = 0, 0
    year_hit, year_den = 0, 0
    ver_hit, ver_den = 0, 0
    period_hit, period_den = 0, 0
    page_hit, page_den = 0, 0
    ref_pred_pos, ref_tp, ref_den = 0, 0, 0
    unsup_bad, unsup_den = 0, 0
    relev_hit = 0
    status_counts = {"answered": 0, "partial_answer": 0, "refused": 0, "ambiguous": 0}
    label_counts = {"true_refusal": 0, "missed_refusal": 0, "false_refusal": 0, "true_answer": 0}
    detail_rows: list[dict] = []

    for r in items:
        g = gold.get(r["question_id"], {})
        pred_chunks = [c for c in (r.get("predicted_chunk_ids") or "").split(";") if c]
        gold_chunks = _gold_chunks_for_row(r, g)
        gold_unique = sorted(set(gold_chunks))

        if gold_unique:
            h3, m_3 = recall_mrr_at(pred_chunks, gold_unique, 3)
            h5, m_5 = recall_mrr_at(pred_chunks, gold_unique, 5)
            h10, m_10 = recall_mrr_at(pred_chunks, gold_unique, 10)
            r3.append(h3)
            r5.append(h5)
            r10.append(h10)
            m3.append(m_3)
            m5.append(m_5)
            m10.append(m_10)
            inter = len(set(pred_chunks[:5]) & set(gold_unique))
            ctx_p.append(inter / 5.0)
            ctx_r.append(inter / len(gold_unique))
            cit_p_den += 1
            if pred_chunks and pred_chunks[0] in gold_unique:
                cit_p_hit += 1

        needs_ref = bool(g.get("needs_more_evidence"))
        pred_is_ref = is_refusal(r.get("predicted_answer", ""))
        if needs_ref:
            ref_den += 1
            if pred_is_ref:
                ref_tp += 1
                relev_hit += 1
        if pred_is_ref:
            ref_pred_pos += 1

        top_full = [chunks_full.get(c, {}) for c in pred_chunks[:5] if c in chunks_full]
        if top_full:
            cit_complete_den += 1
            if citation_complete(top_full):
                cit_complete_hit += 1
        qtext = g.get("question", "") or r.get("question", "")
        mtickers = resolve_tickers(qtext)
        myears = YEAR_RE.findall(qtext)
        top_for_status = [
            {
                "chunk_id": c.get("chunk_id", ""),
                "page": c.get("page", ""),
                "company_id": c.get("company_id", ""),
                "fiscal_year": c.get("fiscal_year", ""),
            }
            for c in top_full
        ]
        decided = decide_status(
            qtext,
            r.get("predicted_answer", ""),
            top_for_status,
            tickers=mtickers or None,
            years=myears or None,
            conflict=detect_retrieval_conflict(mtickers, myears, top_for_status),
            refused_by_rule=pred_is_ref,
        )
        status_counts[decided["status"]] = status_counts.get(decided["status"], 0) + 1
        rlabel = refusal_label(r.get("predicted_answer", ""), needs_ref)
        label_counts[rlabel] = label_counts.get(rlabel, 0) + 1
        detail_rows.append(
            {
                "run": run_name,
                "split": split,
                "question_id": r.get("question_id", ""),
                "answer_status": decided["status"],
                "status_reason": decided.get("reason", ""),
                "refusal_label": rlabel,
                "needs_more_evidence": needs_ref,
                "citation_complete_top1": bool(top_for_status and citation_complete(top_for_status)),
                "predicted_answer": r.get("predicted_answer", ""),
                "predicted_top1_chunk_id": r.get("predicted_top1_chunk_id", ""),
            }
        )

        if not needs_ref and g.get("gold_answer"):
            ans_num_den += 1
            ans_em_den += 1
            if numeric_match_pred(r.get("predicted_answer", ""), g.get("value"), g.get("gold_answer", "")):
                ans_num_hit += 1
                relev_hit += 1
            if norm_answer(r.get("predicted_answer", "")) == norm_answer(g.get("gold_answer", "")):
                ans_em_hit += 1

        gold_comps = parse_pipe_set(g.get("company_id"), upper=True)
        pred_comps = parse_pipe_set(r.get("predicted_company"), upper=True)
        if gold_comps:
            comp_den += 1
            if pred_comps == gold_comps:
                comp_hit += 1
        gold_years = parse_pipe_set(g.get("fiscal_year"))
        pred_years = parse_pipe_set(r.get("predicted_year"))
        if gold_years:
            year_den += 1
            if pred_years == gold_years:
                year_hit += 1
        gold_report = str(g.get("report_id", "")).strip()
        if gold_report:
            ver_den += 1
            gold_ver = (
                "separate"
                if gold_report.endswith("_separate")
                else ("consolidated" if gold_report.endswith("_consolidated") else "")
            )
            if gold_ver and (r.get("predicted_report_version") or "").strip() == gold_ver:
                ver_hit += 1
        if gold_comps and gold_years and gold_report:
            period_den += 1
            gold_ver = (
                "separate"
                if gold_report.endswith("_separate")
                else ("consolidated" if gold_report.endswith("_consolidated") else "")
            )
            if (
                pred_comps == gold_comps
                and pred_years == gold_years
                and (r.get("predicted_report_version") or "").strip() == gold_ver
            ):
                period_hit += 1
        if str(g.get("source_page", "")).strip():
            page_den += 1
            if str(r.get("predicted_page", "")).strip() == str(g.get("source_page", "")).strip():
                page_hit += 1

        pred_ans = (r.get("predicted_answer") or "").strip()
        if pred_ans and not pred_is_ref and not needs_ref and g.get("gold_answer"):
            unsup_den += 1
            ctx_text = CHUNK_SEP.join(chunks.get(c, "") for c in pred_chunks[:5] if chunks.get(c, ""))
            if not numbers_in_context(pred_ans, ctx_text):
                unsup_bad += 1

    k = max(
        (len([c for c in (r.get("predicted_chunk_ids") or "").split(";") if c]) for r in items),
        default=0,
    )
    ev_den = len(r3)
    unsup_rate = round(unsup_bad / unsup_den, 4) if unsup_den else 0.0
    r5v = round(sum(r5) / len(r5), 4) if r5 else 0.0
    m5v = round(sum(m5) / len(m5), 4) if m5 else 0.0
    r10v = round(sum(r10) / len(r10), 4) if r10 else 0.0
    m10v = round(sum(m10) / len(m10), 4) if m10 else 0.0
    rk_vals: list[tuple[float, float]] = []
    for r in items:
        gu = sorted(set(_gold_chunks_for_row(r, gold.get(r["question_id"], {}))))
        if gu:
            pc = [c for c in (r.get("predicted_chunk_ids") or "").split(";") if c]
            rk_vals.append(recall_mrr_at(pc, gu, max(k, 1)))
    rkv = round(sum(x[0] for x in rk_vals) / len(rk_vals), 4) if rk_vals else 0.0
    mkv = round(sum(x[1] for x in rk_vals) / len(rk_vals), 4) if rk_vals else 0.0
    cit_complete_rate = round(cit_complete_hit / cit_complete_den, 4) if cit_complete_den else 0.0
    relev = round(relev_hit / n, 4) if n else 0.0
    false_answer_rate = round(1.0 - relev, 4) if n else 0.0
    row = {
        "run": run_name,
        "split": split,
        "n": n,
        "k": k,
        "recall_at_k": rkv,
        "mrr_at_k": mkv,
        "recall_at_3": round(sum(r3) / len(r3), 4) if r3 else 0.0,
        "recall_at_5": r5v,
        "recall_at_10": r10v,
        "mrr_at_3": round(sum(m3) / len(m3), 4) if m3 else 0.0,
        "mrr_at_5": m5v,
        "mrr_at_10": m10v,
        "context_precision_at_5": round(sum(ctx_p) / len(ctx_p), 4) if ctx_p else 0.0,
        "context_recall_at_5": round(sum(ctx_r) / len(ctx_r), 4) if ctx_r else 0.0,
        "citation_precision_top1": round(cit_p_hit / cit_p_den, 4) if cit_p_den else 0.0,
        "citation_recall_at_5": r5v,
        "citation_correctness": round(cit_p_hit / cit_p_den, 4) if cit_p_den else 0.0,
        "citation_complete_rate": cit_complete_rate,
        "citation_complete_den": cit_complete_den,
        "numeric_match": round(ans_num_hit / ans_num_den, 4) if ans_num_den else 0.0,
        "exact_match": round(ans_em_hit / ans_em_den, 4) if ans_em_den else 0.0,
        "period_accuracy": round(period_hit / period_den, 4) if period_den else 0.0,
        "company_accuracy": round(comp_hit / comp_den, 4) if comp_den else 0.0,
        "year_accuracy": round(year_hit / year_den, 4) if year_den else 0.0,
        "version_accuracy": round(ver_hit / ver_den, 4) if ver_den else 0.0,
        "page_accuracy": round(page_hit / page_den, 4) if page_den else 0.0,
        "evidence_den": ev_den,
        "unsupported_claim_rate": unsup_rate,
        "faithfulness_heuristic": round(1.0 - unsup_rate, 4) if unsup_den else 0.0,
        "answer_relevancy_heuristic": relev,
        "false_answer_rate": false_answer_rate,
        "status_answered": status_counts.get("answered", 0),
        "status_partial": status_counts.get("partial_answer", 0),
        "status_refused": status_counts.get("refused", 0),
        "status_ambiguous": status_counts.get("ambiguous", 0),
        "true_refusal": label_counts.get("true_refusal", 0),
        "missed_refusal": label_counts.get("missed_refusal", 0),
        "false_refusal": label_counts.get("false_refusal", 0),
        "true_answer": label_counts.get("true_answer", 0),
        "refusal_precision": round(ref_tp / ref_pred_pos, 4) if ref_pred_pos else 0.0,
        "refusal_recall": round(ref_tp / ref_den, 4) if ref_den else 0.0,
        "refusal_rate": round(ref_tp / ref_den, 4) if ref_den else 0.0,
        "refusal_den": ref_den,
        "prediction_file": pred_filename,
    }
    return row, detail_rows


def main() -> int:
    p = argparse.ArgumentParser(description="Chấm metric retrieval/answer/citation.")
    p.add_argument("--run", default="E0")
    p.add_argument("--pred", default=None)
    p.add_argument("--gold", default=str(ROOT / "data" / "annotations" / "qa_gold.jsonl"))
    p.add_argument("--out", default=str(ROOT / "evaluation" / "metrics_summary.csv"))
    p.add_argument("--test-dir", default=str(ROOT / "evaluation" / "test_predictions"))
    p.add_argument("--dev-dir", default=str(ROOT / "evaluation" / "dev_predictions"))
    p.add_argument("--refusal-dir", default=str(ROOT / "evaluation" / "refusal_labels"))
    args = p.parse_args()

    with open(args.gold, encoding="utf-8") as gf:
        gold = {json.loads(line)["question_id"]: json.loads(line) for line in gf if line.strip()}
    if args.pred:
        pred_path = Path(args.pred)
    else:
        pred_path = Path(args.test_dir) / f"test_predictions_{args.run}.csv"
        legacy = ROOT / "evaluation" / f"test_predictions_{args.run}.csv"
        if not pred_path.exists() and legacy.exists():
            pred_path = legacy
    with open(pred_path, encoding="utf-8") as pf:
        rows = list(csv.DictReader(pf))

    by_split: dict[str, list[dict]] = {"dev": [], "test": []}
    dev_path = Path(args.dev_dir) / pred_path.name.replace("test_", "dev_")
    legacy_dev = pred_path.parent / pred_path.name.replace("test_", "dev_")
    if not dev_path.exists() and legacy_dev.exists() and legacy_dev != pred_path:
        dev_path = legacy_dev
    all_rows = rows
    if dev_path.exists() and dev_path != pred_path:
        with open(dev_path, encoding="utf-8") as df:
            all_rows = list(csv.DictReader(df)) + rows
    for r in all_rows:
        by_split.setdefault(r.get("split", "test"), []).append(r)

    chunks = load_chunks()
    chunks_full = load_chunks_full()

    summary: list[dict] = []
    detail_rows: list[dict] = []
    for split in ("dev", "test"):
        row, s_details = evaluate_split(
            by_split.get(split, []),
            gold,
            chunks,
            chunks_full,
            args.run,
            split,
            pred_filename=pred_path.name,
        )
        summary.append(row)
        detail_rows.extend(s_details)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    merged: list[dict] = []
    if out.exists():
        try:
            with open(out, encoding="utf-8") as ef:
                existing = list(csv.DictReader(ef))
            merged = [r for r in existing if r.get("run") != args.run]
        except Exception:
            merged = []
    merged.extend(summary)
    order = {"E0": 0, "E1": 1, "E2": 2, "E3": 3, "E4": 4, "E5": 5, "E6": 6, "E7": 7, "E8": 8}
    merged.sort(key=lambda r: (order.get(r.get("run"), 9), r.get("split")))
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
        w.writeheader()
        w.writerows(merged)

    for s in summary:
        print(
            f"{s['run']}/{s['split']}: n={s['n']} R@3={s['recall_at_3']} R@5={s['recall_at_5']} R@10={s['recall_at_10']} "
            f"MRR@5={s['mrr_at_5']} MRR@10={s['mrr_at_10']} ctxP={s['context_precision_at_5']} ctxR={s['context_recall_at_5']} "
            f"citeP={s['citation_precision_top1']} citeFull={s['citation_complete_rate']} "
            f"num={s['numeric_match']} em={s['exact_match']} "
            f"period={s['period_accuracy']} page={s['page_accuracy']} unsup={s['unsupported_claim_rate']} "
            f"faith={s['faithfulness_heuristic']} relev={s['answer_relevancy_heuristic']} "
            f"falseAns={s['false_answer_rate']} refP={s['refusal_precision']} refR={s['refusal_recall']}({s['refusal_den']}) "
            f"status=[ans={s['status_answered']}/part={s['status_partial']}/ref={s['status_refused']}/amb={s['status_ambiguous']}] "
            f"labels=[TR={s['true_refusal']}/MR={s['missed_refusal']}/FR={s['false_refusal']}/TA={s['true_answer']}]"
        )
    print(f"Đã ghi -> {out}")
    detail_path = Path(args.refusal_dir) / f"refusal_labels_{args.run}.csv"
    detail_path.parent.mkdir(parents=True, exist_ok=True)
    if detail_rows:
        with open(detail_path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(detail_rows[0].keys()))
            w.writeheader()
            w.writerows(detail_rows)
        print(f"Đã ghi nhãn chi tiết -> {detail_path} ({len(detail_rows)} dòng)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
