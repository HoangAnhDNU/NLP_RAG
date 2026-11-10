"""Lookup co cau truc tren table_records: loc company/nam/ban, khop chi tieu.

Dung cho E8: cau hoi ve mot chi tieu di qua lookup truoc, RAG giai thich
va trich dan sau. Giam hallucination so lieu so voi embedding thuan tuy.
"""

from __future__ import annotations

import re
import unicodedata

UNIT_FACTORS: dict[str, float] = {
    "đồng": 1.0,
    "nghìn đồng": 1e3,
    "triệu đồng": 1e6,
    "tỷ đồng": 1e9,
    "trăm tỷ đồng": 1e11,
    "nghìn tỷ đồng": 1e12,
    "%": 1.0,
    "lần": 1.0,
    "": 1.0,
}

COMPANY_ALIASES: dict[str, list[str]] = {
    "HPG": ["hpg", "hòa phát", "hoa phat"],
    "HSG": ["hsg", "hoa sen"],
    "NKG": ["nkg", "nam kim", "thép nam kim", "thep nam kim"],
    "MSR": ["msr", "masan", "high-tech", "high tech", "hightech"],
}


def resolve_tickers(question: str) -> list[str]:
    """Nhan dien ma CK ca khi cau hoi chi ghi ten day du, khong ghi ma.

    Giu dau tieng Viet o du lieu, chi bo dau tam thoi de so khop.
    """
    up = (question or "").upper()
    found: list[str] = []
    for t in ["HPG", "HSG", "NKG", "MSR"]:
        if re.search(rf"(?<![A-Z]){t}(?![A-Z])", up):
            if t not in found:
                found.append(t)
    if found:
        return found
    low = strip_accents(question or "").lower()
    for ticker, aliases in COMPANY_ALIASES.items():
        for alias in aliases:
            if alias in low:
                if ticker not in found:
                    found.append(ticker)
                break
    return found


def strip_accents(text: str) -> str:
    text = unicodedata.normalize("NFD", text or "")
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def norm_text(text: str) -> str:
    text = unicodedata.normalize("NFC", (text or "").lower())
    return re.sub(r"\s+", " ", text).strip()


def tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-zà-ỹ0-9_%.,/+-]+", norm_text(text)))


def parse_target_unit(question: str) -> str:
    low = norm_text(question)
    if "%" in question or "phần trăm" in low or "phan tram" in strip_accents(low):
        return "%"
    if "nghìn tỷ" in low:
        return "nghìn tỷ đồng"
    if "trăm tỷ" in low:
        return "trăm tỷ đồng"
    # "tỷ lệ" (ty le) là chỉ tiêu phần trăm, không phải đơn vị tỷ đồng.
    low_no_ratio = low.replace("tỷ lệ", " ").replace("ty le", " ")
    if "triệu" in low_no_ratio:
        return "triệu đồng"
    if re.search(r"\btỷ\b", low_no_ratio) or "tỷ đồng" in low_no_ratio:
        return "tỷ đồng"
    if "nghìn" in low_no_ratio and "đồng" in low_no_ratio:
        return "nghìn đồng"
    if re.search(r"\blần\b", low):
        return "lần"
    if "đồng" in low:
        return "đồng"
    return ""


def convert_value(value: float, from_unit: str, to_unit: str) -> float | None:
    if value is None:
        return None
    fu = UNIT_FACTORS.get(from_unit or "", None)
    tu = UNIT_FACTORS.get(to_unit or "", None)
    if to_unit in ("%", "lần", ""):
        if from_unit in ("%", "lần", "", to_unit):
            return float(value)
        return None
    if fu is None or tu is None:
        return None
    return float(value) * fu / tu


def format_number(value: float) -> str:
    if value is None:
        return ""
    if abs(value) >= 1e15 or (abs(value) < 1e-6 and value != 0):
        return f"{value:.4f}"
    rounded = round(float(value), 4)
    if rounded == int(rounded):
        return str(int(rounded))
    text = f"{rounded:.4f}".rstrip("0").rstrip(".")
    return text


METRIC_KEYWORDS: dict[str, list[str]] = {
    "doanh thu thuan": ["doanh thu thuan", "doanh thu ban hang"],
    "loi nhuan sau thue": ["loi nhuan sau thue", "loi nhuan thuan"],
    "tien va tuong duong tien": ["tien", "tuong duong"],
    "lai co ban": ["lai co ban", "co phieu"],
    "bien loi nhuan gop": ["bien", "loi nhuan gop"],
    "von chu so huu": ["von chu so huu"],
    "tong tai san": ["tong tai san"],
}


def metric_score(question: str, record_metric: str) -> float:
    qn = norm_text(question)
    mn = norm_text(record_metric or "")
    q = tokens(question)
    m = tokens(record_metric or "")
    m = {t for t in m if len(t) > 1}
    if not m:
        return 0.0
    stop = {"ve", "cac", "cua", "va", "cho", "nam", "bao", "nhieu", "dong", "ty", "trieu", "nghin", "tram", "hop", "nhat", "rieng", "me", "cong", "ty", "phan", "co", "bao", "cao", "tai", "chinh", "ket", "thuc", "ngay", "thang"}
    m = {t for t in m if t not in stop}
    if not m:
        return 0.0
    inter = len(q & m)
    recall = inter / len(m)
    bonus = 0.0
    mn_base = re.sub(r"\(.*\)", "", mn).strip()
    if mn_base and mn_base in qn:
        bonus = 0.4 + min(0.2, len(mn_base) / 200.0)
    elif mn and mn in qn:
        bonus = 0.4 + min(0.2, len(mn) / 200.0)
    q_thuan = "thuần" in qn or "thuan" in strip_accents(qn)
    m_thuan = "thuần" in mn or "thuan" in strip_accents(mn)
    if q_thuan == m_thuan:
        bonus += 0.15
    else:
        bonus -= 0.2
    return recall + bonus


def lookup_records(
    records: list[dict],
    tickers: list[str],
    years: list[str],
    version: str,
    question: str,
    min_score: float = 0.3,
) -> list[tuple[float, dict]]:
    scored: list[tuple[float, dict]] = []
    year_set = {str(y) for y in years}
    for r in records:
        if tickers and r.get("company") not in tickers:
            continue
        if year_set and str(r.get("year")) not in year_set:
            continue
        if version and r.get("report_version") != version:
            continue
        s = metric_score(question, r.get("metric", ""))
        if r.get("metric_code"):
            s += 0.05
        if s >= min_score:
            scored.append((s, r))
    scored.sort(key=lambda x: (x[0], float(x[1].get("confidence") or 0)), reverse=True)
    return scored


def find_pair(records: list[dict], tickers: list[str], years: list[str], version: str, keywords: list[str]) -> dict | None:
    cands = lookup_records(records, tickers, years, version, " ".join(keywords), min_score=0.2)
    if not cands:
        return None
    return cands[0][1]


def find_by_code(
    records: list[dict],
    tickers: list[str],
    years: list[str],
    version: str,
    codes: list[str],
    keywords: list[str] | None = None,
) -> dict | None:
    """Tim ban ghi theo ma so chuan (10 doanh thu thuan, 20 loi nhuan gop)."""
    year_set = {str(y) for y in years}
    kw = [norm_text(k) for k in (keywords or [])]
    best: dict | None = None
    for r in records:
        if tickers and r.get("company") not in tickers:
            continue
        if year_set and str(r.get("year")) not in year_set:
            continue
        if version and r.get("report_version") != version:
            continue
        if str(r.get("metric_code") or "") not in codes:
            continue
        if kw:
            mn = norm_text(r.get("metric", ""))
            if not any(k and k in mn for k in kw):
                continue
        if r.get("statement") == "income_statement":
            return r
        if best is None:
            best = r
    return best
